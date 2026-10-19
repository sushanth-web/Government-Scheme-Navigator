import json
import io
import os
import re

import requests
import sounddevice as sd
import soundfile as sf

from dotenv import load_dotenv

load_dotenv()

from retrieval_agent import get_llm, vector_store, DATA_DIR


# 1. Keys and settings (checked first, before the slow steps)
GNANI_API_KEY = os.getenv("GNANI_API_KEY")

if not GNANI_API_KEY:
    raise ValueError("Please set the GNANI_API_KEY environment variable.")

TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
NOT_FOUND = "not found in documents"

languages = {
    "1": ("English", "en-IN"),
    "2": ("Telugu", "te-IN"),
    "3": ("Hindi", "hi-IN"),
}


# 2. Load what the scheme selection agent saved
SELECTED_FILE = os.path.join(DATA_DIR, "selected_schemes.json")

if not os.path.exists(SELECTED_FILE):
    raise FileNotFoundError(
        f"{SELECTED_FILE} not found. Run the scheme selection agent first."
    )

with open(SELECTED_FILE, encoding="utf-8") as f:
    saved = json.load(f)

profile = saved["profile"]
selected_schemes = saved["selected_schemes"]

if not selected_schemes:
    raise ValueError("No schemes were selected.")

if saved.get("language") and saved.get("locale"):
    language, locale = saved["language"], saved["locale"]
else:
    choice = input("Choose language (1. English  2. Telugu  3. Hindi): ").strip()
    language, locale = languages.get(choice, languages["1"])

llm = get_llm(temperature=0.1)


# 3. Voice: Gnani text-to-speech, then play the audio
def speak(text: str, locale: str):
    try:
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
    except Exception as error:
        # the text is already printed, so do not stop the whole run
        print(f"(Could not play the voice: {error})")


def tell(text: str):
    print("ai:", text)
    speak(text, locale)


# 4. Ask the LLM for JSON and parse it
def extract_json(text: str) -> dict:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    start, end = text.find("{"), text.rfind("}")

    if start == -1 or end <= start:
        raise ValueError("No JSON found in the model reply.")

    return json.loads(text[start:end + 1])


def ask_json(prompt: str) -> dict:
    last_error = None

    for _ in range(2):  # one retry if the reply is not valid JSON
        try:
            return extract_json(str(llm.invoke(prompt).content))
        except Exception as error:
            last_error = error

    raise ValueError(f"The model did not return valid JSON: {last_error}")


# 5. Find the application details of one scheme
def get_scheme_text(scheme: str) -> str:
    """Passages from the scheme PDFs about documents, dates and how to apply."""

    queries = [
        f"{scheme} documents required to apply certificates",
        f"{scheme} how to apply application process start date last date",
    ]

    seen, chunks = set(), []

    for q in queries:
        for doc in vector_store.similarity_search(q, k=6):
            if doc.page_content in seen:
                continue

            seen.add(doc.page_content)
            chunks.append(
                f"[{os.path.basename(doc.metadata.get('source', 'unknown'))}, "
                f"page {doc.metadata.get('page', 0) + 1}]\n{doc.page_content}"
            )

    return "\n\n".join(chunks)


def get_web_text(scheme: str) -> str:
    """Optional: latest dates from the web. Only runs if TAVILY_API_KEY is set."""

    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        return ""

    try:
        from tavily import TavilyClient

        results = TavilyClient(api_key=api_key).search(
            query=f"{scheme} Andhra Pradesh application start date last date documents required",
            max_results=3,
        )["results"]

        return "\n\n".join(f"[{r['url']}]\n{r['content']}" for r in results)
    except Exception as error:
        print(f"(Web search skipped: {error})")
        return ""


EXTRACT_PROMPT = """You are helping a person apply for a government scheme in Andhra Pradesh.

SCHEME: {scheme}

USER PROFILE (JSON):
{profile}

TEXT FROM THE OFFICIAL SCHEME DOCUMENTS:
{doc_text}

WEB SEARCH RESULTS (may be newer, but less reliable than the documents):
{web_text}

Find what this person needs in order to apply for THIS scheme only.

Rules:
- Use only the text above. Never invent documents, dates, fees or offices.
- If something is not in the text, write "not found in documents".
- List only the documents this person needs. For example, a caste certificate
  only if the scheme asks for it for this person's category.
- Use common names for documents, for example "Aadhaar card",
  "Income certificate", "Caste certificate", "Bank passbook".
- Use the official documents first. Use the web results only for dates, and
  then set dates_source to "web". If dates come from the documents, set it to
  "documents". If there are no dates, set it to "none".

Reply with ONLY valid JSON in exactly this shape and nothing else:
{{"documents": [{{"name": "Aadhaar card", "note": "short detail or empty"}}], "start_date": "...", "deadline": "...", "dates_source": "documents", "how_to_apply": ["step 1", "step 2"], "other_requirements": ["fee, photo, bank account linking, ..."], "where_to_apply": "portal or office"}}
"""


def find_requirements(scheme: str) -> dict:
    prompt = EXTRACT_PROMPT.format(
        scheme=scheme,
        profile=json.dumps(profile, indent=2, ensure_ascii=False),
        doc_text=get_scheme_text(scheme) or "(nothing found)",
        web_text=get_web_text(scheme) or "(not used)",
    )

    try:
        details = ask_json(prompt)
    except ValueError as error:
        print(f"Warning: could not read the details of {scheme} ({error})")
        details = {}

    documents = []

    for doc in details.get("documents") or []:
        if isinstance(doc, dict) and doc.get("name"):
            documents.append({"name": str(doc["name"]).strip(), "note": str(doc.get("note") or "")})
        elif isinstance(doc, str):
            documents.append({"name": doc.strip(), "note": ""})

    return {
        "scheme": scheme,
        "documents": documents,
        "start_date": details.get("start_date") or NOT_FOUND,
        "deadline": details.get("deadline") or NOT_FOUND,
        "dates_source": details.get("dates_source") or "none",
        "how_to_apply": details.get("how_to_apply") or [],
        "other_requirements": details.get("other_requirements") or [],
        "where_to_apply": details.get("where_to_apply") or NOT_FOUND,
    }


# 6. One checklist for all the selected schemes
def build_master_checklist(results: list) -> list:
    master = {}

    for result in results:
        for doc in result["documents"]:
            key = doc["name"].lower()
            item = master.setdefault(key, {"document": doc["name"], "needed_for": []})

            if result["scheme"] not in item["needed_for"]:
                item["needed_for"].append(result["scheme"])

    return list(master.values())


# 7. Write what the voice will say, in the user's language
SCRIPT_PROMPT = """Write what a voice assistant will say aloud to a user in {language}.

Details of one scheme (JSON):
{details}

Write three short spoken parts in {language}:
1. documents: start with the scheme name, then the documents to prepare,
   each with its note if there is one.
2. dates: when applications start and the last date. If a date is
   "not found in documents", say the documents do not mention it and the
   user should check the official website or the village or ward secretariat.
   If dates_source is "web", say the date comes from a website and should be
   checked again.
3. steps: where and how to apply, and the other things needed (fees, photos,
   and so on), in plain words, step by step.

Rules:
- Plain text only. No markdown, bullet points, symbols or emojis.
- Write document names in {language} script so a voice can read them.
- Write dates so they are easy to read aloud, for example 15 November 2026.
- Use only the details given. Never add facts.
- Each part at most four sentences.

Reply with ONLY valid JSON: {{"documents": "...", "dates": "...", "steps": "..."}}
"""

INTRO_PROMPT = """Write what a voice assistant will say aloud to a user in {language}.

The user selected these schemes: {schemes}

Combined list of documents needed for all of them (JSON):
{checklist}

Write two short spoken parts in {language}:
1. intro: say how many schemes the user selected, name them, and say how many
   documents are needed in total. Then say you will explain each scheme.
2. closing: ask the user to prepare all these documents before applying,
   and name the documents again in one sentence.

Rules:
- Plain text only. No markdown, bullet points, symbols or emojis.
- Write scheme and document names in {language} script so a voice can read them.
- Use only the information given. Never add facts.

Reply with ONLY valid JSON: {{"intro": "...", "closing": "..."}}
"""


def english_script(details: dict) -> dict:
    """Used only if the model fails to write the script."""

    names = ", ".join(d["name"] for d in details["documents"]) or NOT_FOUND

    return {
        "documents": f"{details['scheme']}. Documents to prepare: {names}.",
        "dates": f"Applications start: {details['start_date']}. Last date: {details['deadline']}.",
        "steps": "How to apply: " + (" ".join(details["how_to_apply"]) or NOT_FOUND)
        + f" Where: {details['where_to_apply']}.",
    }


def write_script(details: dict) -> dict:
    prompt = SCRIPT_PROMPT.format(
        language=language,
        details=json.dumps(details, indent=2, ensure_ascii=False),
    )

    try:
        parts = ask_json(prompt)
        return {key: str(parts[key]) for key in ("documents", "dates", "steps")}
    except (ValueError, KeyError) as error:
        print(f"Warning: could not write the {language} script for {details['scheme']} ({error})")
        return english_script(details)


def write_intro(results: list, master: list) -> dict:
    prompt = INTRO_PROMPT.format(
        language=language,
        schemes=", ".join(r["scheme"] for r in results),
        checklist=json.dumps(master, indent=2, ensure_ascii=False),
    )

    try:
        parts = ask_json(prompt)
        return {key: str(parts[key]) for key in ("intro", "closing")}
    except (ValueError, KeyError):
        names = ", ".join(item["document"] for item in master)
        return {
            "intro": f"You selected {len(results)} schemes. You need {len(master)} documents in total.",
            "closing": f"Please prepare all these documents before applying: {names}.",
        }


# 8. Run
print("Reading the application details of your schemes, please wait...")

results = [find_requirements(scheme) for scheme in selected_schemes]
master = build_master_checklist(results)

# saved so the next agent can use it
os.makedirs(DATA_DIR, exist_ok=True)
checklist_path = os.path.join(DATA_DIR, "document_checklist.json")

with open(checklist_path, "w", encoding="utf-8") as f:
    json.dump(
        {
            "profile": profile,
            "language": language,
            "schemes": results,
            "checklist": master,
        },
        f,
        indent=2,
        ensure_ascii=False,
    )

print("\nDocument checklist:")
for item in master:
    print(f"- {item['document']}  (for: {', '.join(item['needed_for'])})")

for result in results:
    print(
        f"\n{result['scheme']}: starts {result['start_date']}, "
        f"last date {result['deadline']} (source: {result['dates_source']})"
    )

print(f"\nSaved to: {checklist_path}\n")

# tell the user by voice, in the selected language
intro = write_intro(results, master)
tell(intro["intro"])

for result in results:
    script = write_script(result)

    tell(script["documents"])
    tell(script["dates"])
    tell(script["steps"])

tell(intro["closing"])