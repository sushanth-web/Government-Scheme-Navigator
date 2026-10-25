import json
import os
import re
import uuid
from typing import Optional

from dotenv import load_dotenv
from langchain.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from agents.retrieval_agent import retrieval_agent, rank_schemes, DATA_DIR
from agents.intake_agent import load_profile, load_language
from agents.audio_utils import get_user_query, require_api_key, tell
from agents.llm_utils import FAST_MODEL, build_chat_model, speakable


load_dotenv()

SELECTED_FILE = os.path.join(DATA_DIR, "selected_schemes.json")


# The ranking prompt, built from any profile
def build_query(profile: dict) -> str:
    profile_text = json.dumps(profile, indent=2)

    return f"""
Here is my profile:
{profile_text}

Compare my profile against EVERY scheme in the uploaded documents and
rank all the schemes from best suited to least suited for me.

For each scheme, do the following:
1. Search the documents for that scheme's eligibility criteria.
2. Check each criterion against my profile (age, occupation, district,
   annual income, land, caste category, household size, student course, and
   disability relevance).
3. Give a status: Eligible, Likely eligible, Need more info, or Not eligible.
4. Quote the exact rule from the document that supports your status.

Return PLAIN TEXT only. No markdown, no tables, no bold, no symbols, no
introduction and no explanation of how you ranked. One block per scheme,
best match first, with a blank line between blocks, in exactly this layout:

Rank 1: Scheme name
Status: Eligible, Likely eligible, Need more info, or Not eligible
Matches: criteria I meet
Unknown or fails: criteria I fail or that my profile does not cover
Benefit: amount or support, if stated
Source: document name and page

Put "Not eligible" schemes at the end with the reason.
Use only what the documents say. If a detail is missing, write
"not found in documents".
"""


# The spoken selection conversation: fast model, short replies
def get_llm(
    model_name: str = FAST_MODEL,
    temperature: float = 0.3,
):
    return build_chat_model(model_name, temperature, timeout=180, max_tokens=1500)


_STATUS_WORDS = ("eligible", "likely eligible", "need more info", "not eligible")


def _looks_ranked(text: str) -> bool:
    """A usable ranking names at least one scheme with a status."""
    lowered = (text or "").lower()
    return len(lowered) > 80 and "status" in lowered and any(w in lowered for w in _STATUS_WORDS)


def _rank(profile_data: dict) -> str:
    """Rank all schemes: direct single-call ranking first, the tool agent as
    a backup. Never returns an empty ranking, so the chat cannot wrongly
    claim that no schemes exist."""
    known = {k: v for k, v in profile_data.items() if v not in (None, "")}
    evidence_query = ", ".join(f"{k}: {v}" for k, v in known.items())
    prompt = build_query(profile_data)

    for attempt in (rank_schemes, None):
        try:
            text = (
                rank_schemes(prompt, evidence_query)
                if attempt
                else retrieval_agent(prompt)
            )
        except Exception:
            if attempt is None:
                raise
            continue
        if _looks_ranked(text):
            return text
    raise RuntimeError("Scheme ranking returned no usable result. Please retry.")


_turn_sessions = {}
_turn_checkpointer = InMemorySaver()


def configure_checkpointer(checkpointer) -> None:
    global _turn_checkpointer
    _turn_checkpointer = checkpointer


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def start_turn_session(
    session_id: str,
    profile_data: dict,
    language: str,
    locale: str,
    ranked_schemes: Optional[str] = None,
    selected: Optional[list[str]] = None,
    resume: bool = False,
) -> dict:
    """Rank schemes and create an isolated, checkpointed selection conversation."""
    if session_id in _turn_sessions and not resume:
        end_turn_session(session_id)

    ranked_text = ranked_schemes or _rank(profile_data)
    ranked_norm = _norm(ranked_text)
    state = {"selected_schemes": list(selected or []), "confirmed": False}

    @tool
    def save_selected_schemes(schemes: list[str]) -> str:
        """Save exact scheme names selected from the ranked list."""
        not_found = [
            name for name in schemes
            if not _norm(name) or _norm(name) not in ranked_norm
        ]
        for name in schemes:
            name = name.strip()
            if name not in not_found and name not in state["selected_schemes"]:
                state["selected_schemes"].append(name)
        return (
            f"Saved. Schemes selected so far: {state['selected_schemes']}"
            + (f" Not saved because they were not in the ranked list: {not_found}." if not_found else "")
        )

    @tool
    def remove_selected_schemes(schemes: list[str]) -> str:
        """Remove schemes the user no longer wants to apply for."""
        for name in schemes:
            for saved in list(state["selected_schemes"]):
                if _norm(saved) == _norm(name):
                    state["selected_schemes"].remove(saved)
        return f"Removed. Schemes selected so far: {state['selected_schemes']}"

    @tool
    def confirm_selected_schemes() -> str:
        """Confirm the selection only after the user confirms it."""
        if not state["selected_schemes"]:
            return "No scheme is saved yet. Ask the user which schemes they want."
        state["confirmed"] = True
        return "Schemes confirmed."

    agent = create_agent(
        model=get_llm(),
        tools=[
            save_selected_schemes,
            remove_selected_schemes,
            confirm_selected_schemes,
        ],
        system_prompt=f"""
        You help people find government schemes in Andhra Pradesh. The user
        speaks {language}; always reply in {language}. Use plain text without
        markdown, and keep replies to at most three short sentences except for
        the first message. Speak scheme names in {language}, but use exact
        English names when calling tools.

        Here is the ranked scheme data. It is for your reference only. Never
        print, quote, copy or summarize it as a list or table, and never add
        any section after your reply. Reply only in short spoken sentences with
        no bullet points, no tables, no bold text, no symbols and no emojis.

        <ranked_schemes>
        {ranked_text}
        </ranked_schemes>

        The user's profile is already complete. Never ask again for age,
        gender, occupation, district, income or any other profile detail:
        {json.dumps({k: v for k, v in profile_data.items() if v not in (None, "")}, ensure_ascii=False)}

        In your first message, list every Eligible and Likely eligible scheme,
        then also list schemes marked Need more info with the exact missing
        criteria. Do not treat unknown profile values as proof of ineligibility.
        Only say there are no suitable schemes when the ranked evidence marks
        every relevant scheme Not eligible. If the user asks about a category
        (such as education or scholarships), identify matching scheme entries
        from the ranked list and explain their status instead of claiming that
        no schemes of that type exist. Include benefits when provided, then ask
        which schemes the user wants. Ask one simple question at a time. Use
        save_selected_schemes for chosen names and
        remove_selected_schemes when the user changes their mind. Explain
        when a chosen scheme is marked Not eligible, but save it if the user
        insists. Once the user is done, read the choices back and ask for
        confirmation. Call confirm_selected_schemes only after confirmation.
        Never ask for Aadhaar, phone, bank details, passwords or OTPs.
        """,
        checkpointer=_turn_checkpointer,
    )
    _turn_sessions[session_id] = {
        "agent": agent,
        "state": state,
        "ranked_schemes": ranked_text,
        "profile": dict(profile_data),
        "language": language,
        "locale": locale,
    }
    if resume:
        return {}
    try:
        return handle_turn(session_id, "Hello")
    except Exception:
        end_turn_session(session_id)
        raise


def has_turn_session(session_id: str) -> bool:
    return session_id in _turn_sessions


def resume_turn_session(
    session_id: str,
    profile_data: dict,
    language: str,
    locale: str,
    ranked_schemes: str,
    selected: list[str],
) -> None:
    if not has_turn_session(session_id):
        start_turn_session(
            session_id,
            profile_data,
            language,
            locale,
            ranked_schemes=ranked_schemes,
            selected=selected,
            resume=True,
        )


def handle_turn(session_id: str, text: str) -> dict:
    """Process one scheme-selection message and return the updated selection."""
    session = _turn_sessions.get(session_id)
    if session is None:
        raise KeyError(f"No scheme-selection session exists for {session_id}.")
    response = session["agent"].invoke(
        {"messages": [{"role": "user", "content": text}]},
        {"configurable": {"thread_id": f"{session_id}:selection"}},
    )
    state = session["state"]
    return {
        "reply": speakable(response["messages"][-1].content),
        "details": {
            "ranked_schemes": session["ranked_schemes"],
            "selected_schemes": list(state["selected_schemes"]),
            "language": session["language"],
            "locale": session["locale"],
        },
        "confirmed": state["confirmed"],
    }


def end_turn_session(session_id: str) -> None:
    _turn_sessions.pop(session_id, None)
    try:
        _turn_checkpointer.delete_thread(f"{session_id}:selection")
    except Exception:
        pass


languages = {
    "1": ("English", "en-IN"),
    "2": ("Telugu", "te-IN"),
    "3": ("Hindi", "hi-IN"),
}


# The function other files import: rank the schemes, let the user choose
def select_schemes(
    profile: Optional[dict] = None,
    language: Optional[str] = None,
    locale: Optional[str] = None,
) -> Optional[dict]:
    """Compare the profile with all the schemes in the documents, tell the
    user the best ones by voice and let them choose. Returns a dict:

        {"ranked_schemes": "<ranked text>",
         "selected_schemes": ["Scheme A", "Scheme B"],
         "language": "Telugu", "locale": "te-IN"}

    profile: the dict from the intake agent (get_profile). If you do not
        pass it, the profile saved by the intake agent is loaded.
    language, locale: for example "Telugu", "te-IN". If you do not pass
        them, the language the user chose in the intake agent is used
        (and only if there is none, the user is asked).

    Returns None if the user quits before confirming.
    The result is also saved to data/selected_schemes.json.
    """

    # check the key BEFORE the slow ranking step
    require_api_key()

    if profile is None:
        profile = load_profile()

    if not (language and locale):
        try:
            language, locale = load_language()
        except FileNotFoundError:
            pass

    if not (language and locale):
        choice = input("Choose language (1. English  2. Telugu  3. Hindi): ").strip()
        language, locale = languages.get(choice, languages["1"])

    print("Comparing your profile with all the schemes, please wait...")
    session_id = str(uuid.uuid4())
    turn = start_turn_session(session_id, profile, language, locale)
    try:
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

        details = turn["details"]
        print("\nSelected schemes:", details["selected_schemes"])
        os.makedirs(DATA_DIR, exist_ok=True)

        with open(SELECTED_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "profile": profile,
                    "language": language,
                    "locale": locale,
                    "selected_schemes": details["selected_schemes"],
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        print("Saved to:", SELECTED_FILE)
        return details
    finally:
        end_turn_session(session_id)


if __name__ == "__main__":
    # run get_profile() (intake agent) first, this reads what it saved
    select_schemes()