"""Recipe Router — CRUD Resep Produk (FR-MFG-004).

Input: resep (bahan + takaran per unit) → dipakai rekomendasi harga & kebutuhan bahan.
"""
import math

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Recipe, Product, Stock

router = APIRouter(prefix="/api/recipes", tags=["Recipe"])


class RecipeIn(BaseModel):
    product_id: int
    ingredient_name: str
    quantity_per_unit: float = Field(gt=0, allow_inf_nan=False)
    unit: str = "kg"


class RecipeOut(RecipeIn):
    id: int
    class Config:
        from_attributes = True


# --- Normalisasi satuan (kanonik: gram untuk massa, liter untuk volume) ---
_MASS_UNITS = {"kg", "kilogram", "g", "gr", "gram"}
_VOLUME_UNITS = {"l", "liter", "ml", "milliliter", "mililiter"}


def _to_grams(value: float, unit: str) -> float:
    """Konversi satuan massa ke gram. Unit tidak dikenal -> nilai apa adanya (jangan crash)."""
    u = (unit or "").strip().lower()
    if u in ("kg", "kilogram"):
        return value * 1000.0
    if u in ("g", "gr", "gram"):
        return value
    return value


def _to_liters(value: float, unit: str) -> float:
    """Konversi satuan volume ke liter. Unit tidak dikenal -> nilai apa adanya (jangan crash)."""
    u = (unit or "").strip().lower()
    if u in ("l", "liter"):
        return value
    if u in ("ml", "milliliter", "mililiter"):
        return value / 1000.0
    return value


def _canonical_quantity(value: float, unit: str) -> float:
    """Normalisasi ke satuan kanonik: gram (massa), liter (volume), pcs passthrough.

    Unit tidak dikenal diasumsikan sama sehingga perbandingan tidak crash.
    """
    if value is None:
        return 0.0
    u = (unit or "").strip().lower()
    if u in _MASS_UNITS:
        return _to_grams(value, u)
    if u in _VOLUME_UNITS:
        return _to_liters(value, u)
    return value


@router.get("/", response_model=list[RecipeOut])
def list_recipes(db: Session = Depends(get_db)):
    """Daftar semua resep."""
    return db.query(Recipe).all()


@router.get("/check")
def check_recipe_stock(
    product_id: int,
    quantity: int = Query(1, ge=1, description="Jumlah produk yang mau dibuat"),
    db: Session = Depends(get_db),
):
    """Cek kecukupan stok bahan baku untuk membuat sejumlah produk.

    Kebutuhan tiap bahan = takaran resep (quantity_per_unit) x quantity,
    dibandingkan dengan stok yang ada. Hasilnya: flag sufficient global
    plus rincian per bahan (needed/stock/deficit/enough).
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, f"Produk {product_id} tidak ditemukan")

    recipes = db.query(Recipe).filter(Recipe.product_id == product_id).all()
    if not recipes:
        raise HTTPException(404, f"Produk '{product.name}' belum punya resep. Tambahkan resep dulu.")

    items = []
    for r in recipes:
        qpu = r.quantity_per_unit
        needed_raw = qpu * quantity if qpu is not None else None
        # Cari stok — fallback case-insensitive biar "kedelai" vs "Kedelai" tetap ketemu
        stock = db.query(Stock).filter(Stock.ingredient_name == r.ingredient_name).first()
        if not stock:
            stock = db.query(Stock).filter(
                func.lower(Stock.ingredient_name) == r.ingredient_name.lower()
            ).first()
        stock_qty = stock.quantity if stock and stock.quantity is not None else 0.0
        if needed_raw is None or not math.isfinite(needed_raw):
            # Data resep korup (null/NaN/inf) — lewati bahan, jangan 500
            items.append({
                "ingredient_name": r.ingredient_name,
                "unit": r.unit or "",
                "needed": None,
                "stock": stock_qty,
                "deficit": None,
                "enough": False,
                "note": "data resep tidak valid",
            })
            continue
        needed = round(needed_raw, 4)
        # Bandingkan di satuan kanonik (gram untuk massa, liter untuk volume, pcs passthrough)
        needed_canon = _canonical_quantity(needed, r.unit)
        stock_canon = _canonical_quantity(stock_qty, stock.unit if stock else r.unit)
        deficit = round(max(0, needed_canon - stock_canon), 4)
        enough = deficit <= 0
        items.append({
            "ingredient_name": r.ingredient_name,
            "unit": r.unit,
            "needed": needed,
            "stock": stock_qty,
            "deficit": deficit,
            "enough": enough,
        })

    # Urutkan: bahan yang tidak cukup tampil paling depan
    items.sort(key=lambda i: i["enough"])
    sufficient = all(i["enough"] for i in items)

    return {
        "product_id": product_id,
        "product_name": product.name,
        "quantity": quantity,
        "sufficient": sufficient,
        "items": items,
    }


@router.get("/product/{product_id}", response_model=list[RecipeOut])
def recipes_by_product(product_id: int, db: Session = Depends(get_db)):
    """Resep untuk satu produk (bahan-bahan yang dibutuhkan)."""
    recipes = db.query(Recipe).filter(Recipe.product_id == product_id).all()
    if not recipes:
        raise HTTPException(404, f"Produk {product_id} belum punya resep")
    return recipes


@router.post("/", response_model=RecipeOut)
def create_recipe(data: RecipeIn, db: Session = Depends(get_db)):
    """Tambah bahan ke resep produk."""
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(404, f"Produk {data.product_id} tidak ditemukan")
    qpu = data.quantity_per_unit
    if qpu is None or not math.isfinite(qpu) or qpu <= 0 or qpu > 1_000_000:
        raise HTTPException(422, "quantity_per_unit harus > 0, finite, dan <= 1e6")

    # Cegah duplikat bahan (case-insensitive) — biaya produksi bisa dobel kalau dibiarkan
    exists = db.query(Recipe).filter(
        Recipe.product_id == data.product_id,
        func.lower(Recipe.ingredient_name) == data.ingredient_name.lower(),
    ).first()
    if exists:
        raise HTTPException(409, f"Bahan '{data.ingredient_name}' sudah ada di resep produk ini")

    recipe = Recipe(**data.model_dump())
    db.add(recipe)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"Bahan '{data.ingredient_name}' sudah ada di resep produk ini")
    db.refresh(recipe)
    return recipe


@router.patch("/{recipe_id}", response_model=RecipeOut)
def update_recipe(recipe_id: int, data: RecipeIn, db: Session = Depends(get_db)):
    """Ubah resep (bahan/takaran)."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(404, f"Resep {recipe_id} tidak ditemukan")
    qpu = data.quantity_per_unit
    if qpu is None or not math.isfinite(qpu) or qpu <= 0 or qpu > 1_000_000:
        raise HTTPException(422, "quantity_per_unit harus > 0, finite, dan <= 1e6")

    # Validasi product (hindari IntegrityError 500 dari FK palsu)
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(404, f"Produk {data.product_id} tidak ditemukan")

    # Cegah duplikat bahan (case-insensitive, exclude id sendiri)
    exists = db.query(Recipe).filter(
        Recipe.product_id == data.product_id,
        func.lower(Recipe.ingredient_name) == data.ingredient_name.lower(),
        Recipe.id != recipe_id,
    ).first()
    if exists:
        raise HTTPException(409, f"Bahan '{data.ingredient_name}' sudah ada di resep produk ini")

    recipe.product_id = data.product_id
    recipe.ingredient_name = data.ingredient_name
    recipe.quantity_per_unit = data.quantity_per_unit
    recipe.unit = data.unit
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, f"Bahan '{data.ingredient_name}' sudah ada di resep produk ini")
    db.refresh(recipe)
    return recipe


@router.delete("/{recipe_id}")
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    """Hapus bahan dari resep."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(404, f"Resep {recipe_id} tidak ditemukan")
    db.delete(recipe)
    db.commit()
    return {"message": f"Resep '{recipe.ingredient_name}' dihapus"}
