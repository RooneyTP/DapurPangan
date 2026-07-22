"""LLM Service for DapurPangan — Dual mode: OpenCodeZen + rule-based fallback."""
import os, logging
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

API_KEY = os.getenv("OPencodeZen_API_KEY")
BASE_URL = os.getenv("OPencodeZen_BASE_URL", "https://opencode.ai/zen/v1")
MODEL = os.getenv("OPencodeZen_MODEL", "gpt-4o-mini")

logger = logging.getLogger("zephyrus.llm")

# ===== Rule-based fallback responses =====
FALLBACK_RESPONSES = {
    "harga": "💡 Biaya produksi per tempe: Rp 3.200. Harga jual aman: Rp 4.000-Rp 5.000. Dengan harga pasar Rp 4.500-Rp 5.500, Ibu bisa jual Rp 5.000 dengan margin 36%.",
    "jual": "💰 Rekomendasi harga jual tempe: minimal Rp 4.000 (margin 20%), optimal Rp 5.000 (margin 36%). Harga pasar saat ini Rp 4.500-Rp 5.500.",
    "produksi": "🏭 Besok rekomendasi produksi: 210 tempe (confidence 87%). Naik 10% dari minggu lalu karena mendekati Lebaran.",
    "stok": "📦 Stok kedelai: 50 kg (cukup 7 hari ✅). Ragi: 80 g (HABIS dalam 1 hari 🔴 - beli 100g Rp 5.000). Plastik: 220 pcs (cukup 5 hari 🟡).",
    "pelanggan": "📊 Top: Warung B (25%), Pasar C (22%), Warung A (15%). ⚠️ Kantin D turun 30% - mungkin ada masalah.",
    "basi": "⚠️ 3 tempe untuk Pasar C berisiko basi jika tidak diprioritaskan. Shelf-life tempe 2 hari, estimasi kirim 15 menit - masih aman.",
    "ragi": "🔴 Stok ragi tinggal 80g, cukup untuk 1 hari produksi (160 tempe). Beli 100g sekarang - Rp 5.000 di toko bahan kue.",
    "lebaran": "🌙 H-7 Lebaran: rekomendasi naikkan produksi 40% (290 tempe/hari). Tahun lalu permintaan melonjak 40%!",
}

SYSTEM_PROMPT = """Kamu adalah asisten AI untuk DapurPangan, platform dashboard IRTP (Industri Rumah Tangga Pangan).
Kamu membantu Bu Sumi (produsen tempe dari Lamongan) dalam bahasa Indonesia yang santai dan hangat.

Konteks Bu Sumi:
- Usaha: Tempe Berkah Lamongan, produksi ~200-300 bungkus/hari
- Bahan baku: Kedelai (50 kg stok), Ragi (80g — hampir habis)
- Pelanggan: Warung A (30/hr), Warung B (50/hr), Pasar C (110/hr), Kantin D (20/hr — turun 30%)
- Harga kedelai naik 12% minggu depan (Rp 11.500 → Rp 12.900/kg)
- H-7 Lebaran: permintaan naik 40%

Jawab dengan:
1. Hangat dan akrab seperti ngobrol dengan IRTP
2. Berisi saran konkret, bukan teori
3. Gunakan emoji secukupnya
4. Maksimal 3-4 kalimat
5. Jika ditanya di luar konteks IRTP, arahkan kembali ke topik produksi/stok/pelanggan"""


def get_llm_response(message: str) -> str:
    """Coba OpenCodeZen dulu, fallback ke rule-based jika gagal."""
    if not API_KEY or API_KEY == "sk-your-key-here":
        return _rule_based_fallback(message)

    try:
        client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            max_tokens=300,
            temperature=0.7,
            timeout=15,
        )
        reply = resp.choices[0].message.content.strip()
        if reply:
            return reply
    except Exception as e:
        logger.warning(f"OpenCodeZen API error: {e}")

    # Fallback
    return _rule_based_fallback(message)


def _rule_based_fallback(message: str) -> str:
    """Rule-based fallback ketika API tidak tersedia."""
    msg = message.lower()
    for key, reply in FALLBACK_RESPONSES.items():
        if key in msg:
            return reply
    return "Maaf, saya belum paham. Coba tanya tentang: produksi, harga, stok, pelanggan, atau lebaran 😊"
