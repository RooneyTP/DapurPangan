"""Pricing Router — Rekomendasi Harga Jual (FR-COM-002)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import PriceRecommendation
from app.services.pricing import recommend_price

router = APIRouter(prefix="/api/pricing", tags=["Pricing"])


@router.get("/recommendation", response_model=PriceRecommendation)
def get_price_recommendation(
    product_id: int = Query(1, description="ID produk"),
    margin_pct: float = Query(20.0, ge=0, le=100, description="Margin target (%)"),
    market_low: float = Query(4500.0, description="Harga pasar terendah"),
    market_high: float = Query(5500.0, description="Harga pasar tertinggi"),
    db: Session = Depends(get_db),
):
    """Rekomendasi harga jual: minimal + optimal berdasarkan biaya produksi.

    FR-COM-002: Berdasarkan harga bahan baku terkini + margin yang diinginkan.
    """
    try:
        result = recommend_price(
            db=db,
            product_id=product_id,
            margin_pct=margin_pct,
            market_low=market_low,
            market_high=market_high,
        )
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
