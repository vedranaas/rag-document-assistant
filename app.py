from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from huggingface_hub import InferenceClient
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="RAG Document Assistant",
    description="RAG application using LangChain, Pinecone and Hugging Face",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")

INDEX_NAME = "langchainvector"



embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


vector_store=PineconeVectorStore(
    index_name=INDEX_NAME,
    embedding=embeddings,
    pinecone_api_key=PINECONE_API_KEY
)


hf_client=InferenceClient(
    api_key=HF_TOKEN
)



def agent_answer(question: str, history):

    documents = vector_store.similarity_search(question, k=6)


    if not documents:
        return {
            "answer": "I cannot find the answer in the provided document.",
            sources: []
        }

    retrieved_information = "\n\n".join(
        f"Page {document.metadata.get('page', 'unknown')}:\n{document.page_content}"
        for document in documents
    )

    messages = [
        {
            "role": "system",
            "content": """
            You are a helpful document assistant.
            Answer the user's question using only the information retrieved from the document.
            If the answer cannot be found in the retrieved information, say:
            "I cannot find the answer in the provided document."
            Do not invent information.
            """
        }
    ]

    messages.extend(
        message.model_dump()
        for message in history
    )

    messages.append(
        {
            "role": "user",
            "content": f"""
            Retrieved information:
            {retrieved_information}
            User question:
            {question}
            """
        }
    )

    response = hf_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=messages,
        max_tokens=500
    )

    sources = [
        {
            "page": document.metadata.get("page", "unknown")
        }
        for document in documents
    ]

        
    return {
        "answer": response.choices[0].message.content,
        "sources": sources
    }


class Message(BaseModel):
    role: str
    content: str


class Question(BaseModel):
    question: str
    history: list[Message] = []



@app.get("/")
def home():
    return {"message": "RAG API is running"}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        return {"error": "Only PDF files are allowed."}

    contents = await file.read()

    with open("uploaded.pdf", "wb") as f:
        f.write(contents)

    loader = PyPDFLoader("uploaded.pdf")
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=50
    )
    chunks = text_splitter.split_documents(documents )

    vector_store.delete(delete_all=True)
    vector_store.add_documents(chunks)

    return {
        "filename": file.filename,
        "message": "PDF uploaded successfully."
    }

@app.post("/ask")
def ask_question(request: Question):
    result=agent_answer(request.question, request.history)

    return {
        "question": request.question,
        "answer": result["answer"],
        "sources": result["sources"]
    }
