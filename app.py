from fastapi import FastAPI
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from huggingface_hub import InferenceClient
from langchain_core.tools import tool
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

def ask_llm(prompt):
    response = hf_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "search_document",
                        "description": "Search the document for information relevant to the user's question.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The question or information to search for in the document."
                                }
                            },
                            "required": ["query"]
                        }
                    }
                }
            ],
            max_tokens=500
        )
    
    return response.choices[0].message



@tool
def search_document(query: str) -> str:
    """Search the document for information relevant to the user's question."""

    documents = vector_store.similarity_search(query, k=3)

    if not documents:
        return "No relevant information was found in the document."

    return "\n\n".join(
        f"Page {document.metadata.get('page', 'unknown')}:\n{document.page_content}"
        for document in documents
        )

tools = [search_document]


def get_sources(query: str):
    documents = vector_store.similarity_search(query, k=3)

    return[
        {
            "page": document.metadata.get("page", "unknown"),
            "content": document.page_content
        }
        for document in documents
    ]


def agent_answer(question: str):

    first_response = ask_llm(question)

    if first_response.tool_calls:
        tool_call = first_response.tool_calls[0]

        if tool_call.function.name == "search_document":

            import json

            arguments = json.loads(tool_call.function.arguments)
            query = arguments["query"]
            tool_result = search_document.invoke(query)

            sources = get_sources(query)

            final_prompt = f"""
            You are a helpful document assistant.
            Use the following information retreived from the document to answer the user's question.
            Retreived information:
            {tool_result}
            User question:
            {question}
            Answer only using the retreived information.
            If the answer cannot be found say:
            "I cannot find the answer in the provided document."
            Answer:
            """

            final_response = hf_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {
                        "role": "user",
                        "content": final_prompt
                    }
                ],
                max_tokens=500
            )
            return {
                "answer": final_response.choices[0].message.content,
                "sources": sources
            }

    return first_response.content


class Question(BaseModel):
    question: str




@app.get("/")
def home():
    return {"message": "RAG API is running"}

@app.post("/ask")
def ask_question(request: Question):
    result=agent_answer(request.question)

    return {
        "question": request.question,
        "answer": result["answer"],
        "sources": result["sources"]
    }
