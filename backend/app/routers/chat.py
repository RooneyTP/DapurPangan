"""Simple AI Chat endpoint for Zephyrus."""
from fastapi import APIRouter
from app.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api", tags=["Chat"])

RESPONSES = {
    "harga": "💡 Biaya produksi per tempe: Rp 3.200. Harga jual aman: Rp 4.000-Rp 5.000. Dengan harga pasar Rp 4.500-Rp 5.500, Ibu bisa jual Rp 5.000 dengan margin 36%.",
    "jual": "💰 Rekomendasi harga jual tempe: minimal Rp 4.000 (margin 20%), optimal Rp 5.000 (margin 36%). Harga pasar saat ini Rp 4.500-Rp 5.500.",
    "produksi": "🏭 Besok rekomendasi produksi: 210 tempe (confidence 87%). Naik 10% dari minggu lalu karena mendekati Lebaran.",
    "stok": "📦 Stok kedelai: 50 kg (cukup 7 hari ✅). Ragi: 80 g (HABIS dalam 1 hari 🔴 - beli 100g Rp 5.000). Plastik: 220 pcs (cukup 5 hari 🟡).",
    "pelanggan": "📊 Top: Warung B (25%), Pasar C (22%), Warung A (15%). ⚠️ Kantin D turun 30% - mungkin ada masalah.",
    "basi": "⚠️ 3 tempe untuk Pasar C berisiko basi jika tidak diprioritaskan. Shelf-life tempe 2 hari, estimasi kirim 15 menit - masih aman.",
    "ragi": "🔴 Stok ragi tinggal 80g, cukup untuk 1 hari produksi (160 tempe). Beli 100g sekarang - Rp 5.000 di toko bahan kue.",
    "lebaran": "🌙 H-7 Lebaran: rekomendasi naikkan produksi 40% (290 tempe/hari). Tahun lalu permintaan melonjak 40%!",
}


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Simple rule-based chat (tanpa LLM). Nanti bisa diganti OpenCodeZen."""
    msg = request.message.lower()
    for key, reply in RESPONSES.items():
        if key in msg:
            return ChatResponse(reply=reply)
    return ChatResponse(
        reply="Maaf, saya belum paham. Coba tanya tentang: produksi, harga, stok, pelanggan, atau lebaran 😊"
    )
