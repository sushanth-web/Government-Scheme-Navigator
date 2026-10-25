from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import threading
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlsplit

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from langgraph.checkpoint.memory import InMemorySaver

from session_store import SessionStore


logger = logging.getLogger(__name__)
MAX_AUDIO_BYTES = 20 * 1024 * 1024
PRIVACY_NOTICE_VERSION = "2026-10-21"
SSE_RESPONSES = {
    200: {
        "description": "Server-sent events: status, reply, and error events.",
        "content": {"text/event-stream": {"schema": {"type": "string"}}},
    }
}
LANGUAGES = {
    "Hindi": "hi-IN",
    "Bengali": "bn-IN",
    "Gujarati": "gu-IN",
    "English": "en-IN",
    "Telugu": "te-IN",
    "Marathi": "mr-IN",
    "Tamil": "ta-IN",
    "Kannada": "kn-IN",
    "Malayalam": "ml-IN",
    "Punjabi": "pa-IN",
}


class LanguageRequest(BaseModel):
    language: str


class ConsentRequest(BaseModel):
    accepted: bool
    notice_version: str = Field(min_length=1, max_length=32)


class MessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)


class TurnDetails(BaseModel):
    profile: dict[str, Any]
    ranked_schemes: str | None
    selected_schemes: list[str]
    scheme_details: list[dict[str, Any]]
    document_checklist: list[dict[str, Any]]
    language: str | None
    locale: str | None


class TurnResponse(BaseModel):
    session_id: str
    stage: str
    reply: str
    details: TurnDetails
    audio_base64: str | None = None
    audio_error: str | None = None


@dataclass
class ConversationSession:
    session_id: str
    consented_at: str | None = None
    consent_notice_version: str | None = None
    stage: str = "language"
    language: str | None = None
    locale: str | None = None
    profile: dict[str, Any] = field(default_factory=dict)
    ranked_schemes: str | None = None
    selected_schemes: list[str] = field(default_factory=list)
    scheme_details: list[dict[str, Any]] = field(default_factory=list)
    document_checklist: list[dict[str, Any]] = field(default_factory=list)
    optional_details_asked: bool = False
    lock: threading.RLock = field(default_factory=threading.RLock)

    @classmethod
    def from_payload(
        cls,
        session_id: str,
        payload: dict[str, Any],
        lock: threading.RLock,
    ) -> "ConversationSession":
        return cls(
            session_id=session_id,
            consented_at=payload.get("consented_at"),
            consent_notice_version=payload.get("consent_notice_version"),
            stage=payload.get("stage", "language"),
            language=payload.get("language"),
            locale=payload.get("locale"),
            profile=payload.get("profile", {}),
            ranked_schemes=payload.get("ranked_schemes"),
            selected_schemes=payload.get("selected_schemes", []),
            scheme_details=payload.get("scheme_details", []),
            document_checklist=payload.get("document_checklist", []),
            optional_details_asked=payload.get("optional_details_asked", False),
            lock=lock,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "consented_at": self.consented_at,
            "consent_notice_version": self.consent_notice_version,
            "stage": self.stage,
            "language": self.language,
            "locale": self.locale,
            "profile": self.profile,
            "ranked_schemes": self.ranked_schemes,
            "selected_schemes": self.selected_schemes,
            "scheme_details": self.scheme_details,
            "document_checklist": self.document_checklist,
            "optional_details_asked": self.optional_details_asked,
        }

    def details(self) -> dict[str, Any]:
        return {
            "profile": dict(self.profile),
            "ranked_schemes": self.ranked_schemes,
            "selected_schemes": list(self.selected_schemes),
            "scheme_details": list(self.scheme_details),
            "document_checklist": list(self.document_checklist),
            "language": self.language,
            "locale": self.locale,
        }


session_store = SessionStore()
_session_locks: dict[str, threading.RLock] = {}
_session_locks_guard = threading.Lock()
_checkpointer = InMemorySaver()


async def _expire_sessions() -> None:
    from agents import eligibilty_agent, intake_agent

    while True:
        await asyncio.sleep(60)
        try:
            expired = await run_in_threadpool(session_store.purge_expired)
        except Exception as error:
            logger.error("Session expiry cleanup failed (%s).", type(error).__name__)
            continue
        for session_id in expired:
            try:
                intake_agent.end_turn_session(session_id)
                eligibilty_agent.end_turn_session(session_id)
                with _session_locks_guard:
                    _session_locks.pop(session_id, None)
            except Exception as error:
                logger.error("Checkpoint expiry cleanup failed (%s).", type(error).__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _checkpointer
    await run_in_threadpool(session_store.open)
    checkpoint_pool = None
    try:
        if session_store.persistent:
            from psycopg_pool import ConnectionPool
            from langgraph.checkpoint.postgres import PostgresSaver
            from agents import eligibilty_agent, intake_agent

            dsn = os.environ["DATABASE_URL"].replace(
                "postgresql+psycopg://", "postgresql://", 1
            )
            checkpoint_pool = ConnectionPool(
                conninfo=dsn,
                min_size=1,
                max_size=int(os.getenv("CHECKPOINT_POOL_SIZE", "3")),
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": 0,
                    "connect_timeout": 10,
                },
                timeout=10,
                open=False,
            )
            await run_in_threadpool(checkpoint_pool.open, True)
            _checkpointer = PostgresSaver(checkpoint_pool)
            await run_in_threadpool(_checkpointer.setup)
            intake_agent.configure_checkpointer(_checkpointer)
            eligibilty_agent.configure_checkpointer(_checkpointer)

        from agents.retrieval_agent import ensure_indexed

        ensure_indexed()
        expiry_task = asyncio.create_task(_expire_sessions())
        try:
            yield
        finally:
            expiry_task.cancel()
            try:
                await expiry_task
            except asyncio.CancelledError:
                pass
    finally:
        if checkpoint_pool is not None:
            await run_in_threadpool(checkpoint_pool.close)
        await run_in_threadpool(session_store.close)


def _frontend_origins() -> list[str]:
    environment = os.getenv("APP_ENV", "development").lower()
    configured = os.getenv("FRONTEND_ORIGINS", "")
    if not configured and environment == "production":
        raise RuntimeError("FRONTEND_ORIGINS must be set to your HTTPS site origin in production.")
    origins = [
        origin.strip()
        for origin in (
            configured
            or "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]
    if environment == "production":
        for origin in origins:
            parsed = urlsplit(origin)
            if parsed.scheme != "https" or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or "*" in origin:
                raise RuntimeError("Production FRONTEND_ORIGINS must contain exact HTTPS origins only.")
    return origins


class RequestGuardMiddleware:
    def __init__(self, app, max_concurrent: int) -> None:
        self.app = app
        self._slots = threading.BoundedSemaphore(max_concurrent)
        self._requests: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith("/api/"):
            await self.app(scope, receive, send)
            return

        method = scope["method"]
        if method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        address = client[0] if client else "unknown"
        path = scope["path"]
        bucket = "audio" if path.endswith("/audio") else "create" if path == "/api/sessions" else "general"
        limit = {"audio": 8, "create": 20, "general": 60}[bucket]
        key = f"{address}:{bucket}"
        now = time.monotonic()
        with self._lock:
            recent = self._requests.setdefault(key, deque())
            while recent and recent[0] <= now - 60:
                recent.popleft()
            limited = len(recent) >= limit
            if not limited:
                recent.append(now)
            if len(self._requests) > 10_000:
                self._requests = {
                    request_key: requests
                    for request_key, requests in self._requests.items()
                    if requests and requests[-1] > now - 60
                }

        if limited:
            response = JSONResponse(
                {"detail": "Too many requests. Please wait a moment and try again."},
                status_code=429,
                headers={"Retry-After": "60"},
            )
            await response(scope, receive, send)
            return

        if not self._slots.acquire(blocking=False):
            response = JSONResponse(
                {"detail": "The service is busy. Please try again shortly."},
                status_code=503,
                headers={"Retry-After": "2"},
            )
            await response(scope, receive, send)
            return
        try:
            await self.app(scope, receive, send)
        finally:
            self._slots.release()


class SecurityHeadersMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        async def send_with_headers(message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend([
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                ])
                if scope.get("scheme") == "https":
                    headers.append(
                        (b"strict-transport-security", b"max-age=31536000")
                    )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


app = FastAPI(title="SchemeSage API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    RequestGuardMiddleware,
    max_concurrent=max(1, int(os.getenv("MAX_CONCURRENT_REQUESTS", "8"))),
)
app.add_middleware(SecurityHeadersMiddleware)
if os.getenv("APP_ENV", "development").lower() == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins(),
    allow_credentials=True,
    allow_methods=["DELETE", "GET", "POST", "PUT"],
    allow_headers=["Content-Type"],
)


def _session_or_404(session_id: str) -> ConversationSession:
    try:
        uuid.UUID(session_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="Conversation session not found.") from error

    payload = session_store.get(session_id)
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation session not found.",
        )
    with _session_locks_guard:
        lock = _session_locks.setdefault(session_id, threading.RLock())
    return ConversationSession.from_payload(session_id, payload, lock)


def _save_session(session: ConversationSession) -> None:
    session_store.save(session.session_id, session.to_payload())


def _event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _is_timeout_error(error: Exception) -> bool:
    pending: list[BaseException] = [error]
    visited: set[int] = set()
    while pending and len(visited) < 16:
        current = pending.pop()
        if id(current) in visited:
            continue
        visited.add(id(current))
        if "timeout" in type(current).__name__.lower():
            return True
        for attribute in ("__cause__", "__context__", "reason"):
            nested = getattr(current, attribute, None)
            if isinstance(nested, BaseException):
                pending.append(nested)
    return False


def _stream(
    operation: Callable[[Callable[[str], None]], Any],
    initial_status: str = "processing",
    failure_message: Callable[[Exception], str] | None = None,
) -> StreamingResponse:
    return StreamingResponse(
        _stream_events(operation, initial_status, failure_message=failure_message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_events(
    operation: Callable[[Callable[[str], None]], Any],
    initial_status: str,
    transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    failure_message: Callable[[Exception], str] | None = None,
):
    yield _event("status", {"status": initial_status})
    loop = asyncio.get_running_loop()
    status_queue: asyncio.Queue[str] = asyncio.Queue()

    def report_status(status: str) -> None:
        loop.call_soon_threadsafe(status_queue.put_nowait, status)

    task = asyncio.create_task(run_in_threadpool(operation, report_status))
    try:
        while not task.done():
            try:
                status = await asyncio.wait_for(status_queue.get(), timeout=15)
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
                continue
            yield _event("status", {"status": status})

        while not status_queue.empty():
            yield _event("status", {"status": status_queue.get_nowait()})

        turn = TurnResponse.model_validate(await task)
        result = turn.model_dump()
        if transform is not None:
            result = transform(result)
    except Exception as error:
        category = "provider timeout" if _is_timeout_error(error) else "processing failure"
        logger.error(
            "SchemeSage request failed (%s; %s).",
            category,
            type(error).__name__,
        )
        yield _event(
            "error",
            {
                "message": (
                    failure_message(error)
                    if failure_message
                    else "We could not process that request. Please try again."
                )
            },
        )
        return

    if turn.details.locale:
        yield _event("status", {"status": "preparing_voice"})
        try:
            from agents.audio_utils import synthesize_speech

            audio_task = asyncio.create_task(
                run_in_threadpool(
                    synthesize_speech, turn.reply, turn.details.locale
                )
            )
            while not audio_task.done():
                try:
                    await asyncio.wait_for(asyncio.shield(audio_task), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
            audio = await audio_task
            result["audio_base64"] = base64.b64encode(audio).decode("ascii")
        except Exception as error:
            logger.warning("Voice synthesis unavailable (%s).", type(error).__name__)
            result["audio_error"] = "Speech service is temporarily unavailable."

    yield _event("reply", result)
    yield _event("status", {"status": "complete"})


def _start_language_session(session: ConversationSession, language: str) -> dict[str, Any]:
    from agents import intake_agent

    session.language = language
    session.locale = LANGUAGES[language]
    intake_agent.start_turn_session(session.session_id, language)
    try:
        result = intake_agent.handle_turn(session.session_id, "Hello")
    except Exception:
        intake_agent.end_turn_session(session.session_id)
        raise
    session.stage = "intake"
    session.profile = result["details"]
    session.optional_details_asked = result["optional_details_asked"]
    return {
        "session_id": session.session_id,
        "stage": session.stage,
        "reply": result["reply"],
        "details": session.details(),
    }


def _start_language_session_safely(
    session: ConversationSession,
    language: str,
    report_status: Callable[[str], None],
) -> dict[str, Any]:
    with session.lock:
        current_payload = session_store.get(session.session_id)
        if current_payload is None:
            raise HTTPException(status_code=404, detail="Conversation session expired.")
        if current_payload.get("stage") != "language":
            raise HTTPException(status_code=409, detail="The language is already set.")
        report_status("asking_first_question")
        result = _start_language_session(session, language)
        _save_session(session)
        return result


def _process_text(
    session: ConversationSession,
    text: str,
    report_status: Callable[[str], None],
) -> dict[str, Any]:
    if session.stage == "intake":
        from agents import intake_agent

        intake_agent.resume_turn_session(
            session.session_id,
            session.language or "English",
            session.profile,
            session.optional_details_asked,
        )
        result = intake_agent.handle_turn(session.session_id, text)
        session.profile = result["details"]
        session.optional_details_asked = result["optional_details_asked"]
        if result["confirmed"]:
            session.stage = "matching"
            _save_session(session)
            reply = _start_scheme_selection(session, report_status)
        else:
            reply = result["reply"]
    elif session.stage == "matching":
        reply = _start_scheme_selection(session, report_status)
    elif session.stage == "selection":
        from agents import eligibilty_agent

        eligibilty_agent.resume_turn_session(
            session.session_id,
            session.profile,
            session.language or "English",
            session.locale or "en-IN",
            session.ranked_schemes or "",
            session.selected_schemes,
        )
        result = eligibilty_agent.handle_turn(session.session_id, text)
        session.ranked_schemes = result["details"]["ranked_schemes"]
        session.selected_schemes = result["details"]["selected_schemes"]
        reply = result["reply"]
        if result["confirmed"]:
            session.stage = "checklist"
            _save_session(session)
            reply = _build_checklist(session, report_status)
    elif session.stage == "checklist":
        reply = _build_checklist(session, report_status)
    elif session.stage == "complete":
        raise HTTPException(
            status_code=409,
            detail=(
                "This conversation has completed its document checklist."
            ),
        )
    else:
        raise HTTPException(
            status_code=409,
            detail="Choose a language before sending a message.",
        )

    return {
        "session_id": session.session_id,
        "stage": session.stage,
        "reply": reply,
        "details": session.details(),
    }


def _start_scheme_selection(
    session: ConversationSession,
    report_status: Callable[[str], None],
) -> str:
    from agents import eligibilty_agent

    report_status("matching_schemes")
    selection = eligibilty_agent.start_turn_session(
        session.session_id,
        session.profile,
        session.language or "English",
        session.locale or "en-IN",
    )
    session.ranked_schemes = selection["details"]["ranked_schemes"]
    session.selected_schemes = selection["details"]["selected_schemes"]
    session.stage = "selection"
    _save_session(session)
    return selection["reply"]


def _build_checklist(
    session: ConversationSession,
    report_status: Callable[[str], None],
) -> str:
    report_status("building_checklist")
    from agents.document_agent import build_session_checklist

    checklist = build_session_checklist(
        session.profile,
        session.selected_schemes,
        session.language or "English",
    )
    session.scheme_details = checklist["schemes"]
    session.document_checklist = checklist["checklist"]
    session.stage = "complete"
    _save_session(session)
    return checklist["reply"]


def _start_language_session_persisted(
    session: ConversationSession,
    language: str,
    report_status: Callable[[str], None],
) -> dict[str, Any]:
    return _start_language_session_safely(session, language, report_status)


def _process_text_persisted(
    session: ConversationSession,
    text: str,
    report_status: Callable[[str], None],
) -> dict[str, Any]:
    with session.lock:
        payload = session_store.get(session.session_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Conversation session expired.")
        latest = ConversationSession.from_payload(
            session.session_id, payload, session.lock
        )
        session.stage = latest.stage
        session.language = latest.language
        session.locale = latest.locale
        session.profile = latest.profile
        session.optional_details_asked = latest.optional_details_asked
        session.ranked_schemes = latest.ranked_schemes
        session.selected_schemes = latest.selected_schemes
        session.scheme_details = latest.scheme_details
        session.document_checklist = latest.document_checklist
        if session.stage == "complete":
            raise HTTPException(
                status_code=409,
                detail="This conversation has completed its document checklist.",
            )
        result = _process_text(session, text, report_status)
        _save_session(session)
        return result


@app.get("/api/health")
@app.get("/health", include_in_schema=False)
def health_check() -> dict[str, str]:
    try:
        session_store.ping()
    except Exception as error:
        logger.error("Session database health check failed (%s).", type(error).__name__)
        raise HTTPException(
            status_code=503,
            detail="Conversation storage is temporarily unavailable.",
        ) from error
    return {
        "status": "ok",
        "storage": "postgres" if session_store.persistent else "in-memory",
    }


@app.post("/api/sessions", status_code=201)
def create_session(request: ConsentRequest) -> dict[str, str]:
    if not request.accepted or request.notice_version != PRIVACY_NOTICE_VERSION:
        raise HTTPException(
            status_code=422,
            detail="Please review and accept the current privacy notice to continue.",
        )
    session_id = str(uuid.uuid4())
    session_store.create(
        session_id,
        ConversationSession(
            session_id=session_id,
            consented_at=datetime.now(timezone.utc).isoformat(),
            consent_notice_version=request.notice_version,
        ).to_payload(),
    )
    return {"session_id": session_id, "stage": "language"}


@app.delete("/api/sessions/{session_id}", status_code=204)
def delete_session(session_id: str) -> None:
    session = _session_or_404(session_id)
    with session.lock:
        from agents import intake_agent

        intake_agent.end_turn_session(session_id)
        if session.stage in {"matching", "selection", "checklist", "complete"}:
            from agents import eligibilty_agent

            eligibilty_agent.end_turn_session(session_id)
        session_store.delete(session_id)
        with _session_locks_guard:
            _session_locks.pop(session_id, None)


@app.put(
    "/api/sessions/{session_id}/language",
    response_class=StreamingResponse,
    responses=SSE_RESPONSES,
)
def choose_language(session_id: str, request: LanguageRequest) -> StreamingResponse:
    session = _session_or_404(session_id)
    if request.language not in LANGUAGES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported language. Choose one of: {', '.join(LANGUAGES)}.",
        )
    if session.stage != "language":
        raise HTTPException(status_code=409, detail="The language is already set.")

    return _stream(
        lambda report: _start_language_session_persisted(
            session, request.language, report
        ),
        initial_status="starting",
    )


@app.post(
    "/api/sessions/{session_id}/messages",
    response_class=StreamingResponse,
    responses=SSE_RESPONSES,
)
def send_message(session_id: str, request: MessageRequest) -> StreamingResponse:
    session = _session_or_404(session_id)
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Message text cannot be empty.")
    if session.stage == "language":
        raise HTTPException(
            status_code=409,
            detail="Choose a language before sending a message.",
        )
    if session.stage == "complete":
        raise HTTPException(
            status_code=409,
            detail="This conversation has completed its document checklist.",
        )

    return _stream(
        lambda report: _process_text_persisted(session, text, report),
        initial_status="thinking",
        failure_message=lambda error: (
            (
                "Scheme matching timed out while contacting the AI service. "
                "Your profile is saved; select Retry to try again."
                if _is_timeout_error(error)
                else "Scheme matching is temporarily unavailable. Your profile "
                "is saved; select Retry to continue."
            )
            if session.stage == "matching"
            else "We could not process that request. Select Retry to try again."
        ),
    )


@app.post(
    "/api/sessions/{session_id}/audio",
    response_class=StreamingResponse,
    responses=SSE_RESPONSES,
)
async def send_audio(
    session_id: str,
    audio: UploadFile = File(...),
) -> StreamingResponse:
    session = await run_in_threadpool(_session_or_404, session_id)
    if not session.locale:
        raise HTTPException(
            status_code=409,
            detail="Choose a language before sending audio.",
        )
    if session.stage == "complete":
        raise HTTPException(
            status_code=409,
            detail="This conversation has completed its document checklist.",
        )
    payload = await audio.read(MAX_AUDIO_BYTES + 1)
    await audio.close()
    if not payload:
        raise HTTPException(status_code=422, detail="The audio file is empty.")
    if len(payload) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio files must be 20 MB or smaller.")

    filename = os.path.basename(audio.filename or "recording.wav")
    return _audio_stream(session, payload, filename)


def _transcribe_upload(payload: bytes, filename: str, locale: str) -> str:
    from agents.audio_utils import convert_audio_to_wav, speech_to_text_bytes

    wav_data = convert_audio_to_wav(payload, filename)
    return speech_to_text_bytes(wav_data, "recording.wav", locale)


def _audio_stream(
    session: ConversationSession,
    payload: bytes,
    filename: str,
) -> StreamingResponse:
    async def events():
        yield _event("status", {"status": "transcribing"})
        try:
            text = await run_in_threadpool(
                _transcribe_upload, payload, filename, session.locale or "en-IN"
            )
            if not text:
                yield _event(
                    "error",
                    {"message": "We could not understand the audio. Please try again."},
                )
                return
            yield _event("status", {"status": "thinking"})
        except (RuntimeError, ValueError) as error:
            logger.warning("Could not process uploaded audio (%s).", type(error).__name__)
            yield _event("error", {"message": str(error)})
            return
        except Exception as error:
            logger.error("SchemeSage audio request failed (%s).", type(error).__name__)
            yield _event(
                "error",
                {"message": "We could not process that audio. Please try again."},
            )
            return
        async for event in _stream_events(
            lambda report: _process_text_persisted(session, text, report),
            "thinking",
            transform=lambda result: {**result, "transcript": text},
        ):
            yield event

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
