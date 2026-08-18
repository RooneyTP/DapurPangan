"""Chat endpoint — LLM-powered dengan fallback dinamis (data DB live)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas import ChatRequest, ChatResponse
from app.services.llm import get_llm_response
from app.services.data_entry import try_data_entry
from app.database import get_db

router = APIRouter(prefix="/api", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """AI data entry (rule-based) dulu; sisanya LLM + fallback data DB live."""
    entry_reply = try_data_entry(request.message, db)
    if entry_reply:
        return ChatResponse(reply=entry_reply)

    reply = get_llm_response(request.message, db=db)
    return ChatResponse(reply=reply)
