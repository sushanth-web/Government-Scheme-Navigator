import json
import io
import os

from agents.retrieval_agent import retrieval_agent, DATA_DIR
from agents.intake_agent import load_profile, load_language
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

# 1. API key (checked inside select_schemes(), so importing this file never fails)
GNANI_API_KEY = os.getenv("GNANI_API_KEY")

STT_URL = "https://api.vachana.ai/stt/v3"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
SAMPLE_RATE = 16000

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
   annual income, land, caste category).
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

    return ChatNVIDIA(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        timeout=180,
        max_completion_tokens=1024,
    )


# 4. Voice
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


# 5. Shared data used by the tools
ranked = {"text": ""}          # the ranked list, filled by select_schemes()
selected_schemes = []          # the schemes the user chose
confirmed = {"done": False}


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
    if not GNANI_API_KEY:
        raise ValueError("Please set the GNANI_API_KEY environment variable.")

    # take the details from the intake agent
    if profile is None:
        profile = load_profile()

    if not (language and locale):
        try:
            language, locale = load_language()
        except FileNotFoundError:
            pass

    # start fresh, in case this function is called more than once
    selected_schemes.clear()
    confirmed["done"] = False

    if not (language and locale):
        choice = input("Choose language (1. English  2. Telugu  3. Hindi): ").strip()
        language, locale = languages.get(choice, languages["1"])

    print("Comparing your profile with all the schemes, please wait...")
    ranked["text"] = retrieval_agent(build_query(profile))

    agent = build_agent(language, ranked["text"])
    config = {"configurable": {"thread_id": "1"}}

    def ask_agent(text: str) -> str:
        response = agent.invoke(
            {"messages": [{"role": "user", "content": text}]},
            config,
        )
        return response["messages"][-1].content

    # the agent speaks first and presents the top schemes
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

    print("\nSelected schemes:", selected_schemes)

    # saved so the next agent can read it
    os.makedirs(DATA_DIR, exist_ok=True)

    with open(SELECTED_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "profile": profile,
                "language": language,
                "locale": locale,
                "selected_schemes": selected_schemes,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("Saved to:", SELECTED_FILE)

    return {
        "ranked_schemes": ranked["text"],
        "selected_schemes": list(selected_schemes),
        "language": language,
        "locale": locale,
    }


if __name__ == "__main__":
    # run get_profile() (intake agent) first, this reads what it saved
    select_schemes()