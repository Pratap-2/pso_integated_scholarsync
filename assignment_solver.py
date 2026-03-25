import os
import re
import requests
from io import BytesIO
from pypdf import PdfReader
from dotenv import dotenv_values

# ---------------- ENV ----------------

env = dotenv_values(".env")
GROQ_KEY = env.get("GROQ_API_KEY")

import os
from dotenv import load_dotenv
load_dotenv()

CACHE_DIR = "cache"
PDF_DIR = "generated_pdfs"

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)


# ---------------- GOOGLE DRIVE LINK FIX ----------------

def convert_drive_link(url):

    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)

    if match:
        return f"https://drive.google.com/uc?export=download&id={match.group(1)}"

    match = re.search(r'id=([a-zA-Z0-9_-]+)', url)

    if match:
        return f"https://drive.google.com/uc?export=download&id={match.group(1)}"

    return url


# ---------------- DOWNLOAD PDF ----------------

def download_pdf(url):

    url = convert_drive_link(url)

    # extract real Google Drive id
    match = re.search(r'id=([a-zA-Z0-9_-]+)', url)

    if match:
        file_id = match.group(1)
    else:
        file_id = str(abs(hash(url)))

    path = f"{CACHE_DIR}/{file_id}.pdf"

    if os.path.exists(path):
        return path

    r = requests.get(url)

    with open(path, "wb") as f:
        f.write(r.content)

    return path

# ---------------- READ PDF ----------------

def load_pdf_text(path):

    reader = PdfReader(path)

    text = ""

    for page in reader.pages:
        t = page.extract_text()
        if t:
            text += t + "\n"

    return text


# ---------------- Azure AI Search RAG ----------------

def _get_search_client():
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents import SearchClient
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
    index = os.getenv("AZURE_SEARCH_INDEX_NAME", "scholarsync-docs")
    return SearchClient(endpoint=endpoint, index_name=index, credential=AzureKeyCredential(key))

def _get_index_client():
    from azure.core.credentials import AzureKeyCredential
    from azure.search.documents.indexes import SearchIndexClient
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
    return SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(key))

def _ensure_index():
    """Create the Azure AI Search index if it doesn't exist yet."""
    from azure.search.documents.indexes.models import (
        SearchIndex, SimpleField, SearchableField, SearchField,
        SearchFieldDataType, VectorSearch, HnswAlgorithmConfiguration,
        VectorSearchProfile
    )
    client = _get_index_client()
    index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "scholarsync-docs")
    existing = [i.name for i in client.list_indexes()]
    if index_name in existing:
        return
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SimpleField(name="doc_key", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="myHnswProfile"
        ),
    ]
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="myHnsw")],
        profiles=[VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="myHnsw")]
    )
    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
    client.create_index(index)
    print(f"Created Azure AI Search index: {index_name}")

def _embed(text: str) -> list:
    """Embed a single text string using Azure OpenAI text-embedding-3-small."""
    from openai import AzureOpenAI
    client = AzureOpenAI(
        api_key=os.getenv("AZURE_EMBEDDING_API_KEY"),
        api_version=os.getenv("AZURE_EMBEDDING_API_VERSION", "2024-02-01"),
        azure_endpoint=os.getenv("AZURE_EMBEDDING_ENDPOINT")
    )
    result = client.embeddings.create(
        input=text,
        model=os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
    )
    return result.data[0].embedding

def _get_doc_key(urls: list) -> str:
    import hashlib
    return hashlib.md5("".join(sorted(urls)).encode()).hexdigest()

def _index_documents(chunks: list, doc_key: str):
    """Embed and upload text chunks into Azure AI Search."""
    import hashlib
    client = _get_search_client()
    docs = []
    for i, chunk in enumerate(chunks):
        chunk_id = hashlib.md5(f"{doc_key}-{i}".encode()).hexdigest()
        docs.append({
            "id": chunk_id,
            "doc_key": doc_key,
            "content": chunk,
            "embedding": _embed(chunk)
        })
    # Upload in batches of 100
    for i in range(0, len(docs), 100):
        client.upload_documents(documents=docs[i:i+100])
    print(f"Indexed {len(docs)} chunks into Azure AI Search.")

def _is_indexed(doc_key: str) -> bool:
    """Check if this doc_key already exists in the index."""
    client = _get_search_client()
    results = list(client.search(search_text="*", filter=f"doc_key eq '{doc_key}'", top=1))
    return len(results) > 0

def _vector_search(query: str, doc_keys: list, top_k: int = 15) -> list:
    """Run a vector search and return top-k content snippets."""
    from azure.search.documents.models import VectorizedQuery
    if not doc_keys: return []
    client = _get_search_client()
    query_vec = _embed(query)
    vector_query = VectorizedQuery(vector=query_vec, k_nearest_neighbors=top_k, fields="embedding")
    keys_str = ",".join(doc_keys)
    filter_expr = f"search.in(doc_key, '{keys_str}', ',')"
    results = client.search(
        search_text=query,
        vector_queries=[vector_query],
        filter=filter_expr,
        select=["content"],
        top=top_k
    )
    return [r["content"] for r in results]

def index_document(url: str) -> str:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    if not url: return None
    _ensure_index()
    key = _get_doc_key([url])
    if _is_indexed(key): return key
    try:
        path = download_pdf(url)
        text = load_pdf_text(path)
        if text.strip():
            splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
            chunks = [c.page_content for c in splitter.create_documents([text])]
            _index_documents(chunks, key)
            print(f"Index complete: {url}")
        return key
    except Exception as e:
        print(f"Failed to index {url}: {e}")
        return None

def solve_assignment(question, history, assignment_url, material_urls):
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_openai import AzureChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.messages import HumanMessage, AIMessage

    _ensure_index()

    all_urls = [u for u in [assignment_url] + (material_urls or []) if u]
    doc_keys = [index_document(u) for u in all_urls]
    doc_keys = [k for k in doc_keys if k]

    if not doc_keys:
        return "I could not read the document. The URL may be inaccessible or not a valid PDF."

    # Retrieve relevant chunks via vector search
    context_chunks = _vector_search(question, doc_keys)
    context = "\n\n".join(context_chunks)

    llm = AzureChatOpenAI(
        azure_deployment=os.getenv("DEPLOYMENT_NAME", "gpt-4o-mini"),
        temperature=0,
        api_version="2024-02-15-preview"
    )

    system_prompt = """You are an expert academic assistant.

Use the provided study materials and assignment context to answer the question.

Rules:
- Give clear structured answers
- Show steps if solving problems
- Use headings if needed
- If answer not found say "Not found in materials"

Context:
{context}
"""
    langchain_history = []
    for msg in history:
        content = msg.get("content", "")
        if isinstance(content, dict):
            content = content.get("answer", str(content))
        if msg.get("role") == "assistant":
            langchain_history.append(AIMessage(content=str(content)))
        else:
            langchain_history.append(HumanMessage(content=str(content)))

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ])

    chain = (
        {"context": lambda _: context, "chat_history": lambda _: langchain_history, "input": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    answer = chain.invoke(question)
    return answer


# ---------------- FULL ASSIGNMENT SOLVER ----------------

def solve_entire_assignment(assignment_url, material_urls):

    from langchain_openai import AzureChatOpenAI

    assignment_path = download_pdf(assignment_url)

    assignment_text = load_pdf_text(assignment_path)

    # LIMIT assignment size (important)
    assignment_text = assignment_text[:8000]

    llm = AzureChatOpenAI(
        azure_deployment=os.getenv("DEPLOYMENT_NAME", "gpt-4o-mini"),
        temperature=0,
        api_version="2024-02-15-preview"
    )

    prompt = f"""
You are a university academic assistant.

Solve the following assignment completely.

Rules:
- Solve each question clearly
- Show steps if needed
- Provide explanations
- Structure answers properly
- Only solve the assignment below

ASSIGNMENT:

{assignment_text}
"""

    response = llm.invoke(prompt)

    return response.content


# ---------------- GENERATE SOLUTION PDF ----------------

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4


def generate_solution_pdf(solution_text, assignment_id):

    file_name = f"solution_{assignment_id}.pdf"

    path = f"{PDF_DIR}/{file_name}"

    styles = getSampleStyleSheet()
    story = []

    # Simple Markdown to ReportLab XML conversion
    # Note: ReportLab Paragraph supports <b>, <i>, <u>, <font>, <br/>
    
    # Process line by line for headers to avoid splitting issues
    for line in solution_text.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 6))
            continue
            
        # Headers
        if line.startswith("### "):
            line = f'<font size="13" color="#1060f0"><b>{line[4:]}</b></font>'
        elif line.startswith("## "):
            line = f'<font size="15" color="#1060f0"><b>{line[3:]}</b></font>'
        elif line.startswith("# "):
            line = f'<font size="17" color="#1060f0"><b>{line[2:]}</b></font>'
            
        # Bold: **text** -> <b>text</b>
        line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
        # Italic: *text* -> <i>text</i>
        line = re.sub(r'\*(.*?)\*', r'<i>\1</i>', line)
        # List bullets: - text -> &bull; text
        if line.startswith("- "):
            line = "&bull; " + line[2:]

        try:
            story.append(Paragraph(line, styles["Normal"]))
        except:
            # Fallback if XML tags are malformed
            story.append(Paragraph(re.sub(r'<.*?>', '', line), styles["Normal"]))
            
        story.append(Spacer(1, 6))

    pdf = SimpleDocTemplate(path, pagesize=A4)

    pdf.build(story)

    return path