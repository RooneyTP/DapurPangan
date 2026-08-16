"""Recipe Router — CRUD Resep Produk (FR-MFG-004).

Input: resep (bahan + takaran per unit) → dipakai rekomendasi harga & kebutuhan bahan.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Recipe, Product

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
