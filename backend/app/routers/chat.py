"""Chat endpoint — LLM-powered dengan fallback rule-based."""
from fastapi import APIRouter
from app.schemas import ChatRequest, ChatResponse
from app.services.llm import get_llm_response

router = APIRouter(prefix="/api", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Tanya Zephyrus — pake OpenCodeZen kalau available, fallback rule-based."""
    reply = get_llm_response(request.message)
    return ChatResponse(reply=reply)
