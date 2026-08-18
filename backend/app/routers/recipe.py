"""Recipe Router — CRUD Resep Produk (FR-MFG-004).

Input: resep (bahan + takaran per unit) → dipakai rekomendasi harga & kebutuhan bahan.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Recipe, Product, Stock

router = APIRouter(prefix="/api/recipes", tags=["Recipe"])


class RecipeIn(BaseModel):
    product_id: int
    ingredient_name: str
    quantity_per_unit: float
    unit: str = "kg"


class RecipeOut(RecipeIn):
    id: int
    class Config:
        from_attributes = True


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
        needed = round(r.quantity_per_unit * quantity, 4)
        # Cari stok — fallback case-insensitive biar "kedelai" vs "Kedelai" tetap ketemu
        stock = db.query(Stock).filter(Stock.ingredient_name == r.ingredient_name).first()
        if not stock:
            stock = db.query(Stock).filter(
                func.lower(Stock.ingredient_name) == r.ingredient_name.lower()
            ).first()
        stock_qty = stock.quantity if stock else 0.0
        deficit = round(max(0, needed - stock_qty), 4)
        enough = deficit <= 0
        unit = stock.unit if stock else r.unit
        items.append({
            "ingredient_name": r.ingredient_name,
            "unit": unit,
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
    if data.quantity_per_unit <= 0:
        raise HTTPException(422, "quantity_per_unit harus > 0")

    # Cegah duplikat bahan — biaya produksi bisa dobel kalau dibiarkan
    exists = db.query(Recipe).filter(
        Recipe.product_id == data.product_id,
        Recipe.ingredient_name == data.ingredient_name,
    ).first()
    if exists:
        raise HTTPException(409, f"Bahan '{data.ingredient_name}' sudah ada di resep produk ini")

    recipe = Recipe(**data.model_dump())
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.patch("/{recipe_id}", response_model=RecipeOut)
def update_recipe(recipe_id: int, data: RecipeIn, db: Session = Depends(get_db)):
    """Ubah resep (bahan/takaran)."""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(404, f"Resep {recipe_id} tidak ditemukan")
    if data.quantity_per_unit <= 0:
        raise HTTPException(422, "quantity_per_unit harus > 0")

    # Validasi product (hindari IntegrityError 500 dari FK palsu)
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(404, f"Produk {data.product_id} tidak ditemukan")

    # Cegah duplikat bahan (termasuk kalau rename ke bahan yang sudah ada)
    exists = db.query(Recipe).filter(
        Recipe.product_id == data.product_id,
        Recipe.ingredient_name == data.ingredient_name,
        Recipe.id != recipe_id,
    ).first()
    if exists:
        raise HTTPException(409, f"Bahan '{data.ingredient_name}' sudah ada di resep produk ini")

    recipe.product_id = data.product_id
    recipe.ingredient_name = data.ingredient_name
    recipe.quantity_per_unit = data.quantity_per_unit
    recipe.unit = data.unit
    db.commit()
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
