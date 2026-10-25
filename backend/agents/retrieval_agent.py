import os
import logging
import re
import threading
import time
import uuid
import hashlib
import json

from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_chroma import Chroma
from langgraph.checkpoint.memory import InMemorySaver
from tavily import TavilyClient

from agents.http_clients import create_retry_session
from agents.llm_utils import (
    EMBEDDING_MODEL,
    FAST_MODEL,
    RANKING_MODEL,
    build_chat_model,
    clean_text,
    strip_markdown,
)


load_dotenv()

# All paths start from the project folder (the parent of agents/), so the
# result is the same no matter which folder you run the script from.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SCHEMES_DIR = os.path.join(DATA_DIR, "schemes")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
INDEX_MANIFEST = os.path.join(CACHE_DIR, "schemes_manifest.json")
logger = logging.getLogger(__name__)
_web_cache: dict[tuple[str, ...], tuple[float, str]] = {}
_web_cache_lock = threading.Lock()


# 1. Initialize the LLM (ranking every scheme needs the stronger model)
_active_model = {"name": RANKING_MODEL}


def get_llm(
    model_name: str = "",
    temperature: float = 0.2,  # low = consistent eligibility checks
):
    return build_chat_model(
        model_name or _active_model["name"], temperature, timeout=180, max_tokens=8192
    )


# 2. Initialize the embedding model
class LazyNVIDIAEmbeddings:
    def __init__(self) -> None:
        self._client: NVIDIAEmbeddings | None = None

    def _get_client(self) -> NVIDIAEmbeddings:
        if self._client is None:
            self._client = NVIDIAEmbeddings(model=EMBEDDING_MODEL, truncate="END")
            self._client._client.timeout = 30
            self._client._client.get_session_fn = create_retry_session
        return self._client

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._get_client().embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._get_client().embed_query(text)


embeddings = LazyNVIDIAEmbeddings()


# 3. Initialize persistent ChromaDB
vector_store = Chroma(
    collection_name="chroma_collection",
    embedding_function=embeddings,
    persist_directory=CACHE_DIR,
)

_fingerprint_cache: dict = {"key": None, "value": None}
_catalogue_cache: dict = {"key": None, "text": ""}


def _scheme_files() -> list[tuple[str, str, int, int]]:
    if not os.path.isdir(SCHEMES_DIR):
        raise FileNotFoundError(f"Scheme documents directory not found: {SCHEMES_DIR}")
    files = []
    for filename in sorted(os.listdir(SCHEMES_DIR)):
        path = os.path.join(SCHEMES_DIR, filename)
        if filename.lower().endswith(".pdf") and os.path.isfile(path):
            stat = os.stat(path)
            files.append((filename, path, stat.st_size, stat.st_mtime_ns))
    return files


def _scheme_fingerprint() -> dict:
    """Content hashes of the PDFs plus the embedding model used for the index.
    Hashes are cached until a file's size or modified time changes."""
    files = _scheme_files()
    key = tuple((name, size, mtime) for name, _path, size, mtime in files)
    if _fingerprint_cache["key"] == key:
        return _fingerprint_cache["value"]

    hashes = {}
    for filename, path, _size, _mtime in files:
        digest = hashlib.sha256()
        with open(path, "rb") as pdf_file:
            for chunk in iter(lambda: pdf_file.read(1024 * 1024), b""):
                digest.update(chunk)
        hashes[filename] = digest.hexdigest()

    value = {"embedding_model": EMBEDDING_MODEL, "files": hashes}
    _fingerprint_cache["key"] = key
    _fingerprint_cache["value"] = value
    return value


def build_index() -> None:
    """Rebuild the persistent vector index from the current scheme PDFs."""
    loader = PyPDFDirectoryLoader(SCHEMES_DIR)
    documents = loader.load()

    if not documents:
        raise ValueError(f"No PDF documents found in {SCHEMES_DIR}")

    print(f"Loaded {len(documents)} document pages")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )

    splitted_doc = splitter.split_documents(documents)

    print(f"Created {len(splitted_doc)} chunks")

    existing_ids = vector_store.get(include=[])["ids"]
    if existing_ids:
        vector_store.delete(ids=existing_ids)
    if splitted_doc:
        vector_store.add_documents(documents=splitted_doc)

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(INDEX_MANIFEST, "w", encoding="utf-8") as manifest_file:
        json.dump(_scheme_fingerprint(), manifest_file, indent=2, sort_keys=True)
    _catalogue_cache["key"] = None


def ensure_indexed() -> None:
    if not vector_store.get(limit=1)["ids"]:
        raise RuntimeError(
            f"No prebuilt scheme index found in {CACHE_DIR}. "
            "Build it with `python -m agents.build_index`."
        )
    try:
        with open(INDEX_MANIFEST, encoding="utf-8") as manifest_file:
            indexed_fingerprint = json.load(manifest_file)
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            "The scheme index has no valid freshness manifest. Rebuild it with "
            "`python -m agents.build_index`."
        ) from error

    if indexed_fingerprint != _scheme_fingerprint():
        raise RuntimeError(
            "The scheme PDFs or the embedding model changed since the Chroma index "
            "was built. Rebuild it with `python -m agents.build_index`, then "
            "restart the API."
        )


def _catalogue_text() -> str:
    """All indexed text with only letters and digits, cached per index state."""
    key = _fingerprint_cache["key"]
    if _catalogue_cache["key"] != key or key is None:
        documents = vector_store.get(include=["documents"])["documents"]
        _catalogue_cache["text"] = re.sub(r"[^a-z0-9]", "", "\n".join(documents).lower())
        _catalogue_cache["key"] = key
    return _catalogue_cache["text"]


@tool
def search_official_sources(scheme_names: list[str]) -> str:
    """Search current official government sources for scheme names from the
    local document catalogue. Supply scheme names only, never user details."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Official web search is not configured; use the indexed documents only."

    searchable_text = _catalogue_text()
    names = []
    for supplied_name in scheme_names:
        candidate = supplied_name.strip()
        normalized = re.sub(r"[^a-z0-9]", "", candidate.lower())
        if (
            len(normalized) >= 8
            and len(candidate) <= 120
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9&()/' .-]{2,119}", candidate)
            and normalized in searchable_text
            and candidate not in names
        ):
            names.append(candidate)
        if len(names) == 5:
            break
    if not names:
        return "No recognized scheme names were supplied for official web search."

    cache_key = tuple(sorted(names))
    now = time.monotonic()
    with _web_cache_lock:
        cached = _web_cache.get(cache_key)
        if cached and cached[0] > now:
            return cached[1]

    query = (
        "Official Andhra Pradesh government scheme eligibility, benefits, "
        "application process, and current dates for: " + "; ".join(names)
    )
    result_text = ""
    for attempt in range(2):
        try:
            results = TavilyClient(api_key=api_key, timeout=8).search(
                query=query,
                search_depth="basic",
                max_results=8,
                include_domains=["ap.gov.in", "gov.in", "nic.in", "myscheme.gov.in"],
            ).get("results", [])
            result_text = "\n\n".join(
                f"{result.get('title', 'Official source')}\n"
                f"URL: {result.get('url', '')}\n"
                f"{str(result.get('content', ''))[:900]}"
                for result in results
            )
            if not result_text:
                result_text = "No results were returned from the selected official domains."
            break
        except Exception as error:
            logger.warning("Official web search failed (%s).", type(error).__name__)
            if attempt == 0:
                time.sleep(0.25)
            else:
                result_text = (
                    "Official web search is temporarily unavailable; use the "
                    "indexed documents and identify that limitation."
                )

    with _web_cache_lock:
        _web_cache[cache_key] = (time.monotonic() + 900, result_text)
    return result_text


# 5. Create the retrieval tools
@tool
def retrieve_context(query: str) -> str:
    """Search the indexed scheme PDFs for information relevant
    to the user's question."""

    ensure_indexed()
    docs = vector_store.similarity_search(query, k=4)

    if not docs:
        return "No relevant information was found in the documents."

    return "\n\n".join(
        f"[{os.path.basename(doc.metadata.get('source', 'unknown'))}, "
        f"page {doc.metadata.get('page', 0) + 1}]\n{doc.page_content}"
        for doc in docs
    )


ELIGIBILITY_QUERY = (
    "eligibility criteria who can apply age income occupation "
    "caste category district land ownership benefits"
)


@tool
def retrieve_all_schemes(query: str) -> str:
    """Return profile-relevant evidence from EVERY scheme document, grouped
    by document. Include the user's relevant profile and eligibility criteria
    in the query; unknown details should not be inferred."""

    ensure_indexed()
    data = vector_store.get(include=["metadatas"])
    sources = sorted(
        {m["source"] for m in data["metadatas"] if m and m.get("source")}
    )
    query_embedding = embeddings.embed_query(
        f"{ELIGIBILITY_QUERY}. Profile and matching criteria: {query}"
    )

    parts = []
    for source in sources:
        docs = vector_store.similarity_search_by_vector(
            query_embedding,
            k=3,
            filter={"source": source},
        )
        docs.sort(key=lambda document: document.metadata.get("page", 0))
        text = "\n".join(
            f"[page {document.metadata.get('page', 0) + 1}] "
            f"{document.page_content}"
            for document in docs
        )

        parts.append(f"=== DOCUMENT: {os.path.basename(source)} ===\n{text}")

    return "\n\n".join(parts)


# 6. Create the agent only when document retrieval is actually needed.
_agent = None
_agent_lock = threading.Lock()
_checkpointer = InMemorySaver()


def get_agent():
    global _agent
    with _agent_lock:
        if _agent is None:
            _agent = create_agent(
                model=get_llm(),
                tools=[retrieve_context, retrieve_all_schemes, search_official_sources],
                system_prompt="""
    You are a document question-answering agent.

    Rules:
    1. For every question about the uploaded scheme documents,
       call retrieve_context before answering.
    2. Base your answer only on the retrieved document context.
    3. Never invent scheme benefits, eligibility criteria,
       amounts, deadlines, or other details.
    4. If the retrieved context does not contain the answer,
       say that the information could not be found in the
       uploaded documents.
    5. Answer clearly and directly. Use plain text only: no markdown, no
       tables, no bold text, no symbols and no emojis.
    6. When the user gives a profile and asks you to compare or rank
       schemes, call retrieve_all_schemes ONCE instead of retrieve_context.
       Pass a concise search query containing all known relevant profile
       values and criteria such as age, occupation, district, income, caste,
       land, household size, student course, and disability status. Do not
       treat unknown profile values as negative matches.
       Then call search_official_sources ONCE with only the names of promising
       schemes from those documents. Never send profile details, income, caste,
       district, or other personal data to web search. Treat official documents
       as the eligibility source and use web results to supplement or flag
       current public information. Include official source URLs when relevant.
       Compare the profile with EVERY document and list EVERY scheme, ranked
       from best suited to least suited. Follow the answer format the user asks for.
    7. Ranking order: Eligible first, then Likely eligible, then
       Need more info, then Not eligible. Inside the same status, put
       the scheme that meets more criteria first.
    8. Name each scheme exactly as its official name is written in
       the document.
    """,
                checkpointer=_checkpointer,
            )
        return _agent


def _model_unavailable(error: Exception) -> bool:
    text = str(error).lower()
    return "404" in text or "not found" in text


def _reset_agent() -> None:
    global _agent
    with _agent_lock:
        _agent = None


def retrieval_agent(query: str) -> str:
    ensure_indexed()
    for attempt in range(2):
        thread_id = str(uuid.uuid4())  # new thread for every call
        try:
            response = get_agent().invoke(
                {"messages": [{"role": "user", "content": query}]},
                {
                    "configurable": {"thread_id": thread_id},
                    "recursion_limit": 50,
                },
            )
            break
        except Exception as error:
            # The chosen ranking model is not served: fall back to the fast model.
            if attempt == 0 and _active_model["name"] != FAST_MODEL and _model_unavailable(error):
                logger.warning(
                    "Ranking model %s unavailable, falling back to %s.",
                    _active_model["name"],
                    FAST_MODEL,
                )
                _active_model["name"] = FAST_MODEL
                _reset_agent()
                continue
            raise
        finally:
            try:
                _checkpointer.delete_thread(thread_id)  # no memory build-up
            except Exception:
                pass

    return strip_markdown(clean_text(response["messages"][-1].content), keep_lines=True)


def rank_schemes(prompt: str, evidence_query: str) -> str:
    """Rank every scheme in ONE model call.

    The evidence from every scheme PDF is fetched directly (no tool-calling
    loop that can return an empty answer) and handed to the model together
    with the instructions. Returns plain text, one block per scheme.
    """
    ensure_indexed()
    evidence = retrieve_all_schemes.invoke({"query": evidence_query})
    full_prompt = (
        f"{prompt}\n\nEVIDENCE FROM THE SCHEME DOCUMENTS (your only source, "
        f"one section per document):\n{evidence}"
    )
    reply = get_llm().invoke(full_prompt).content
    return strip_markdown(clean_text(reply), keep_lines=True)