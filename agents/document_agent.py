import json
import os
import re

from typing import Optional

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

from agents.retrieval_agent import get_llm, vector_store, DATA_DIR
from agents.intake_agent import load_language
from agents.audio_utils import require_api_key, tell


NOT_FOUND = "not found in documents"

languages = {
    "1": ("English", "en-IN"),
    "2": ("Telugu", "te-IN"),
    "3": ("Hindi", "hi-IN"),
}

SELECTED_FILE = os.path.join(DATA_DIR, "selected_schemes.json")
CHECKLIST_FILE = os.path.join(DATA_DIR, "document_checklist.json")


# 2. Load what the scheme selection agent saved (only used when you call the
#    function without passing the profile and schemes)
def load_selected() -> dict:
    if not os.path.exists(SELECTED_FILE):
        raise FileNotFoundError(
            f"{SELECTED_FILE} not found. Run select_schemes() first."
        )

    with open(SELECTED_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_web_text(scheme: str) -> str:
    """Find current application dates for a scheme, if web search is configured."""
    api_key = os.getenv("TAVILY_API_KEY")

    if not api_key:
        return ""

    response = TavilyClient(api_key=api_key).search(
        query=(
            f"{scheme} application start date last date deadline "
            "official Andhra Pradesh government scheme"
        ),
        search_depth="basic",
        max_results=5,
    )
    results = response.get("results", [])

    return "\n\n".join(
        f"{result.get('title', 'Untitled')}\n"
        f"URL: {result.get('url', '')}\n"
        f"{result.get('content', '')[:1200]}"
        for result in results
    )


# 4. Ask the LLM for JSON and parse it
def extract_json(text: str) -> dict:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    start, end = text.find("{"), text.rfind("}")

    if start == -1 or end <= start:
        raise ValueError("No JSON found in the model reply.")

    return json.loads(text[start:end + 1])


def ask_json(llm, prompt: str) -> dict:
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


EXTRACT_PROMPT = """You are helping a person apply for a government scheme in Andhra Pradesh.

SCHEME: {scheme}

USER PROFILE (JSON):
{profile}

TEXT FROM THE OFFICIAL SCHEME DOCUMENTS (the only source for this extraction):
{doc_text}

Find what this person needs in order to apply for THIS scheme only.

Rules:
- Use only the official document text above. Never invent documents, dates, fees or offices.
- If something is not in the text, write "not found in documents".
- List only the documents this person needs. For example, a caste certificate
  only if the scheme asks for it for this person's category.
- Use common names for documents, for example "Aadhaar card",
  "Income certificate", "Caste certificate", "Bank passbook".
- Set dates_source to "documents" only when the dates are stated in the
  official document text. Otherwise set it to "none".

Reply with ONLY valid JSON in exactly this shape and nothing else:
{{"documents": [{{"name": "Aadhaar card", "note": "short detail or empty"}}], "start_date": "...", "deadline": "...", "dates_source": "documents", "how_to_apply": ["step 1", "step 2"], "other_requirements": ["fee, photo, bank account linking, ..."], "where_to_apply": "portal or office"}}
"""


WEB_DATE_PROMPT = """Find application dates for this Andhra Pradesh government scheme.

SCHEME: {scheme}

Dates already found in official scheme documents:
Start date: {start_date}
Deadline: {deadline}

Search results:
{web_text}

Use only explicit application start dates or deadlines stated in these search
results. Prefer official government sources. Do not infer a date from a
publication date, announcement date, or unrelated scheme cycle. Preserve any
date already found in the official documents. If a date is not explicitly
available, return "not found in documents".

Reply with ONLY valid JSON in exactly this shape:
{{"start_date": "...", "deadline": "..."}}
"""


def _is_missing_date(value: object) -> bool:
    if value is None:
        return True

    normalized = str(value).strip().lower()

    return not normalized or normalized in {
        "none",
        "n/a",
        "na",
        "unknown",
        "not available",
        "not found",
        NOT_FOUND,
    } or "not found in" in normalized or "not mentioned" in normalized


def find_requirements(scheme: str, profile: dict, llm) -> dict:
    document_text = get_scheme_text(scheme) or "(nothing found)"
    prompt = EXTRACT_PROMPT.format(
        scheme=scheme,
        profile=json.dumps(profile, indent=2, ensure_ascii=False),
        doc_text=document_text,
    )

    try:
        details = ask_json(llm, prompt)
    except ValueError as error:
        print(f"Warning: could not read the details of {scheme} ({error})")
        details = {}

    start_date = details.get("start_date") or NOT_FOUND
    deadline = details.get("deadline") or NOT_FOUND
    dates_source = details.get("dates_source") or "none"

    if _is_missing_date(start_date) or _is_missing_date(deadline):
        web_text = get_web_text(scheme)

        if web_text:
            date_prompt = WEB_DATE_PROMPT.format(
                scheme=scheme,
                start_date=start_date,
                deadline=deadline,
                web_text=web_text,
            )

            try:
                web_dates = ask_json(llm, date_prompt)
            except ValueError as error:
                print(f"Warning: could not extract web dates for {scheme} ({error})")
                web_dates = {}

            web_start_date = web_dates.get("start_date")
            web_deadline = web_dates.get("deadline")
            used_web_dates = False

            if _is_missing_date(start_date) and not _is_missing_date(web_start_date):
                start_date = str(web_start_date).strip()
                used_web_dates = True

            if _is_missing_date(deadline) and not _is_missing_date(web_deadline):
                deadline = str(web_deadline).strip()
                used_web_dates = True

            if used_web_dates:
                dates_source = "web"

    documents = []

    for doc in details.get("documents") or []:
        if isinstance(doc, dict) and doc.get("name"):
            documents.append({"name": str(doc["name"]).strip(), "note": str(doc.get("note") or "")})
        elif isinstance(doc, str):
            documents.append({"name": doc.strip(), "note": ""})

    return {
        "scheme": scheme,
        "documents": documents,
        "start_date": start_date,
        "deadline": deadline,
        "dates_source": dates_source,
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


def write_script(details: dict, language: str, llm) -> dict:
    prompt = SCRIPT_PROMPT.format(
        language=language,
        details=json.dumps(details, indent=2, ensure_ascii=False),
    )

    try:
        parts = ask_json(llm, prompt)
        return {key: str(parts[key]) for key in ("documents", "dates", "steps")}
    except (ValueError, KeyError) as error:
        print(f"Warning: could not write the {language} script for {details['scheme']} ({error})")
        return english_script(details)


def write_intro(results: list, master: list, language: str, llm) -> dict:
    prompt = INTRO_PROMPT.format(
        language=language,
        schemes=", ".join(r["scheme"] for r in results),
        checklist=json.dumps(master, indent=2, ensure_ascii=False),
    )

    try:
        parts = ask_json(llm, prompt)
        return {key: str(parts[key]) for key in ("intro", "closing")}
    except (ValueError, KeyError):
        names = ", ".join(item["document"] for item in master)
        return {
            "intro": f"You selected {len(results)} schemes. You need {len(master)} documents in total.",
            "closing": f"Please prepare all these documents before applying: {names}.",
        }


# 8. The function other files import: build the checklist and tell the user
def build_document_checklist(
    profile: Optional[dict] = None,
    selected_schemes: Optional[list] = None,
    language: Optional[str] = None,
    locale: Optional[str] = None,
) -> dict:
    """Find the documents, dates and steps for each selected scheme, make one
    combined checklist and tell it to the user by voice. Returns a dict:

        {"schemes": [ {scheme, documents, start_date, deadline, ...}, ... ],
         "checklist": [ {"document": "Aadhaar card", "needed_for": [...]}, ... ],
         "language": "Telugu", "locale": "te-IN"}

    profile, selected_schemes: from the previous agents. If you do not pass
        them, data/selected_schemes.json (saved by select_schemes) is used.
    language, locale: for example "Telugu", "te-IN". If you do not pass them,
        the saved language is used (and only if there is none, the user is asked).

    The result is also saved to data/document_checklist.json.
    """

    # check the key BEFORE the slow steps
    require_api_key()

    # take the details from the previous agents
    if profile is None or selected_schemes is None:
        saved = load_selected()

        if profile is None:
            profile = saved["profile"]

        if selected_schemes is None:
            selected_schemes = saved["selected_schemes"]

        if not (language and locale):
            language, locale = saved.get("language"), saved.get("locale")

    if not selected_schemes:
        raise ValueError("No schemes were selected.")

    if not (language and locale):
        try:
            language, locale = load_language()
        except FileNotFoundError:
            choice = input("Choose language (1. English  2. Telugu  3. Hindi): ").strip()
            language, locale = languages.get(choice, languages["1"])

    llm = get_llm(temperature=0.1)

    print("Reading the application details of your schemes, please wait...")

    results = [find_requirements(scheme, profile, llm) for scheme in selected_schemes]
    master = build_master_checklist(results)

    # saved so the next agent can use it
    os.makedirs(DATA_DIR, exist_ok=True)

    with open(CHECKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "profile": profile,
                "language": language,
                "locale": locale,
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

    print(f"\nSaved to: {CHECKLIST_FILE}\n")

    # tell the user by voice, in the selected language
    intro = write_intro(results, master, language, llm)
    tell(intro["intro"], locale, continue_on_error=True)

    for result in results:
        script = write_script(result, language, llm)

        tell(script["documents"], locale, continue_on_error=True)
        tell(script["dates"], locale, continue_on_error=True)
        tell(script["steps"], locale, continue_on_error=True)

    tell(intro["closing"], locale, continue_on_error=True)

    return {
        "schemes": results,
        "checklist": master,
        "language": language,
        "locale": locale,
    }


if __name__ == "__main__":
    # run select_schemes() first, this reads what it saved
    build_document_checklist()