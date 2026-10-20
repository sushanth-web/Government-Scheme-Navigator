import json
import os
from typing import Optional

from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from agents.audio_utils import get_user_query, require_api_key, tell


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

    return ChatNVIDIA(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        timeout=180,
        max_completion_tokens=1024,
    )


# 6. The user profile we want to fill (stored in English)
REQUIRED_FIELDS = ["age","gender", "occupation", "district", "annual_income"]

profile = {
    "age": None,
    "gender": None,
    "occupation": None,
    "district": None,
    "annual_income": None,
    "land_acres": None,
    "caste_category": None,
}

confirmed = {"done": False}


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
    }

    for key, value in updates.items():
        if value is not None:
            profile[key] = value

    missing = [f for f in REQUIRED_FIELDS if profile[f] is None]

    if missing:
        return f"Saved. Still missing: {missing}"

    return "Saved. All required fields are collected. Now confirm with the user."


# 8. Tool: mark the profile as confirmed
@tool
def confirm_profile() -> str:
    """Call this only after the user has confirmed that the summary
    of their profile is correct."""

    confirmed["done"] = True
    return "Profile confirmed."


# 9. Create the agent
def build_agent(language: str):
    return create_agent(
        model=get_llm(),
        tools=[update_profile, confirm_profile],
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

        Rules:
        1. Ask only ONE simple question at a time.
        2. Whenever the user gives any detail, call update_profile
           with only those details. Save values in English
           (occupation as "farmer", numbers as digits).
        3. Do not ask again for details you already have.
        4. If the user does not know or wants to skip an optional
           detail, move on.
        5. Never ask for Aadhaar, phone number or bank details.
        6. When update_profile says all required fields are
           collected, read the details back in {language} and ask
           the user to confirm.
        7. When the user confirms, call confirm_profile.
        """,
        checkpointer=InMemorySaver(),
    )


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

    if not (language and locale):
        choice = input("Choose language (1. English  2. Telugu  3. Hindi): ").strip()
        language, locale = languages.get(choice, languages["1"])

    agent = build_agent(language)
    config = {"configurable": {"thread_id": "1"}}

    def ask_agent(text: str) -> str:
        response = agent.invoke(
            {"messages": [{"role": "user", "content": text}]},
            config,
        )
        return response["messages"][-1].content

    # 12. Voice chat loop
    reply = ask_agent("Hello")
    tell(reply, locale)

    while not confirmed["done"]:
        query = get_user_query(locale)

        if query is None:
            continue

        if query.lower() in ["exit", "bye"]:
            break

        print("user:", query)

        reply = ask_agent(query)
        tell(reply, locale)

    if not confirmed["done"]:
        return None

    result = dict(profile)
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