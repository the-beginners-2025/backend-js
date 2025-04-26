import os

from dotenv import load_dotenv

from services.llm_service import LLMService
from services.ocr_service import OCRService
from services.rag_service import RAGService

load_dotenv()

RAG_TOKEN = os.getenv("RAG_TOKEN")
RAG_ENDPOINT = os.getenv("RAG_ENDPOINT")
RAG_CHAT_ID = os.getenv("RAG_CHAT_ID")
RAG_AUTHORIZATION = os.getenv("RAG_AUTHORIZATION")
if not RAG_TOKEN or not RAG_ENDPOINT or not RAG_CHAT_ID or not RAG_AUTHORIZATION:
    raise RuntimeError(
        "RAG_TOKEN, RAG_ENDPOINT, RAG_CHAT_ID, and RAG_AUTHORIZATION environment variables not set"
    )
rag_service = RAGService(
    token=RAG_TOKEN,
    endpoint=RAG_ENDPOINT,
)

LLM_TOKEN = os.getenv("LLM_TOKEN")
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT")
LLM_MODEL = os.getenv("LLM_MODEL")
if not LLM_TOKEN or not LLM_ENDPOINT or not LLM_MODEL:
    raise RuntimeError(
        "LLM_TOKEN, LLM_ENDPOINT, and LLM_MODEL environment variables not set"
    )
llm_service = LLMService(
    token=LLM_TOKEN,
    endpoint=LLM_ENDPOINT,
)

OCR_TOKEN = os.getenv("OCR_TOKEN")
OCR_ENDPOINT = os.getenv("OCR_ENDPOINT")
if not OCR_TOKEN or not OCR_ENDPOINT:
    raise RuntimeError("OCR_TOKEN or OCR_ENDPOINT environment variable not set")
ocr_service = OCRService(OCR_TOKEN, OCR_ENDPOINT)

LIGHT_GRAPH_ENDPOINT = os.getenv("LIGHT_GRAPH_ENDPOINT")
if not LIGHT_GRAPH_ENDPOINT:
    raise RuntimeError("LIGHT_GRAPH_ENDPOINT environment variable not set")
