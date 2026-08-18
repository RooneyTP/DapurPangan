"""LLM Service for DapurPangan — Dual mode: OpenCodeZen + fallback dinamis (DB)."""
import os, logging, re
from datetime import date, timedelta
from dotenv import load_dotenv
from openai import OpenAI

from app.models import Stock, Product, Order, Customer, Sale
from app.services.predictor import predictor, sales_predictor
from app.services.pricing import recommend_price

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


def get_llm_response(message: str, db=None) -> str:
    """Coba OpenCodeZen dulu, fallback dinamis-DB (atau rule-based) jika gagal.

    `db` opsional (sqlalchemy Session): kalau diberikan, fallback membaca data
    aktual dari database. Kalau None, pakai rule-based lama (backward compatible).
    """
    if not API_KEY or API_KEY == "sk-your-key-here":
        return _pick_fallback(message, db)

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
    return _pick_fallback(message, db)


def _pick_fallback(message: str, db) -> str:
    """Pilih fallback: dinamis (data DB live) kalau ada db, rule-based kalau tidak."""
    if db is not None:
        return _dynamic_db_fallback(message, db)
    return _rule_based_fallback(message)


def _fmt_qty(quantity: float, unit: str) -> str:
    """Format kuantitas rapi: 50 kg, 80 g, 220 pcs (bukan 0.08 kg)."""
    if unit == "kg" and quantity < 1:
        return f"{round(quantity * 1000)} g"
    if float(quantity).is_integer():
        return f"{int(quantity)} {unit}"
    return f"{quantity:.2f} {unit}"


def _stock_summary(db) -> str:
    """Ringkasan stok live: nama, kuantitas, dan status (AMAN/WASPADA/KRITIS)."""
    stocks = db.query(Stock).all()
    if not stocks:
        return "Belum ada stok tercatat."
    parts = []
    for s in stocks:
        if s.quantity < s.min_critical:
            status = "KRITIS - beli segera"
        elif s.quantity < s.min_warning:
            status = "WASPADA"
        else:
            status = "AMAN"
        parts.append(f"{s.ingredient_name}: {_fmt_qty(s.quantity, s.unit)} ({status})")
    return "Stok " + ". ".join(parts) + "."


def _prediction_text() -> str:
    """Prediksi produksi besok dari ML predictor (data produksi aktual)."""
    p = predictor.predict(date.today())
    return (f"Besok rekomendasi produksi: {p['prediction']} bungkus "
            f"(confidence {p['confidence_pct']}%, dari {p['data_points']} hari data).")


def _sales_prediction_text(db) -> str:
    """Prediksi penjualan B2C besok: perkiraan pembeli & unit terjual.

    Logika sama dengan GET /api/sales/prediction (duplikasi kecil tanpa
    import router): total unit per hari dari tabel Sale → fine-tune
    sales_predictor → prediksi unit besok; pembeli pakai rata-rata harian.
    """
    sales = db.query(Sale).all()
    if not sales:
        return ("Belum ada data penjualan. Catat penjualan dulu "
                "(misal: 'hari ini ada 50 orang beli 1 tempe').")

    per_day: dict = {}
    individuals_per_day: dict = {}
    for s in sales:
        per_day[s.date] = per_day.get(s.date, 0) + \
            s.individual_count * s.quantity_per_individual
        individuals_per_day[s.date] = individuals_per_day.get(s.date, 0) + \
            s.individual_count

    sales_predictor.reset()
    for d, total in sorted(per_day.items()):
        sales_predictor.add_data_point(d, total)

    tomorrow = date.today() + timedelta(days=1)
    p = sales_predictor.predict(tomorrow)
    avg_individuals = int(round(
        sum(individuals_per_day.values()) / len(individuals_per_day)
    ))
    return (f"Besok ({tomorrow}): diperkirakan ~{avg_individuals} pembeli, "
            f"~{p['prediction']} unit terjual (dari {p['data_points']} hari data).")


def _price_text(db):
    """Rekomendasi harga dari biaya produksi aktual. None kalau gagal dihitung."""
    prod = db.query(Product).first()
    if not prod:
        return None
    try:
        r = recommend_price(db=db, product_id=prod.id, margin_pct=20.0,
                            market_low=4500.0, market_high=5500.0)
    except Exception as e:
        logger.warning(f"Rekomendasi harga gagal: {e}")
        return None
    return (f"Biaya produksi {r['product_name']}: Rp {r['production_cost']:,.0f}. "
            f"Harga jual minimal: Rp {r['price_minimum']:,.0f} (margin 20%). "
            f"Rekomendasi optimal: Rp {r['price_optimal']:,.0f}.")


def _top_customers_text(db) -> str:
    """Top 3 pelanggan berdasarkan total quantity pesanan 7 hari terakhir."""
    since = date.today() - timedelta(days=7)
    rows = db.query(Order, Customer).join(
        Customer, Order.customer_id == Customer.id
    ).filter(Order.date > since).all()
    totals = {}
    for o, c in rows:
        totals[c.name] = totals.get(c.name, 0) + o.quantity
    if not totals:
        return "Belum ada pesanan 7 hari terakhir."
    top = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:3]
    return "Top pelanggan 7 hari: " + ", ".join(f"{n} ({q})" for n, q in top) + "."


def _today_summary(db) -> str:
    """Ringkasan singkat kondisi terkini: stok kritis + prediksi + harga."""
    stocks = db.query(Stock).all()
    kritis = [f"{s.ingredient_name} ({_fmt_qty(s.quantity, s.unit)})"
              for s in stocks if s.quantity < s.min_critical]
    parts = []
    if kritis:
        parts.append("🔴 Stok kritis: " + ", ".join(kritis))
    else:
        parts.append("🟢 Stok aman semua")
    parts.append(_prediction_text())
    price = _price_text(db)
    if price:
        parts.append(price)
    return " ".join(parts) + " Coba tanya: stok, produksi, harga, pelanggan, atau lebaran 😊"


def _dynamic_db_fallback(message: str, db) -> str:
    """Fallback dinamis: jawaban dibangun dari data LIVE di database."""
    msg = message.lower()
    # Urutan prioritas sama dengan rule-based lama: spesifik dulu, umum belakangan.
    priority = ["lebaran", "ragi", "penjualan", "basi", "pelanggan", "stok",
                "produksi", "pembeli", "besok", "harga", "jual"]
    for key in priority:
        if re.search(rf"\b{key}\b", msg):
            if key in ("stok", "ragi"):
                return "📦 " + _stock_summary(db)
            if key == "produksi":
                return "🏭 " + _prediction_text()
            if key in ("pembeli", "besok"):
                return "📈 " + _sales_prediction_text(db)
            if key in ("harga", "jual"):
                price = _price_text(db)
                if price:
                    return "💰 " + price
                # Harga gagal dihitung → jawab dengan data stok saja
                return "📦 " + _stock_summary(db)
            if key in ("pelanggan", "penjualan"):
                return "📊 " + _top_customers_text(db)
            if key == "lebaran":
                return ("🌙 " + _prediction_text() +
                        " Saran: naikkan produksi ±40% jelang Lebaran biar tidak kehabisan stok!")
            if key == "basi":
                return ("⚠️ " + _prediction_text() +
                        " Shelf-life tempe ±2 hari — prioritaskan kirim ke pelanggan terdekat dulu.")
    return _today_summary(db)


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
