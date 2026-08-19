"""AI Data Entry — input data lewat chat dengan rule-based regex (tanpa LLM).

Pola yang didukung (prioritas tinggi → rendah):
1. Pesanan massal   : "hari ini ada 100 pelanggan yang masing masing beli 1 tempe"
2. Pesanan spesifik : "pesanan Warung A 30" / "catat pesanan Budi 10 tempe"
3. Pelanggan baru   : "tambah pelanggan Budi, Jl. Kenanga 5, 081234567890"
4. Stok             : "stok kedelai 30 kg" (menimpa) / "tambah stok ragi 0.1 kg" (menambah)

Semua handler deterministik: kalau pesan cocok → simpan ke DB + return string
konfirmasi; kalau tidak cocok → return None (biarkan chat normal ke LLM).
Tidak pernah raise HTTPException — selalu return string atau None.
"""
import logging
import re
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from app.models import Customer, Order, Product, Stock

logger = logging.getLogger("daparpangan.data_entry")

# Pertanyaan tidak pernah dianggap input data
_QUESTION_PREFIX = re.compile(
    r'^(berapa|apa|bagaimana|kapan|siapa|tolong\s+(cek|lihat|info))', re.IGNORECASE
)

# --- Pola 1: pesanan massal ---
_BULK_CUSTOMERS = re.compile(r'(\d+)\s*pelanggan', re.IGNORECASE)
_BULK_EACH = re.compile(r'masing[-\s]*masing\s*(?:beli|membeli)?\s*(\d+)', re.IGNORECASE)
_BULK_ATAS_NAMA = re.compile(
    r'atas nama\s+([A-Za-z0-9][A-Za-z0-9 .\'\-]*?)(?=\s+untuk|\s*$)', re.IGNORECASE
)

# --- Pola 2: pesanan spesifik ---
_SPECIFIC_ORDER = re.compile(
    r'(?:(?:catat|input)\s+)?(?:pesanan|order)\s+([A-Za-z0-9][A-Za-z0-9 .\'\-]*?)\s+(\d+)\s*([A-Za-z ]+)?$',
    re.IGNORECASE,
)

# --- Pola 3: pelanggan baru ---
_NEW_CUSTOMER = re.compile(
    r'(?:tambah|daftar(?:kan)?)\s+pelanggan\s+([A-Za-z0-9][A-Za-z0-9 .\'\-]*?)'
    r'(?:\s*,\s*([^,]+))?(?:\s*,\s*(\S+))?\s*$',
    re.IGNORECASE,
)

# --- Pola 4: stok ---
# Awalan 'tambah' = menambah (+=), 'set'/'input'/tanpa awalan = menimpa (=).
# Anchor $ supaya kalimat panjang/pertanyaan tidak masuk pola ini.
# Harga opsional di akhir ikut ditangkap (grup 5).
_STOCK = re.compile(
    r'(?:(tambah(?:kan)?|set|input)\s+)?stok\s+([A-Za-z0-9][A-Za-z0-9 .\'\-]*?)'
    r'\s+(\d+(?:[.,]\d+)?)\s*(kg|g|liter|lembar|pcs|bungkus)?'
    r'(?:\s+harga\s*(?:rp\s*)?(\d+))?\s*$',
    re.IGNORECASE,
)


def try_data_entry(message: str, db) -> str | None:
    """Kalau pesan cocok dengan pola input data -> proses & simpan, return konfirmasi.

    Kalau tidak cocok -> return None (biarkan chat normal ke LLM).
    """
    if not message or not message.strip():
        return None
    msg = message.strip()

    # Jangan tangkap pertanyaan ("berapa stok kedelai?" bukan input data)
    if _QUESTION_PREFIX.match(msg):
        return None
    if re.search(r'\btanya\b', msg, re.IGNORECASE):
        return None

    # Prioritas pola: (1) pesanan massal, (2) pesanan spesifik,
    # (3) pelanggan baru, (4) stok.
    for handler in (_bulk_order, _specific_order, _new_customer, _stock_entry):
        reply = handler(msg, db)
        if reply is not None:
            return reply
    return None


# ============================== Helpers ==============================

def _find_or_create_customer(db, name: str) -> Customer:
    """Cari customer case-insensitive; kalau tidak ada, buat baru (flush biar dapat id)."""
    name = name.strip()
    existing = db.query(Customer).filter(func.lower(Customer.name) == name.lower()).first()
    if existing:
        return existing
    cust = Customer(name=name, address='', phone='')
    db.add(cust)
    db.flush()
    return cust


def _find_product(db, message: str):
    """Cari produk yang namanya muncul sebagai KATA utuh (word-boundary).

    'tahukah' TIDAK cocok dengan produk 'tahu' karena \b memisahkan kata.
    """
    ml = message.lower()
    for p in db.query(Product).all():
        if re.search(rf'\b{re.escape(p.name.lower())}\b', ml):
            return p
    return None


def _find_or_create_stock(db, name: str) -> Stock:
    """Cari stok case-insensitive; kalau tidak ada, buat baru (quantity 0, unit kg)."""
    name = name.strip()
    existing = db.query(Stock).filter(func.lower(Stock.ingredient_name) == name.lower()).first()
    if existing:
        return existing
    stock = Stock(ingredient_name=name, quantity=0, unit='kg')
    db.add(stock)
    db.flush()
    return stock


def _first_product_or_none(db):
    prod = db.query(Product).first()
    return prod


def _commit_or_rollback(db, ok_msg: str, err_msg: str) -> str:
    """Commit; kalau error SQLAlchemy umum (IntegrityError dkk) → rollback + pesan error."""
    try:
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.warning(f"Commit gagal ({type(e).__name__}): {e}")
        return err_msg
    return ok_msg


# ============================ Pola 1: massal ============================

def _bulk_order(message: str, db) -> str | None:
    """'... N pelanggan ... masing masing beli M <produk>' → 1 Order total N*M."""
    m_cust = _BULK_CUSTOMERS.search(message)
    m_each = _BULK_EACH.search(message)
    if not (m_cust and m_each):
        return None

    n_cust = int(m_cust.group(1))
    per_orang = int(m_each.group(1))
    total = n_cust * per_orang
    if total < 1 or total > 10000:
        return f"Jumlah tidak masuk akal ({total}). Cek lagi ya."

    # Tanggal: hari ini / sekarang / tadi → today; kemarin → kemarin; else today
    if re.search(r'hari ini|sekarang|\btadi\b', message, re.IGNORECASE):
        tgl = date.today()
    elif re.search(r'kemarin', message, re.IGNORECASE):
        tgl = date.today() - timedelta(days=1)
    else:
        tgl = date.today()

    # Produk: cari di pesan → fallback produk pertama → kalau kosong, tolak
    prod = _find_product(db, message)
    if prod is None:
        prod = _first_product_or_none(db)
    if prod is None:
        return "Belum ada produk terdaftar. Tambahkan produk dulu."

    # Customer: "atas nama X" kalau ada, selain itu Pelanggan Umum
    m_an = _BULK_ATAS_NAMA.search(message)
    cust_name = m_an.group(1).strip() if m_an else "Pelanggan Umum"
    cust = _find_or_create_customer(db, cust_name)

    order = Order(customer_id=cust.id, product_id=prod.id, date=tgl,
                  quantity=total, status='pending')
    db.add(order)
    ok = (f"✅ Dicatat: {total} {prod.name} ({n_cust} pelanggan x {per_orang}) "
          f"untuk {tgl} atas nama {cust.name}.")
    return _commit_or_rollback(db, ok, "Gagal menyimpan pesanan (data bentrok). Coba lagi.")


# ========================= Pola 2: pesanan spesifik =========================

def _specific_order(message: str, db) -> str | None:
    """'pesanan <nama> <jumlah> [<produk>]' → 1 Order untuk customer tsb."""
    m = _SPECIFIC_ORDER.search(message)
    if not m:
        return None

    name = m.group(1).strip()
    qty = int(m.group(2))
    if qty < 1:
        return "Jumlah pesanan harus minimal 1."
    # Cap konsisten dengan jalur pesanan massal (maksimal 10000)
    if qty > 10000:
        return f"Jumlah pesanan tidak masuk akal ({qty}, maksimal 10000). Cek lagi ya."

    prod = _find_product(db, message)
    if prod is None:
        prod = _first_product_or_none(db)
    if prod is None:
        return "Belum ada produk terdaftar. Tambahkan produk dulu."

    cust = _find_or_create_customer(db, name)
    order = Order(customer_id=cust.id, product_id=prod.id, date=date.today(),
                  quantity=qty, status='pending')
    db.add(order)
    ok = f"✅ Pesanan {cust.name} dicatat: {qty} {prod.name} ({date.today()})."
    return _commit_or_rollback(db, ok, "Gagal menyimpan pesanan (data bentrok). Coba lagi.")


# ========================= Pola 3: pelanggan baru =========================

def _new_customer(message: str, db) -> str | None:
    """'tambah pelanggan <nama>[, <alamat>[, <telepon>]]' → Customer baru (tanpa duplikat)."""
    m = _NEW_CUSTOMER.search(message)
    if not m:
        return None

    name = m.group(1).strip()
    address = (m.group(2) or '').strip()
    phone = (m.group(3) or '').strip()

    existing = db.query(Customer).filter(func.lower(Customer.name) == name.lower()).first()
    if existing:
        return f"Pelanggan {name} sudah ada (id {existing.id})."

    cust = Customer(name=name, address=address, phone=phone)
    db.add(cust)
    ok = f"✅ Pelanggan {name} ditambahkan."
    if address:
        ok += f" Alamat: {address}."
    if phone:
        ok += f" Telepon: {phone}."
    return _commit_or_rollback(db, ok, "Gagal menambahkan pelanggan (data bentrok). Coba lagi.")


# ============================= Pola 4: stok =============================

def _stock_entry(message: str, db) -> str | None:
    """'[tambah|set|input] stok <nama> <jumlah> [unit] [harga Rp N]' → upsert Stock.

    - 'tambah' = menambah stok (+=), bukan menimpa.
    - Tanpa awalan / 'set' / 'input' = menimpa (=).
    - Pertanyaan (akhiran '?') atau kalimat negasi TIDAK dieksekusi.
    """
    msg = message.strip()
    # Pertanyaan & negasi bukan perintah input — jangan ubah data
    if msg.endswith('?'):
        return None
    if re.search(r'\b(jangan|bukan|tidak)\b', msg, re.IGNORECASE):
        return None

    m = _STOCK.search(msg)
    if not m:
        return None

    prefix = (m.group(1) or '').lower()
    raw_name = m.group(2).strip()
    qty = float(m.group(3).replace(',', '.'))
    if qty < 0:
        return "Jumlah stok tidak boleh negatif."

    # Simpan nama dengan huruf depan kapital (ragi → Ragi) biar konsisten di DB
    name = raw_name[:1].upper() + raw_name[1:]
    stock = _find_or_create_stock(db, name)
    unit = m.group(4) or stock.unit or 'kg'

    if prefix.startswith('tambah'):
        stock.quantity = (stock.quantity or 0) + qty
        total_str = f"{stock.quantity:g} {unit}"
        ok = f"✅ Stok {stock.ingredient_name} ditambah {qty:g} {unit} (total: {total_str})"
    else:
        stock.quantity = qty
        ok = f"✅ Stok {stock.ingredient_name} = {qty:g} {unit}"
    stock.unit = unit

    harga = None
    if m.group(5):
        harga = int(m.group(5))
        stock.price_per_unit = harga
        ok += f", harga Rp {harga}"

    return _commit_or_rollback(db, ok, "Gagal menyimpan stok (data bentrok). Coba lagi.")
