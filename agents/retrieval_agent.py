import os
import uuid

from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_chroma import Chroma
from langgraph.checkpoint.memory import InMemorySaver


load_dotenv()

# All paths start from the project folder (the parent of agents/), so the
# result is the same no matter which folder you run the script from.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SCHEMES_DIR = os.path.join(DATA_DIR, "schemes")
CACHE_DIR = os.path.join(DATA_DIR, "cache")


# 1. Initialize the LLM
def get_llm(
    model_name: str = "nvidia/nemotron-3.5-super-vl-120b-a12b",
    temperature: float = 0.2,  # was 0.5, lower = more consistent eligibility checks
):
    api_key = os.getenv("NVIDIA_API_KEY")

    if not api_key:
        raise ValueError("Please set the NVIDIA_API_KEY environment variable.")

    return ChatNVIDIA(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        timeout=180,
        max_completion_tokens=4096,  # was 1024, a ranked list of all schemes is long
    )


# 2. Initialize the embedding model
embeddings = NVIDIAEmbeddings(
    model="nvidia/nemotron-3-embed-1b"
)


# 3. Initialize persistent ChromaDB
vector_store = Chroma(
    collection_name="chroma_collection",
    embedding_function=embeddings,
    persist_directory=CACHE_DIR,
)


# 4. Load, split and store the PDFs ONLY if the DB is empty
#    (before, the PDFs were added again on every run, creating duplicates)
if not vector_store.get(limit=1)["ids"]:
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

    vector_store.add_documents(
        documents=splitted_doc,
    )
else:
    print(f"Using the existing vector DB (delete {CACHE_DIR} to index the PDFs again)")


# 5. Create the retrieval tools
@tool
def retrieve_context(query: str) -> str:
    """Search the indexed scheme PDFs for information relevant
    to the user's question."""

    docs = vector_store.similarity_search(query, k=4)

    if not docs:
        return "No relevant information was found in the documents."

    context = "\n\n".join(
        f"[{os.path.basename(doc.metadata.get('source', 'unknown'))}, "
        f"page {doc.metadata.get('page', 0) + 1}]\n{doc.page_content}"
        for doc in docs
    )

    return context


ELIGIBILITY_QUERY = (
    "eligibility criteria who can apply age income occupation "
    "caste category district land ownership benefits"
)
CHUNKS_PER_SCHEME = 4


@tool
def retrieve_all_schemes() -> str:
    """Return the eligibility and benefit text of EVERY scheme document in the
    vector DB, grouped by document. Use this when you must compare a user
    profile with all the schemes."""

    data = vector_store.get(include=["metadatas"])
    sources = sorted(
        {m["source"] for m in data["metadatas"] if m and m.get("source")}
    )

    parts = []

    for source in sources:
        docs = vector_store.similarity_search(
            ELIGIBILITY_QUERY,
            k=CHUNKS_PER_SCHEME,
            filter={"source": source},
        )
        docs.sort(key=lambda doc: doc.metadata.get("page", 0))

        text = "\n".join(
            f"[page {doc.metadata.get('page', 0) + 1}] {doc.page_content}"
            for doc in docs
        )

        parts.append(f"=== DOCUMENT: {os.path.basename(source)} ===\n{text}")

    return "\n\n".join(parts)


# 6. Create the agent
agent = create_agent(
    model=get_llm(),
    tools=[retrieve_context, retrieve_all_schemes],
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
    5. Answer clearly and directly.
    6. When the user gives a profile and asks you to compare or rank
       schemes, call retrieve_all_schemes ONCE instead of retrieve_context.
       It returns the text of every scheme document. Compare the profile
       with EVERY document and list EVERY scheme, ranked from best suited
       to least suited. Follow the answer format the user asks for.
    7. Ranking order: Eligible first, then Likely eligible, then
       Need more info, then Not eligible. Inside the same status, put
       the scheme that meets more criteria first.
    8. Name each scheme exactly as its official name is written in
       the document.
    """,

    checkpointer=InMemorySaver()
)


def retrieval_agent(query: str) -> str:
    response = agent.invoke(
        {
            "messages": [
                {"role": "user", "content": query}
            ]
        },
        {
            # new thread for every call, so old answers do not pile up
            "configurable": {"thread_id": str(uuid.uuid4())},
            "recursion_limit": 50,
        }
    )

    answer = response["messages"][-1].content

    print("ai:", answer)

    return answer  # before, this function returned None