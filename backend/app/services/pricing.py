"""Pricing Service — Rekomendasi Harga Jual (FR-COM-002).

Hitung biaya produksi dari resep + harga bahan baku,
lalu rekomendasi harga jual minimal & optimal.
"""
import math
import logging
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Product, Recipe, Stock

logger = logging.getLogger("daparpangan.pricing")


# --- Normalisasi satuan (kanonik: gram untuk massa, liter untuk volume) ---
# Sama seperti logika di backend/app/routers/recipe.py supaya konsisten.
_MASS_UNITS = {"kg", "kilogram", "g", "gr", "gram"}
_VOLUME_UNITS = {"l", "liter", "ml", "milliliter", "mililiter"}


def _to_grams(value: float, unit: str) -> float:
    """Konversi satuan massa ke gram. Unit tak dikenal -> nilai apa adanya (jangan crash)."""
    u = (unit or "").strip().lower()
    if u in ("kg", "kilogram"):
        return value * 1000.0
    if u in ("g", "gr", "gram"):
        return value
    return value


def _to_liters(value: float, unit: str) -> float:
    """Konversi satuan volume ke liter. Unit tak dikenal -> nilai apa adanya (jangan crash)."""
    u = (unit or "").strip().lower()
    if u in ("l", "liter"):
        return value
    if u in ("ml", "milliliter", "mililiter"):
        return value / 1000.0
    return value


def _convert_to_stock_unit(quantity: float, recipe_unit: str, stock_unit: str) -> float:
    """Konversi kuantitas resep ke satuan stok sebelum perkalian harga.

    Massa (kg/kilogram/g/gr/gram) <-> massa, volume (l/liter/ml/milliliter/
    mililiter) <-> volume, termasuk bentuk panjang 'gram'/'kilogram'/'ml'.
    pcs/lembar/bungkus & unit tak dikenal -> passthrough (jangan crash).
    """
    ru = (recipe_unit or '').strip().lower()
    su = (stock_unit or '').strip().lower()
    if ru == su:
        return quantity
    if ru in _MASS_UNITS and su in _MASS_UNITS:
        return _to_grams(quantity, ru) / _to_grams(1.0, su)
    if ru in _VOLUME_UNITS and su in _VOLUME_UNITS:
        return _to_liters(quantity, ru) / _to_liters(1.0, su)
    # pcs / lembar / bungkus dan kombinasi lain: passthrough
    return quantity


def compute_production_cost(db: Session, product: Product) -> tuple[float, list[dict]]:
    """Hitung biaya produksi per unit produk berdasarkan resep & harga stok.

    Returns:
        (total_cost_per_unit, breakdown)
    """
    recipes = db.query(Recipe).filter(Recipe.product_id == product.id).all()
    breakdown = []
    total_cost = 0.0

    for r in recipes:
        # Lookup stok case-insensitive (resep 'kedelai' ↔ stok 'Kedelai')
        stock = db.query(Stock).filter(
            func.lower(Stock.ingredient_name) == func.lower(r.ingredient_name)
        ).first()

        # Bedakan None (belum ada harga) vs 0 (harga diisi nol — peringatkan)
        if stock is not None and stock.price_per_unit is not None:
            qty_converted = _convert_to_stock_unit(r.quantity_per_unit, r.unit, stock.unit)
            price = stock.price_per_unit
            if price == 0:
                logger.warning(
                    f"Harga stok '{r.ingredient_name}' = 0 (mungkin belum diisi) — "
                    f"biaya dihitung 0."
                )
            cost = qty_converted * price
            if not math.isfinite(cost):
                logger.warning(f"Biaya non-finite untuk '{r.ingredient_name}' — dihitung 0.")
                cost = 0.0
            total_cost += cost
            breakdown.append({
                "ingredient": r.ingredient_name,
                "quantity_per_unit": r.quantity_per_unit,
                "unit": r.unit,
                "price_per_unit": stock.price_per_unit,
                "cost_per_unit": round(cost, 2),
            })
        else:
            # Bahan tanpa harga — estimasi 0, tandai
            breakdown.append({
                "ingredient": r.ingredient_name,
                "quantity_per_unit": r.quantity_per_unit,
                "unit": r.unit,
                "price_per_unit": 0.0,
                "cost_per_unit": 0.0,
            })

    if not math.isfinite(total_cost):
        logger.warning("Total biaya non-finite — dikembalikan 0.")
        total_cost = 0.0
    return round(total_cost, 2), breakdown


def recommend_price(
    db: Session,
    product_id: int,
    margin_pct: float = 20.0,
    market_low: float = 4500.0,
    market_high: float = 5500.0,
) -> dict:
    """Rekomendasi harga jual minimal & optimal.

    - price_minimum = biaya produksi * (1 + margin/100)
    - price_optimal = harga minimal dengan margin optimal (margin + 10%)
    - Dipatok tidak melebihi harga pasar atas (market_high).
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ValueError(f"Produk {product_id} tidak ditemukan")

    cost, breakdown = compute_production_cost(db, product)

    # Harga minimal: cukup margin target
    price_min = round(cost * (1 + margin_pct / 100))

    # Harga optimal: kompetitif DI DALAM rentang pasar.
    # - Kalau pasar mendukung harga lebih tinggi dari margin minimal → pakai harga pasar
    #   (margin lebih besar, tetap kompetitif)
    # - Kalau biaya produksi sudah di atas pasar → patok di batas pasar atas
    # - Tidak pernah di bawah market_low (buang margin) dan tidak pernah di atas market_high (tidak kompetitif)
    price_opt = min(max(price_min, market_low), market_high)

    # Saran naratif
    margin_opt_actual = ((price_opt - cost) / cost * 100) if cost > 0 else 0
    # Penjelasan: kalau harga optimal = market_low (bukan cost-based), beri tahu user
    if price_opt >= market_low and price_min < market_low:
        note = (
            f"Biaya produksi per {product.unit}: Rp {cost:,.0f}. "
            f"Margin target {margin_pct:.0f}% → harga minimal Rp {price_min:,.0f}. "
            f"Tapi pasar mendukung harga Rp {market_low:,.0f}-Rp {market_high:,.0f}, "
            f"jadi rekomendasi optimal: Rp {price_opt:,.0f} (masih di bawah harga pasar — "
            f"peluang margin aktual {margin_opt_actual:.0f}%)."
        )
    else:
        note = (
            f"Biaya produksi per {product.unit}: Rp {cost:,.0f}. "
            f"Harga jual minimal Rp {price_min:,.0f} (margin {margin_pct:.0f}%). "
            f"Harga optimal Rp {price_opt:,.0f} — kompetitif di pasar "
            f"Rp {market_low:,.0f}-Rp {market_high:,.0f}."
        )

    return {
        "product_id": product.id,
        "product_name": product.name,
        "production_cost": cost,
        "breakdown": breakdown,
        "margin_pct": margin_pct,
        "price_minimum": price_min,
        "price_optimal": price_opt,
        "market_price_low": market_low,
        "market_price_high": market_high,
        "note": note,
    }
