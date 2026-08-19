"""Chat endpoint — LLM-powered dengan fallback dinamis (data DB live).

Menyimpan riwayat percakapan (ChatMessage) ke database dan memakainya
sebagai konteks chat (memori chat) + konteks database LIVE di system prompt.

DESAIN SINGLE-USER (scope lomba): riwayat chat global, TANPA kolom
user/session/autentikasi. Kalau nanti jadi multi-user, tambahkan kolom
user_id di ChatMessage dan filter query history per user.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import ChatRequest, ChatResponse, ChatHistoryItem
from app.services.llm import get_llm_response
from app.services.data_entry import try_data_entry
from app.database import get_db
from app.models import ChatMessage

logger = logging.getLogger("daparpangan.chat")

router = APIRouter(prefix="/api", tags=["Chat"])

# Pesan user dipotong sebelum disimpan supaya DB tidak diisi spam panjang
MAX_MESSAGE_LEN = 500


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Simpan pesan user, AI data entry (rule-based) dulu; sisanya LLM + fallback data DB live.

    Riwayat chat (10 pesan terakhir SEBELUM pesan baru) ikut dikirim sebagai
    konteks ke LLM, lalu jawaban assistant disimpan juga ke database.
    """
    # Tolak pesan kosong/whitespace SEBELUM menyimpan apa pun
    msg_text = (request.message or "").strip()
    if not msg_text:
        raise HTTPException(status_code=400, detail="Pesan tidak boleh kosong.")

    # Truncate sebelum simpan (defense in depth, sama seperti batas history LLM)
    msg_text = msg_text[:MAX_MESSAGE_LEN]

    # Simpan pesan user sebelum diproses
    pesan_baru = ChatMessage(role="user", content=msg_text)
    db.add(pesan_baru)
    db.commit()
    db.refresh(pesan_baru)

    # Riwayat 10 pesan TERAKHIR SEBELUM pesan baru ini (id < pesan_baru.id),
    # urut kronologis — pesan user terbaru JANGAN ikut terambil (anti duplikat).
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.id < pesan_baru.id)
        .order_by(ChatMessage.id.desc())
        .limit(10)
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in reversed(rows)]

    # Data entry rule-based: kalau error (DB dsb), balas pesan error ramah,
    # jangan biarkan request jadi HTTP 500.
    try:
        entry_reply = try_data_entry(msg_text, db)
        if entry_reply:
            db.add(ChatMessage(role="assistant", content=entry_reply))
            db.commit()
            return ChatResponse(reply=entry_reply)
    except Exception as e:
        db.rollback()
        logger.warning(f"Data entry error ({type(e).__name__}): {e}")
        reply = ("Maaf, data gagal disimpan. Coba ulangi dengan format yang "
                 "benar (misal: 'stok kedelai 30 kg' atau 'pesanan Warung A 30').")
        db.add(ChatMessage(role="assistant", content=reply))
        db.commit()
        return ChatResponse(reply=reply)

    reply = get_llm_response(msg_text, db=db, history=history)

    db.add(ChatMessage(role="assistant", content=reply))
    db.commit()
    return ChatResponse(reply=reply)


@router.get("/chat/history", response_model=list[ChatHistoryItem])
def chat_history(db: Session = Depends(get_db)):
    """Riwayat 50 pesan terakhir, urut ascending (terlama dulu)."""
    rows = db.query(ChatMessage).order_by(ChatMessage.id.desc()).limit(50).all()
    return [ChatHistoryItem(role=m.role, content=m.content) for m in reversed(rows)]
