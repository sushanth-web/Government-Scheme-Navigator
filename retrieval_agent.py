import os

from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_chroma import Chroma
from langgraph.checkpoint.memory import InMemorySaver


# 1. Initialize the LLM
def get_llm(
    model_name: str = "nvidia/nemotron-3.5-super-vl-120b-a12b",
    temperature: float = 0.5,
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



# 2. Load PDF documents
loader = PyPDFDirectoryLoader("data/schemes")
documents = loader.load()

if not documents:
    raise ValueError("No PDF documents found in data/schemes.")

print(f"Loaded {len(documents)} document pages")


# 3. Split documents into chunks
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)

splitted_doc = splitter.split_documents(documents)

print(f"Created {len(splitted_doc)} chunks")


# 4. Initialize the embedding model
embeddings = NVIDIAEmbeddings(
    model="nvidia/nemotron-3-embed-1b"
)


# 5. Initialize persistent ChromaDB
vector_store = Chroma(
    collection_name="chroma_collection",
    embedding_function=embeddings,
    persist_directory="data/cache",
)


vector_store.add_documents(
    documents=splitted_doc,
)



# 7. Create the retrieval tool
@tool
def retrieve_context(query: str) -> str:
    """Search the indexed scheme PDFs for information relevant
    to the user's question."""

    docs = vector_store.similarity_search(query, k=4)

    if not docs:
        return "No relevant information was found in the documents."

    context = "\n\n".join(
        doc.page_content for doc in docs
    )

    return context


# 8. Create the agent
agent = create_agent(
    model=get_llm(),
    tools=[retrieve_context],
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
    """,

    checkpointer=InMemorySaver()
)





while True:
    query = input("user:")
    if query.lower() in ["exit","bye"]:
        break
    

    response = agent.invoke(
        {
            "messages": [
                {"role": "user", "content": query}
            ]
        },
        {
            "configurable":{"thread_id":"1"}
        }
    )

    print("ai:",response["messages"][-1].content)
