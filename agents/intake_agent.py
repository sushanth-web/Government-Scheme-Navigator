import io
import json
import os
from typing import Optional

import numpy as np
import requests
import sounddevice as sd
import soundfile as sf

from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver


load_dotenv()

# 1. API keys (set these as environment variables, never hardcode them)
#    The check now runs inside get_profile(), so importing this file
#    never fails or asks questions.
GNANI_API_KEY = os.getenv("GNANI_API_KEY")

STT_URL = "https://api.vachana.ai/stt/v3"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
SAMPLE_RATE = 16000

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


# 3. Voice: record from the microphone
def record_audio(path: str = "input.wav") -> Optional[str]:
    chunks = []

    def callback(indata, frames, time, status):
        chunks.append(indata.copy())

    print("Listening... speak now, press Enter when you are done.")

    with sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=callback
    ):
        input()

    if not chunks:
        return None

    sf.write(path, np.concatenate(chunks), SAMPLE_RATE)
    return path


# 4. Voice: Gnani speech-to-text (max 60 seconds per clip)
def speech_to_text(wav_path: str, locale: str) -> str:
    with open(wav_path, "rb") as f:
        response = requests.post(
            STT_URL,
            headers={"X-API-Key-ID": GNANI_API_KEY},
            files={"audio_file": f},
            data={"language_code": locale, "format": "transcribe"},
            timeout=60,
        )

    response.raise_for_status()
    return response.json().get("transcript", "").strip()


# 5. Voice: Gnani text-to-speech, then play the audio
def speak(text: str, locale: str):
    response = requests.post(
        TTS_URL,
        headers={
            "Content-Type": "application/json",
            "X-API-Key-ID": GNANI_API_KEY,
        },
        json={
            "text": text,
            "voice": "Shivani",
            "model": "timbre-v3.0",
            "language": locale,
            "speed": 1.0,
            "audio_config": {
                "sample_rate": 24000,
                "num_channels": 1,
                "sample_width": 2,
                "encoding": "linear_pcm",
                "container": "wav",
            },
        },
        timeout=60,
    )

    response.raise_for_status()

    data, rate = sf.read(io.BytesIO(response.content))
    sd.play(data, rate)
    sd.wait()


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

    if not GNANI_API_KEY:
        raise ValueError("Please set the GNANI_API_KEY environment variable.")

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
    print("ai:", reply)
    speak(reply, locale)

    while not confirmed["done"]:
        typed = input("\nPress Enter to speak (or type your answer): ").strip()

        if typed.lower() in ["exit", "bye"]:
            break

        if typed:
            query = typed
        else:
            wav_path = record_audio()

            if not wav_path:
                print("No audio recorded, try again.")
                continue

            query = speech_to_text(wav_path, locale)

            if not query:
                print("Could not understand the audio, try again.")
                continue

        print("user:", query)

        reply = ask_agent(query)
        print("ai:", reply)
        speak(reply, locale)

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