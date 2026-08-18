"""Stock management endpoints."""
import math
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from app.database import get_db
from app.models import Product, Recipe, Stock
from app.schemas import StockBase, StockResponse
from app.services.predictor import predictor

router = APIRouter(prefix="/api/stocks", tags=["Stock"])


@router.get("/recommendations")
def stock_recommendations(db: Session = Depends(get_db)):
    """Rekomendasi pembelian stok otomatis.

    Kebutuhan bahan baku = prediksi produksi hari ini × kebutuhan per
    produk (dari resep), diakumulasi per bahan. Defisit = kebutuhan
    dikurangi stok yang ada → aksi 'beli' kalau defisit, 'waspada'
    kalau stok tersisa di bawah ambang min_warning, selain itu 'cukup'.
    """
    today = date.today()
    pred = predictor.predict(today)
    pred_qty = pred["prediction"]

    products = db.query(Product).all()

    # Akumulasi kebutuhan bahan dari resep semua produk
    needed_map: dict[str, float] = {}
    unit_map: dict[str, str] = {}
    for p in products:
        recipes = db.query(Recipe).filter(Recipe.product_id == p.id).all()
        for r in recipes:
            key = r.ingredient_name
            needed_map[key] = needed_map.get(key, 0.0) + r.quantity_per_unit * pred_qty
            unit_map.setdefault(key, r.unit or "kg")

    # Bahan yang dipertimbangkan: ada di resep ATAU di stok
    ingredients = set(needed_map.keys())
    ingredients.update(s.ingredient_name for s in db.query(Stock).all())

    items = []
    for name in ingredients:
        needed = needed_map.get(name, 0.0)
        # Cari stok: exact match dulu, fallback case-insensitive
        stock = db.query(Stock).filter(Stock.ingredient_name == name).first()
        if not stock:
            stock = db.query(Stock).filter(
                func.lower(Stock.ingredient_name) == name.lower()
            ).first()

        if stock:
            stock_qty = stock.quantity or 0.0
            unit = stock.unit or unit_map.get(name, "kg")
            min_warning = stock.min_warning if stock.min_warning is not None else 5.0
            deficit = max(0.0, needed - stock_qty)
            if deficit > 0:
                action = "beli"
            elif (stock_qty - needed) < min_warning:
                action = "waspada"
            else:
                action = "cukup"
        else:
            # Stok tidak tercatat sama sekali → anggap kosong
            stock_qty = 0.0
            unit = unit_map.get(name, "kg")
            deficit = max(0.0, needed)
            action = "beli"

        items.append({
            "ingredient_name": name,
            "stock": stock_qty,
            "unit": unit,
            "needed": round(needed, 4),
            "deficit": round(deficit, 4),
            "action": action,
        })

    # Urutkan: beli dulu, lalu waspada, lalu cukup (defisit terbesar duluan)
    order_rank = {"beli": 0, "waspada": 1, "cukup": 2}
    items.sort(key=lambda it: (order_rank[it["action"]], -it["deficit"]))

    return {
        "date": str(today),
        "predicted_production": pred_qty,
        "items": items,
    }


@router.get("/", response_model=list[StockResponse])
def list_stocks(db: Session = Depends(get_db)):
    stocks = db.query(Stock).all()
    result = []
    for s in stocks:
        if s.quantity < s.min_critical:
            status = "kritis"
        elif s.quantity < s.min_warning:
            status = "waspada"
        else:
            status = "aman"
        result.append(StockResponse(
            id=s.id,
            ingredient_name=s.ingredient_name,
            quantity=s.quantity,
            unit=s.unit,
            price_per_unit=s.price_per_unit,
            min_warning=s.min_warning,
            min_critical=s.min_critical,
            status=status,
            updated_at=s.updated_at
        ))
    return result


@router.post("/", response_model=StockResponse)
def create_stock(data: StockBase, db: Session = Depends(get_db)):
    ingredient_name = data.ingredient_name.strip()
    if not ingredient_name:
        raise HTTPException(422, "Nama bahan wajib diisi")

    # Cek duplikat case-insensitive (hindari 'Kedelai' vs 'kedelai' dobel)
    exists = db.query(Stock).filter(
        func.lower(Stock.ingredient_name) == ingredient_name.lower()
    ).first()
    if exists:
        raise HTTPException(409, f"Stok '{ingredient_name}' sudah ada")

    payload = data.model_dump()
    payload["ingredient_name"] = ingredient_name
    stock = Stock(**payload)
    db.add(stock)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"Stok '{ingredient_name}' sudah ada")
    db.refresh(stock)
    status = "aman"
    if stock.quantity < stock.min_critical:
        status = "kritis"
    elif stock.quantity < stock.min_warning:
        status = "waspada"
    return StockResponse(id=stock.id, **payload, status=status)


@router.patch("/{stock_id}/adjust")
def adjust_stock(stock_id: int, delta: float, db: Session = Depends(get_db)):
    # Tolak NaN/Inf — kalau dibiarkan, stok jadi 0/NULL (data korup permanen)
    if not math.isfinite(delta):
        raise HTTPException(422, "delta harus angka terbatas (bukan NaN/Infinity)")
    stock = db.query(Stock).filter(Stock.id == stock_id).first()
    if not stock:
        raise HTTPException(404, "Stok tidak ditemukan")
    stock.quantity = max(0, stock.quantity + delta)
    db.commit()
    db.refresh(stock)
    return {"message": f"Stok {stock.ingredient_name} = {stock.quantity} {stock.unit}"}


@router.put("/{stock_id}", response_model=StockResponse)
def update_stock(stock_id: int, data: StockBase, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.id == stock_id).first()
    if not stock:
        raise HTTPException(404, "Stok tidak ditemukan")

    ingredient_name = data.ingredient_name.strip()
    if not ingredient_name:
        raise HTTPException(422, "Nama bahan wajib diisi")

    # Cek duplikat case-insensitive, exclude id sendiri
    exists = db.query(Stock).filter(
        func.lower(Stock.ingredient_name) == ingredient_name.lower(),
        Stock.id != stock_id
    ).first()
    if exists:
        raise HTTPException(409, f"Stok '{ingredient_name}' sudah ada")

    payload = data.model_dump()
    payload["ingredient_name"] = ingredient_name
    for field, value in payload.items():
        setattr(stock, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"Stok '{ingredient_name}' sudah ada")
    db.refresh(stock)

    # Hitung status seperti di list_stocks
    if stock.quantity < stock.min_critical:
        status = "kritis"
    elif stock.quantity < stock.min_warning:
        status = "waspada"
    else:
        status = "aman"

    return StockResponse(
        id=stock.id,
        ingredient_name=stock.ingredient_name,
        quantity=stock.quantity,
        unit=stock.unit,
        price_per_unit=stock.price_per_unit,
        min_warning=stock.min_warning,
        min_critical=stock.min_critical,
        status=status,
        updated_at=stock.updated_at
    )


@router.delete("/{stock_id}")
def delete_stock(stock_id: int, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.id == stock_id).first()
    if not stock:
        raise HTTPException(404, "Stok tidak ditemukan")
    name = stock.ingredient_name
    db.delete(stock)
    db.commit()
    return {"message": f"Stok '{name}' dihapus"}
