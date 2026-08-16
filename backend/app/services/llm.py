"""LLM Service for DapurPangan — Dual mode: OpenCodeZen + rule-based fallback."""
import os, logging, re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

API_KEY = os.getenv("OPencodeZen_API_KEY")
BASE_URL = os.getenv("OPencodeZen_BASE_URL", "https://opencode.ai/zen/v1")
MODEL = os.getenv("OPencodeZen_MODEL", "deepseek-v4-flash-free")

logger = logging.getLogger("daparpangan.llm")

# ===== Rule-based fallback responses (angka disinkronkan dengan data aktual) =====
FALLBACK_RESPONSES = {
    "harga": "💡 Biaya produksi per tempe: Rp 1.181. Harga jual minimal: Rp 1.418 (margin 20%). Dengan pasar Rp 4.500-Rp 5.500, rekomendasi optimal Rp 4.500.",
    "jual": "💰 Rekomendasi harga jual tempe: minimal Rp 1.418 (margin 20%), optimal Rp 4.500 (masih di bawah pasar Rp 4.500-Rp 5.500).",
    "produksi": "🏭 Besok rekomendasi produksi: 222 tempe (confidence 71%, dari 14 hari data).",
    "stok": "📦 Stok kedelai: 50 kg (cukup ±2 hari produksi — beli segera). Ragi: 80 g (habis hari ini 🔴 — beli 100g). Plastik: 220 pcs (cukup ±1 hari 🟡).",
    "pelanggan": "📊 Top: Pasar C (±56%), Warung B (22%), Warung A (13%). ⚠️ Kantin D turun 30% — cek apakah ada masalah.",
    "basi": "⚠️ Tempe untuk Pasar C berisiko basi jika tidak diprioritaskan. Shelf-life tempe 2 hari, estimasi kirim 15 menit - masih aman.",
    "ragi": "🔴 Stok ragi tinggal 80g, cukup ±160 bungkus (kurang dari 1 hari produksi). Beli 100g sekarang.",
    "penjualan": "📈 Untuk menaikkan penjualan: tawarkan pesanan rutin ke warung, beri harga grosir untuk pembelian banyak, dan pastikan produksi cukup di hari ramai (lihat prediksi produksi di dashboard).",
    "lebaran": "🌙 H-7 Lebaran: rekomendasi naikkan produksi 40% (290 tempe/hari). Tahun lalu permintaan melonjak 40%!",
}

SYSTEM_PROMPT = """Kamu adalah asisten AI untuk DapurPangan, platform dashboard IRTP (Industri Rumah Tangga Pangan).
Kamu membantu Bu Sumi (produsen tempe dari Lamongan) dalam bahasa Indonesia yang santai dan hangat.

Konteks Bu Sumi:
- Usaha: Tempe Berkah Lamongan, produksi ~222 bungkus/hari (prediksi ML 14 hari terakhir)
- Bahan baku: Kedelai (50 kg stok), Ragi (80g — habis kurang dari 1 hari)
- Pelanggan: Warung A (30/hr), Warung B (50/hr), Pasar C (~115/hr), Kantin D (20/hr — turun 30%)
- Harga kedelai naik 13% (Rp 10.200 → Rp 11.500/kg)
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
            max_tokens=2000,
            temperature=0.7,
            timeout=90,
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
    # Urutan prioritas: konteks SPESIFIK dicek lebih dulu (lebaran, ragi, ...)
    # lalu yang umum (stok, produksi, harga). Word-boundary: 'jual' != 'penjualan'.
    priority = ["lebaran", "ragi", "penjualan", "basi", "pelanggan", "stok",
                "produksi", "harga", "jual"]
    for key in priority:
        if re.search(rf"\b{key}\b", msg):
            return FALLBACK_RESPONSES[key]
    return "Maaf, saya belum paham. Coba tanya tentang: produksi, harga, stok, pelanggan, atau lebaran 😊"
