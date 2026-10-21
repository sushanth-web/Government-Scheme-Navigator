import json
import os
import uuid
from typing import Optional

from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver


from agents.audio_utils import get_user_query, require_api_key, tell
from agents.http_clients import create_retry_session


load_dotenv()

# the profile is saved here so other agents can read it later
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PROFILE_FILE = os.path.join(DATA_DIR, "profile.json")


# 2. Initialize the LLM
def get_llm(
    model_name: str = "nvidia/nemotron-3.5-super-vl-120b-a12b",
    temperature: float = 0.3,
):
    api_key = os.getenv("NVIDIA_API_KEY")

    if not api_key:
        raise ValueError("Please set the NVIDIA_API_KEY environment variable.")

    model = ChatNVIDIA(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        timeout=90,
        max_completion_tokens=1024,
    )
    model._client.get_session_fn = create_retry_session
    return model


# 6. The user profile we want to fill (stored in English)
REQUIRED_FIELDS = ["age", "gender", "occupation", "district", "annual_income"]

profile = {
    "age": None,
    "gender": None,
    "occupation": None,
    "district": None,
    "annual_income": None,
    "land_acres": None,
    "caste_category": None,
    "household_size": None,
    "student_course": None,
    "disability_status": None,
}

confirmed = {"done": False}

_turn_sessions = {}
_turn_checkpointer = InMemorySaver()


def configure_checkpointer(checkpointer) -> None:
    global _turn_checkpointer
    _turn_checkpointer = checkpointer


# 7. Tool: save what the user told us
@tool
def update_profile(
    age: Optional[int] = None,
    gender: Optional[str] = None,
    occupation: Optional[str] = None,
    district: Optional[str] = None,
    annual_income: Optional[int] = None,
    land_acres: Optional[float] = None,
    caste_category: Optional[str] = None,
    household_size: Optional[int] = None,
    student_course: Optional[str] = None,
    disability_status: Optional[str] = None,
) -> str:
    """Save profile details the user has told you. Only pass the fields
    the user actually mentioned. Returns which required fields are
    still missing."""

    updates = {
        "age": age,
        "gender": gender,
        "occupation": occupation,
        "district": district,
        "annual_income": annual_income,
        "land_acres": land_acres,
        "caste_category": caste_category,
        "household_size": household_size,
        "student_course": student_course,
        "disability_status": disability_status,
    }

    for key, value in updates.items():
        if value is not None:
            profile[key] = value

    missing = [f for f in REQUIRED_FIELDS if profile[f] is None]

    if missing:
        return f"Saved. Still missing: {missing}"

    if not confirmed.get("optional_details_asked", False):
        confirmed["optional_details_asked"] = True
        return (
            "Saved. Ask once whether the user wants to share optional details "
            "(household size, student course, disability relevance, land, or "
            "caste category), or skip them. Then summarize and ask for confirmation."
        )
    return "Saved. Summarize the profile and ask the user to confirm."


# 8. Tool: mark the profile as confirmed
@tool
def confirm_profile() -> str:
    """Call this only after the user has confirmed that the summary
    of their profile is correct."""

    confirmed["done"] = True
    return "Profile confirmed."


@tool
def skip_optional_profile_details() -> str:
    """Continue without collecting optional profile details."""
    confirmed["optional_details_asked"] = True
    return "Optional details skipped. Summarize the profile and ask for confirmation."


# 9. Create the agent
def build_agent(language: str):
    return create_agent(
        model=get_llm(),
        tools=[update_profile, skip_optional_profile_details, confirm_profile],
        system_prompt=f"""
        You are a voice assistant that helps people find government
        schemes in Andhra Pradesh.

        The user speaks {language}. Always reply in {language}.

        Your replies are spoken aloud, so:
        - Use plain text only. No markdown, no bullet points, no emojis.
        - Keep every reply short, at most two sentences.

        Your job is to collect these details:
        - age
        - gender (for example male, female)
        - occupation (for example farmer, student, laborer)
        - district
        - annual income in rupees
        - land in acres (only if the user is a farmer)
        - caste category: OC, BC, SC, ST, EWS or Minority (optional)
        - household size, student course, and disability relevance (optional)

        Rules:
        1. Ask only ONE simple question at a time.
        2. Whenever the user gives any detail, call update_profile
           with only those details. Save values in English
           (occupation as "farmer", numbers as digits).
        3. Do not ask again for details you already have.
        4. Leave uncertain optional values unknown. Use
           skip_optional_profile_details only if the user declines all
           optional details.
        5. Never ask for Aadhaar, phone number or bank details.
        6. After required details are collected, ask once whether the user
           wants to share optional details or skip them.
        7. Then read the details back in {language} and ask the user to confirm.
        8. When the user confirms, call confirm_profile.
        """,
        checkpointer=InMemorySaver(),
    )


def start_turn_session(
    session_id: str,
    language: str,
    profile_data: Optional[dict] = None,
    resume: bool = False,
    optional_details_asked: bool = False,
) -> None:
    """Create an isolated intake agent whose checkpoints are keyed by session."""
    if session_id in _turn_sessions and not resume:
        end_turn_session(session_id)

    saved_profile = profile_data or {key: None for key in profile}
    state = {
        "profile": dict(saved_profile),
        "confirmed": False,
        "optional_details_asked": optional_details_asked,
    }

    @tool
    def save_profile_details(
        age: Optional[int] = None,
        gender: Optional[str] = None,
        occupation: Optional[str] = None,
        district: Optional[str] = None,
        annual_income: Optional[int] = None,
        land_acres: Optional[float] = None,
        caste_category: Optional[str] = None,
        household_size: Optional[int] = None,
        student_course: Optional[str] = None,
        disability_status: Optional[str] = None,
    ) -> str:
        """Save only profile details the user has provided."""
        updates = {
            "age": age,
            "gender": gender,
            "occupation": occupation,
            "district": district,
            "annual_income": annual_income,
            "land_acres": land_acres,
            "caste_category": caste_category,
            "household_size": household_size,
            "student_course": student_course,
            "disability_status": disability_status,
        }
        for key, value in updates.items():
            if value is not None:
                state["profile"][key] = value
        missing = [key for key in REQUIRED_FIELDS if state["profile"][key] is None]
        if missing:
            return f"Saved. Still missing: {missing}"
        if not state["optional_details_asked"]:
            state["optional_details_asked"] = True
            return (
                "Saved. Ask once whether the user wants to share optional details "
                "(household size, student course, disability relevance, land, or "
                "caste category), or skip them. Then summarize and ask for confirmation."
            )
        return "Saved. Summarize the profile and ask the user to confirm."

    @tool
    def skip_optional_details() -> str:
        """Use only when the user skips all optional profile details."""
        state["optional_details_asked"] = True
        return "Optional details skipped. Summarize the profile and ask for confirmation."

    @tool
    def confirm_profile_details() -> str:
        """Mark the profile confirmed only after the user confirms it."""
        state["confirmed"] = True
        return "Profile confirmed."

    agent = create_agent(
        model=get_llm(),
        tools=[
            save_profile_details,
            skip_optional_details,
            confirm_profile_details,
        ],
        system_prompt=f"""
        You help people find government schemes in Andhra Pradesh. The user
        speaks {language}; always reply in {language}. Replies are spoken
        aloud: use plain text, no markdown, and at most two short sentences.

        Collect age, gender, occupation, district, and annual income in
        rupees. Optional details are land in acres for farmers, caste category
        (OC, BC, SC, ST, EWS or Minority), household size, student course, and
        disability relevance. Ask one optional follow-up after required
        details. Explain that "not sure", "prefer not to say", or "skip" is
        accepted and does not stop matching. Never infer an optional value.

        Ask one simple question at a time. When the user provides details, call
        save_profile_details with only those details, saving values in English.
        Do not repeat details already collected. Save any optional details the
        user chooses to share; use skip_optional_details only when they skip
        all optional details. Never ask for Aadhaar, phone, bank details,
        passwords or OTPs. After optional details are answered or skipped,
        read the profile back and ask the user to confirm.
        Call confirm_profile_details only after the user confirms.
        """,
        checkpointer=_turn_checkpointer,
    )
    _turn_sessions[session_id] = {"agent": agent, "state": state}


def has_turn_session(session_id: str) -> bool:
    return session_id in _turn_sessions


def resume_turn_session(
    session_id: str,
    language: str,
    profile_data: dict,
    optional_details_asked: bool = False,
) -> None:
    if not has_turn_session(session_id):
        start_turn_session(
            session_id,
            language,
            profile_data,
            resume=True,
            optional_details_asked=optional_details_asked,
        )


def handle_turn(session_id: str, text: str) -> dict:
    """Process exactly one user message and return the reply and profile."""
    session = _turn_sessions.get(session_id)
    if session is None:
        raise KeyError(f"No intake session exists for {session_id}.")

    response = session["agent"].invoke(
        {"messages": [{"role": "user", "content": text}]},
        {"configurable": {"thread_id": f"{session_id}:intake"}},
    )
    return {
        "reply": response["messages"][-1].content,
        "details": dict(session["state"]["profile"]),
        "confirmed": session["state"]["confirmed"],
        "optional_details_asked": session["state"]["optional_details_asked"],
    }


def end_turn_session(session_id: str) -> None:
    _turn_sessions.pop(session_id, None)
    _turn_checkpointer.delete_thread(f"{session_id}:intake")


# 10. Choose the language
languages = {
    "1": ("English", "en-IN"),
    "2": ("Telugu", "te-IN"),
    "3": ("Hindi", "hi-IN"),
}


# 11. The function other files import: run the voice intake, return the profile
def get_profile(
    language: Optional[str] = None,
    locale: Optional[str] = None,
) -> Optional[dict]:
    """Ask the user their details by voice and return the confirmed profile
    as a dict, for example {"age": 18, "gender": "female", ...}.

    Pass language and locale (for example "Telugu", "te-IN") to skip the
    language question. Returns None if the user quits before confirming.
    The profile is also saved to data/profile.json (see load_profile).
    """

    require_api_key()

    # start fresh, in case this function is called more than once
    for key in profile:
        profile[key] = None
    confirmed["done"] = False
    confirmed["optional_details_asked"] = False

    if not (language and locale):
        choice = input("Choose language (1. English  2. Telugu  3. Hindi): ").strip()
        language, locale = languages.get(choice, languages["1"])

    session_id = str(uuid.uuid4())
    start_turn_session(session_id, language)
    try:
        turn = handle_turn(session_id, "Hello")
        tell(turn["reply"], locale)
        while not turn["confirmed"]:
            query = get_user_query(locale)
            if query is None:
                continue
            if query.lower() in ["exit", "bye"]:
                return None

            print("user:", query)
            turn = handle_turn(session_id, query)
            tell(turn["reply"], locale)

        result = turn["details"]
        print("\nFinal profile:", result)
        os.makedirs(DATA_DIR, exist_ok=True)

        with open(PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"language": language, "locale": locale, "profile": result},
                f,
                indent=2,
                ensure_ascii=False,
            )

        return result
    finally:
        end_turn_session(session_id)


def load_profile() -> dict:
    """Return the profile saved by get_profile(), without asking any questions."""

    if not os.path.exists(PROFILE_FILE):
        raise FileNotFoundError(f"{PROFILE_FILE} not found. Run get_profile() first.")

    with open(PROFILE_FILE, encoding="utf-8") as f:
        return json.load(f)["profile"]


def load_language() -> tuple:
    """Return (language, locale) saved by get_profile(), for example
    ("Telugu", "te-IN"), so other agents speak the same language."""

    if not os.path.exists(PROFILE_FILE):
        raise FileNotFoundError(f"{PROFILE_FILE} not found. Run get_profile() first.")

    with open(PROFILE_FILE, encoding="utf-8") as f:
        saved = json.load(f)

    return saved["language"], saved["locale"]


if __name__ == "__main__":
    get_profile()