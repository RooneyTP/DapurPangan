"""Import CSV — stok, pelanggan, dan pesanan massal.

Setiap baris divalidasi satu per satu; hasilnya dilaporkan dalam bentuk
jumlah berhasil (imported), jumlah gagal (failed), dan daftar error
per baris (maksimal 20 entri). Commit dilakukan satu kali di akhir.
"""
import csv
import io
import math
from datetime import date
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import Stock, Customer, Order, Product, Sale

router = APIRouter(prefix="/api/import", tags=["Import"])

VALID_ORDER_STATUSES = {"pending", "delivered", "cancelled"}


def _decode(payload: bytes) -> str:
    """Decode CSV: utf-8-sig dulu (BOM Excel), fallback cp1252 (Excel Indonesia)."""
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return payload.decode(enc)
        except UnicodeDecodeError:
            continue
    raise HTTPException(422, "File tidak bisa dibaca sebagai teks")


def _check_header(fieldnames, required: list[str]) -> None:
    """Pastikan header CSV memuat semua kolom wajib, kalau tidak → 422."""
    missing = [c for c in required if c not in (fieldnames or [])]
    if missing:
        raise HTTPException(
            422,
            "Format CSV salah. Header wajib: " + ", ".join(required)
        )


def _parse_optional_float(value):
    """Parse float opsional: kosong -> (None, None), tidak valid -> (None, error).

    Non-finite (NaN/Infinity) ditolak supaya tidak pernah masuk DB.
    """
    s = (value or "").strip()
    if not s:
        return None, None
    try:
        f = float(s)
    except ValueError:
        return None, "harus angka"
    if not math.isfinite(f):
        return None, "harus angka terbatas (bukan NaN/Infinity)"
    return f, None


def _finish(kind: str, imported: int, errors: list, db: Session) -> dict:
    """Commit sekali di akhir; kalau gagal → rollback + lapor. Error dipotong 20."""
    if imported > 0:
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            imported = 0
            errors.append({"row": None, "reason": "Gagal menyimpan batch (konflik database)"})
    return {
        "kind": kind,
        "imported": imported,
        "failed": len(errors),
        "errors": errors[:20],
    }


@router.post("/stocks")
def import_stocks(payload: bytes = Body(...), db: Session = Depends(get_db)):
    """Import stok dari CSV. Header wajib: ingredient_name, quantity.

    Opsional: unit, price_per_unit, min_warning, min_critical.
    Baris duplikat (case-insensitive, terhadap DB & batch ini) dilewati.
    """
    reader = csv.DictReader(io.StringIO(_decode(payload)))
    _check_header(reader.fieldnames, ["ingredient_name", "quantity"])

    imported = 0
    errors = []
    imported_names: set[str] = set()  # nama stok yang sudah diimpor di batch ini

    for idx, raw in enumerate(reader, start=2):
        name = (raw.get("ingredient_name") or "").strip()
        if not name:
            errors.append({"row": idx, "reason": "Nama bahan wajib diisi"})
            continue

        try:
            qty = float((raw.get("quantity") or "").strip())
        except ValueError:
            errors.append({"row": idx, "reason": "quantity harus angka"})
            continue
        if not math.isfinite(qty) or qty < 0:
            errors.append({"row": idx, "reason": "quantity harus angka >= 0"})
            continue

        # Cek duplikat case-insensitive: terhadap DB dan batch ini
        key = name.lower()
        exists = db.query(Stock).filter(func.lower(Stock.ingredient_name) == key).first()
        if exists or key in imported_names:
            errors.append({"row": idx, "reason": f"Stok '{name}' sudah ada"})
            continue

        unit = (raw.get("unit") or "").strip() or "kg"
        price, price_err = _parse_optional_float(raw.get("price_per_unit"))
        if price_err:
            errors.append({"row": idx, "reason": "price_per_unit " + price_err})
            continue
        min_warning, warn_err = _parse_optional_float(raw.get("min_warning"))
        if warn_err:
            errors.append({"row": idx, "reason": "min_warning " + warn_err})
            continue
        min_critical, crit_err = _parse_optional_float(raw.get("min_critical"))
        if crit_err:
            errors.append({"row": idx, "reason": "min_critical " + crit_err})
            continue

        try:
            with db.begin_nested():
                db.add(Stock(
                    ingredient_name=name,
                    quantity=qty,
                    unit=unit,
                    price_per_unit=price,
                    min_warning=min_warning,
                    min_critical=min_critical,
                ))
                # flush eksplisit: IntegrityError ketangkap per baris (savepoint),
                # bukan menunggu commit akhir yang menggagalkan seluruh batch
                db.flush()
        except IntegrityError:
            errors.append({"row": idx, "reason": f"Stok '{name}' sudah ada"})
            continue
        except OverflowError:
            errors.append({"row": idx, "reason": "Angka terlalu besar"})
            continue
        imported_names.add(key)
        imported += 1

    return _finish("stocks", imported, errors, db)


@router.post("/customers")
def import_customers(payload: bytes = Body(...), db: Session = Depends(get_db)):
    """Import pelanggan dari CSV. Header wajib: name.

    Opsional: address, phone, notes. Nama duplikat (case-insensitive,
    terhadap DB & batch ini) dilewati + dilaporkan, bukan insert baru.
    """
    reader = csv.DictReader(io.StringIO(_decode(payload)))
    _check_header(reader.fieldnames, ["name"])

    imported = 0
    errors = []
    imported_names: set[str] = set()  # nama pelanggan yang sudah diimpor di batch ini

    for idx, raw in enumerate(reader, start=2):
        name = (raw.get("name") or "").strip()
        if not name:
            errors.append({"row": idx, "reason": "Nama pelanggan wajib diisi"})
            continue

        # Dedup case-insensitive: sudah ada di DB atau di batch ini? skip
        key = name.lower()
        exists = db.query(Customer).filter(
            func.lower(Customer.name) == key
        ).first()
        if exists or key in imported_names:
            errors.append({"row": idx, "reason": f"Pelanggan '{name}' sudah ada"})
            continue

        try:
            with db.begin_nested():
                db.add(Customer(
                    name=name,
                    address=(raw.get("address") or "").strip() or None,
                    phone=(raw.get("phone") or "").strip() or None,
                    notes=(raw.get("notes") or "").strip() or None,
                ))
                db.flush()
        except IntegrityError:
            errors.append({"row": idx, "reason": "Gagal menyimpan pelanggan (konflik database)"})
            continue
        except OverflowError:
            errors.append({"row": idx, "reason": "Angka terlalu besar"})
            continue
        imported_names.add(key)
        imported += 1

    return _finish("customers", imported, errors, db)


@router.post("/orders")
def import_orders(payload: bytes = Body(...), db: Session = Depends(get_db)):
    """Import pesanan dari CSV. Header wajib: customer_name, product_name, date, quantity.

    Opsional: status (default 'pending'; nilai di luar pending/delivered/cancelled
    dianggap 'pending'). Pelanggan/produk yang tidak dikenal → baris dilewati.
    """
    reader = csv.DictReader(io.StringIO(_decode(payload)))
    _check_header(reader.fieldnames, ["customer_name", "product_name", "date", "quantity"])

    imported = 0
    errors = []
    imported_orders: set = set()  # kombinasi (customer, product, date, qty) batch ini

    for idx, raw in enumerate(reader, start=2):
        customer_name = (raw.get("customer_name") or "").strip()
        if not customer_name:
            errors.append({"row": idx, "reason": "customer_name wajib diisi"})
            continue
        customer = db.query(Customer).filter(
            func.lower(Customer.name) == customer_name.lower()
        ).first()
        if not customer:
            errors.append({"row": idx, "reason": f"Pelanggan '{customer_name}' tidak ditemukan"})
            continue

        product_name = (raw.get("product_name") or "").strip()
        if not product_name:
            errors.append({"row": idx, "reason": "product_name wajib diisi"})
            continue
        product = db.query(Product).filter(
            func.lower(Product.name) == product_name.lower()
        ).first()
        if not product:
            errors.append({"row": idx, "reason": f"Produk '{product_name}' tidak ditemukan"})
            continue

        try:
            order_date = date.fromisoformat((raw.get("date") or "").strip())
        except ValueError:
            errors.append({"row": idx, "reason": "date harus format YYYY-MM-DD"})
            continue

        try:
            qty = int((raw.get("quantity") or "").strip())
        except ValueError:
            errors.append({"row": idx, "reason": "quantity harus bilangan bulat"})
            continue
        if qty < 1:
            errors.append({"row": idx, "reason": "quantity harus >= 1"})
            continue
        if qty > 1_000_000:
            errors.append({"row": idx, "reason": "quantity terlalu besar (maks 1000000)"})
            continue

        status = (raw.get("status") or "").strip().lower() or "pending"
        if status not in VALID_ORDER_STATUSES:
            status = "pending"

        # Dedup: kombinasi (customer, product, date, quantity) sudah ada? skip
        combo = (customer.id, product.id, order_date, qty)
        exists_order = db.query(Order).filter(
            Order.customer_id == customer.id,
            Order.product_id == product.id,
            Order.date == order_date,
            Order.quantity == qty,
        ).first()
        if exists_order or combo in imported_orders:
            errors.append({
                "row": idx,
                "reason": "Pesanan duplikat (customer, product, date, quantity yang sama sudah ada)",
            })
            continue

        try:
            with db.begin_nested():
                db.add(Order(
                    customer_id=customer.id,
                    product_id=product.id,
                    date=order_date,
                    quantity=qty,
                    status=status,
                ))
                db.flush()
        except IntegrityError:
            errors.append({"row": idx, "reason": "Gagal menyimpan pesanan (konflik database)"})
            continue
        except OverflowError:
            errors.append({"row": idx, "reason": "Angka terlalu besar"})
            continue
        imported_orders.add(combo)
        imported += 1

    return _finish("orders", imported, errors, db)


@router.post("/sales")
def import_sales(payload: bytes = Body(...), db: Session = Depends(get_db)):
    """Import penjualan per individu (B2C) dari CSV.

    Header wajib: product_name, individual_count, quantity_per_individual.
    Opsional: date (format YYYY-MM-DD; default tanggal hari ini).
    Produk dicari case-insensitive; baris dengan produk tak dikenal,
    angka tidak valid (< 1), atau tanggal salah → dilewati + dilaporkan.
    """
    reader = csv.DictReader(io.StringIO(_decode(payload)))
    _check_header(reader.fieldnames, [
        "product_name", "individual_count", "quantity_per_individual"
    ])

    imported = 0
    errors = []

    for idx, raw in enumerate(reader, start=2):
        product_name = (raw.get("product_name") or "").strip()
        if not product_name:
            errors.append({"row": idx, "reason": "product_name wajib diisi"})
            continue
        product = db.query(Product).filter(
            func.lower(Product.name) == product_name.lower()
        ).first()
        if not product:
            errors.append({"row": idx, "reason": f"Produk '{product_name}' tidak ditemukan"})
            continue

        date_raw = (raw.get("date") or "").strip()
        if date_raw:
            try:
                sale_date = date.fromisoformat(date_raw)
            except ValueError:
                errors.append({"row": idx, "reason": "Tanggal harus format YYYY-MM-DD"})
                continue
        else:
            sale_date = date.today()

        try:
            individuals = int((raw.get("individual_count") or "").strip())
        except ValueError:
            errors.append({"row": idx, "reason": "individual_count harus bilangan bulat"})
            continue
        if individuals < 1:
            errors.append({"row": idx, "reason": "individual_count harus >= 1"})
            continue
        if individuals > 100_000:
            errors.append({"row": idx, "reason": "individual_count terlalu besar (maks 100000)"})
            continue

        try:
            qty_per = int((raw.get("quantity_per_individual") or "").strip())
        except ValueError:
            errors.append({"row": idx, "reason": "quantity_per_individual harus bilangan bulat"})
            continue
        if qty_per < 1:
            errors.append({"row": idx, "reason": "quantity_per_individual harus >= 1"})
            continue
        if qty_per > 100:
            errors.append({"row": idx, "reason": "quantity_per_individual terlalu besar (maks 100)"})
            continue

        try:
            with db.begin_nested():
                db.add(Sale(
                    product_id=product.id,
                    date=sale_date,
                    individual_count=individuals,
                    quantity_per_individual=qty_per,
                ))
                db.flush()
        except IntegrityError:
            errors.append({"row": idx, "reason": "Gagal menyimpan penjualan (konflik database)"})
            continue
        except OverflowError:
            errors.append({"row": idx, "reason": "Angka terlalu besar"})
            continue
        imported += 1

    return _finish("sales", imported, errors, db)
