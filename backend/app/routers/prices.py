"""Price Router — Peringatan Harga Bahan Baku (FR-MFG-003)."""
from fastapi import APIRouter

from app.services.prices import fetch_prices, get_price_alerts, search_price

router = APIRouter(prefix="/api/prices", tags=["Prices"])


@router.get("/")
def list_prices():
    """Daftar harga komoditas saat ini (Bapanas / fallback)."""
    prices = fetch_prices()
    return [
        {"key": k, **v}
        for k, v in prices.items()
    ]


@router.get("/alerts")
def price_alerts():
    """Peringatan harga untuk dashboard."""
    return get_price_alerts()


@router.get("/search")
def price_search(q: str):
    """Cari harga komoditas (dipakai chat AI)."""
    result = search_price(q)
    if result is None:
        return {"found": False, "message": "Komoditas tidak ditemukan"}
    return {"found": True, **result}
