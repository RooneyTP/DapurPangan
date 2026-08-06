"""Pricing Service — Rekomendasi Harga Jual (FR-COM-002).

Hitung biaya produksi dari resep + harga bahan baku,
lalu rekomendasi harga jual minimal & optimal.
"""
from sqlalchemy.orm import Session

from app.models import Product, Recipe, Stock


def compute_production_cost(db: Session, product: Product) -> tuple[float, list[dict]]:
    """Hitung biaya produksi per unit produk berdasarkan resep & harga stok.

    Returns:
        (total_cost_per_unit, breakdown)
    """
    recipes = db.query(Recipe).filter(Recipe.product_id == product.id).all()
    breakdown = []
    total_cost = 0.0

    for r in recipes:
        stock = db.query(Stock).filter(
            Stock.ingredient_name == r.ingredient_name
        ).first()

        if stock and stock.price_per_unit:
            cost = r.quantity_per_unit * stock.price_per_unit
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

    # Harga optimal: margin lebih tinggi (+10pp), tapi tidak overprice pasar
    optimal_margin = margin_pct + 10
    price_opt_raw = round(cost * (1 + optimal_margin / 100))
    price_opt = min(price_opt_raw, market_high)

    # Saran naratif
    margin_opt_actual = ((price_opt - cost) / cost * 100) if cost > 0 else 0
    note = (
        f"Biaya produksi per {product.unit}: Rp {cost:,.0f}. "
        f"Harga jual minimal Rp {price_min:,.0f} (margin {margin_pct:.0f}%). "
        f"Harga optimal Rp {price_opt:,.0f} (margin {margin_opt_actual:.0f}% — "
        f"kompetitif di pasar Rp {market_low:,.0f}-Rp {market_high:,.0f})."
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
