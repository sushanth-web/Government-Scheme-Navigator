import json
import os

from agents.retrieval_agent import retrieval_agent, DATA_DIR
from agents.intake_agent import load_profile, load_language
from typing import Optional

from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from agents.audio_utils import get_user_query, require_api_key, tell
from agents.http_clients import create_retry_session


load_dotenv()

SELECTED_FILE = os.path.join(DATA_DIR, "selected_schemes.json")


# 2. The ranking prompt (it was a global before, now it is built from any profile)
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

Return the result as a ranked list, best match first:
Rank. Scheme name
- Status:
- Why it matches: (criteria I meet)
- What does not match or is unknown: (criteria I fail or that my profile
  does not cover)
- Benefit: (amount or support, if stated)
- Source: (document name and page)

Put "Not eligible" schemes at the end with the reason.
Use only what the documents say. If a detail is missing, write
"not found in documents".
"""


# 3. LLM
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
        timeout=180,
        max_completion_tokens=1024,
    )
    model._client.get_session_fn = create_retry_session
    return model


# 5. Shared data used by the tools
ranked = {"text": ""}          # the ranked list, filled by select_schemes()
selected_schemes = []          # the schemes the user chose
confirmed = {"done": False}

_turn_sessions = {}
_turn_checkpointer = InMemorySaver()


def configure_checkpointer(checkpointer) -> None:
    global _turn_checkpointer
    _turn_checkpointer = checkpointer


@tool
def update_scheme(schemes: list[str]) -> str:
    """Save the schemes the user wants to apply to. Pass the exact scheme
    names from the ranked list, in English. Only pass the schemes the
    user just chose."""

    not_found = []

    for name in schemes:
        if name.lower() not in ranked["text"].lower():
            not_found.append(name)
        elif name not in selected_schemes:
            selected_schemes.append(name)

    message = f"Saved. Schemes selected so far: {selected_schemes}"

    if not_found:
        message += f" NOT saved, not in the ranked list: {not_found}. Check the exact name."

    return message


@tool
def remove_scheme(schemes: list[str]) -> str:
    """Remove schemes the user does not want any more. Pass the exact
    scheme names."""

    for name in schemes:
        if name in selected_schemes:
            selected_schemes.remove(name)

    return f"Removed. Schemes selected so far: {selected_schemes}"


@tool
def confirm_scheme() -> str:
    """Call this only after the user has confirmed that the list
    of selected schemes is correct."""

    if not selected_schemes:
        return "No scheme is saved yet. Ask the user which schemes they want."

    confirmed["done"] = True
    return "Schemes confirmed."


# 6. The voice agent
def build_agent(language: str, ranked_schemes: str):
    return create_agent(
        model=get_llm(),
        tools=[update_scheme, remove_scheme, confirm_scheme],
        system_prompt=f"""
        You are a voice assistant that helps people find government
        schemes in Andhra Pradesh.

        The user speaks {language}. Always reply in {language}.

        Your replies are spoken aloud, so:
        - Use plain text only. No markdown, no bullet points, no emojis.
        - Keep every reply short, at most three short sentences. The only
          exception is your first message, which lists the eligible schemes.
        - Speak scheme names and benefits in {language}. Translate the
          scheme name into {language} script so the voice can read it.
          But when you call a tool, always use the exact English scheme
          name from the ranked list.

        Here are all the schemes, already ranked from best to least suited
        for this user:
        {ranked_schemes}

        Your job is to collect:
        - the schemes the user wants to apply to, chosen from the ranked list above
        - if the user picks a scheme that is Not eligible, tell the user it is not a good match and why. If the user insists on that scheme, save it anyway.

        Rules:
        1. In your first message, tell the user in {language} ALL the
           schemes that are Eligible or Likely eligible, best first, each
           with its benefit in a few words. Then say how many other
           schemes need more details or are not a good match, and ask
           which schemes the user wants to apply to.
        2. Ask only ONE simple question at a time.
        3. When the user picks schemes (by name or by position, like "the
           first one"), call update_scheme with the exact English scheme
           names from the ranked list.
        4. If the user changes their mind, call remove_scheme.
        5. If the user asks about a scheme, answer only from the ranked
           list above.
        6. Never ask for Aadhaar, phone number or bank details.
        7. When the user says they are done choosing, read the chosen
           schemes back in {language} and ask the user to confirm.
        8. When the user confirms, call confirm_scheme.
        """,
        checkpointer=InMemorySaver(),
    )


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

    ranked_text = ranked_schemes or retrieval_agent(build_query(profile_data))
    state = {"selected_schemes": list(selected or []), "confirmed": False}

    @tool
    def save_selected_schemes(schemes: list[str]) -> str:
        """Save exact scheme names selected from the ranked list."""
        not_found = [
            name for name in schemes
            if name.lower() not in ranked_text.lower()
        ]
        for name in schemes:
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
            if name in state["selected_schemes"]:
                state["selected_schemes"].remove(name)
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

        Ranked schemes:
        {ranked_text}

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
        "reply": response["messages"][-1].content,
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
    _turn_checkpointer.delete_thread(f"{session_id}:selection")


languages = {
    "1": ("English", "en-IN"),
    "2": ("Telugu", "te-IN"),
    "3": ("Hindi", "hi-IN"),
}


# 7. The function other files import: rank the schemes, let the user choose
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

    # take the details from the intake agent
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