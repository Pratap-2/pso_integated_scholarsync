import os
import re
import uuid
import json
import PyPDF2
import docx

from typing import Dict, List
from dotenv import load_dotenv

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_community.vectorstores.azuresearch import AzureSearch

from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SimpleField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchAlgorithmConfiguration
)
from azure.core.credentials import AzureKeyCredential


load_dotenv()

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SimpleField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile
)

def ensure_index_exists():
    credential = AzureKeyCredential(AZURE_SEARCH_KEY)
    client = SearchIndexClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        credential=credential
    )
    existing = list(client.list_index_names())
    if INDEX_NAME in existing:
        print(f"Azure index '{INDEX_NAME}' already exists")
        return
    print("Creating Azure Search index...")
    fields = [
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True
        ),
        SearchField(
            name="content",
            type=SearchFieldDataType.String,
            searchable=True
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            vector_search_dimensions=3072,
            vector_search_profile_name="vector-profile"
        ),
        SimpleField(
            name="metadata",
            type=SearchFieldDataType.String,
            filterable=True
        )
    ]
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="hnsw-config"
            )
        ],
        profiles=[
            VectorSearchProfile(
                name="vector-profile",
                algorithm_configuration_name="hnsw-config"
            )
        ]
    )
    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search
    )
    client.create_index(index)
    print("Azure Search index created successfully")
def test_azure_connection():

    print("\nTesting Azure Search connection...")

    try:
        client = SearchIndexClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            credential=AzureKeyCredential(AZURE_SEARCH_KEY)
        )

        indexes = list(client.list_index_names())

        print("Connected to Azure Search")
        print("Existing indexes:", indexes)

        return True

    except Exception as e:

        print("Azure connection FAILED:", e)
        return False

class CVParser:

    def __init__(self):

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001"
        )
        
        # Groq LLM
        self.llm = ChatGroq(
            model_name="llama-3.1-8b-instant",
            verbose=True
        )

        # Azure Vector Store
        self.vector_store = AzureSearch(
            azure_search_endpoint=AZURE_SEARCH_ENDPOINT,
            azure_search_key=AZURE_SEARCH_KEY,
            index_name=INDEX_NAME,
            embedding_function=self.embeddings.embed_query
        )
    def extract_pdf(self, path):
        text = ""
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text += t
        return text
    def extract_docx(self, path):
        doc = docx.Document(path)
        return "\n".join([p.text for p in doc.paragraphs])
    def extract_email(self, text):
        result = re.findall(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]+",
            text
        )
        return result[0] if result else ""
    def extract_phone(self, text):
        result = re.findall(
            r"[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]",
            text
        )
        return result[0] if result else ""
    def extract_skills(self, text):

        skills = [
            "python","java","javascript","typescript",
            "c++","react","node","docker","kubernetes",
            "azure","aws","gcp","sql","mongodb",
            "machine learning","deep learning"
        ]

        t = text.lower()

        return [s for s in skills if s in t]
    
    def structured_resume(self, text):

        prompt = f"""
        Extract structured information from the following resume.

        You MUST output ONLY valid JSON. Absolutely no other text, no intro, no markdown blocks.
        Use exactly this schema:

        {{
        "name": "",
        "contact": {{
            "email": "",
            "phone": "",
            "github": "",
            "linkedin": ""
        }},
        "education": [],
        "experience": [],
        "projects": [],
        "skills": {{
            "languages": [],
            "tools": [],
            "concepts": []
        }},
        "achievements": [],
        "activities": []
        }}

        Resume:
        {text}
        """
        try:
            llm_with_json = self.llm.bind(response_format={"type": "json_object"})
            response = llm_with_json.invoke(prompt)
        except Exception as e:
            print(f"Failed JSON mode, falling back to standard: {e}")
            response = self.llm.invoke(prompt)
        content = response.content.strip()
        content = content.replace("```json", "").replace("```", "")
        try:
            # Try to parse directly first
            return json.loads(content)
        except:
            # Fallback: try to extract just the JSON part using regex
            import re
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    pass
            print("LLM returned invalid JSON")
            print(content)
            return {}

    def parse_cv(self, file_path):
        if file_path.endswith(".pdf"):
            text = self.extract_pdf(file_path)
        elif file_path.endswith(".docx"):
            text = self.extract_docx(file_path)
        else:
            with open(file_path) as f:
                text = f.read()

        data = self.structured_resume(text)
        chunks = self.splitter.split_text(text)
        ids = [str(uuid.uuid4()) for _ in chunks]
        self.vector_store.add_texts(
            texts=chunks,
            ids=ids,
            metadatas=[{"source": file_path, "chunk": i} for i in range(len(chunks))]
        )

        print(f"{len(chunks)} chunks stored in Azure Search")
        return data

    def search(self, query):
        docs = self.vector_store.similarity_search(query, k=3)
        if not docs:
            print("No results found")
            return
        context = "\n\n".join([d.page_content for d in docs])
        prompt = f"""
        Answer the question based on this CV context using minimal tokens ?
        Question: {query}
        Context:
        {context}
        """
        response = self.llm.invoke(prompt)
        print("\n--- Retrieved Context ---\n")
        print(context)
        print("\n--- LLM Answer ---\n")
        print(response.content)



if __name__ == "__main__":

    if not test_azure_connection():
        print("Fix Azure credentials in .env")
        exit()

    # ensure_index_exists() #imp in case of new index creation

    parser = CVParser()
    import json
    cv = parser.parse_cv(r"C:\Users\Aditya Pratap Singh\Desktop\MS PROJECT\resumes\sde_aditya_pratap_singh.pdf")
    with open("parsed_cv.json", "w", encoding="utf-8") as f:
        json.dump(cv, f, indent=4)
    print("Parsed CV saved to parsed_cv.json")
    # print(cv)
    # print("\nSearch Example\n")

    parser.search("how are the technical skills of person ")