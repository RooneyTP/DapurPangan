"""Dashboard & Production Prediction endpoints.

FR-MFG-001: Prediksi produksi pakai ML model dengan fine-tuning harian.
"""
from fastapi import APIRouter, Depends
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, Stock, Customer, Order, Production
from app.schemas import DashboardResponse
from app.services.predictor import predictor

router = APIRouter(prefix="/api", tags=["Dashboard"])


def _fmt_qty(quantity: float, unit: str) -> str:
    """Format kuantitas dengan baik: 50 kg, 80 g, 220 pcs (bukan 0.08 kg)."""
    if unit == "kg" and quantity < 1:
        return f"{round(quantity * 1000)} g"
    if float(quantity).is_integer():
        return f"{int(quantity)} {unit}"
    return f"{quantity:.2f} {unit}"


@router.get("/products")
def list_products(db: Session = Depends(get_db)):
    """Daftar produk (untuk form pesanan & resep)."""
    products = db.query(Product).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "unit": p.unit,
            "shelf_life_days": p.shelf_life_days,
        }
        for p in products
    ]


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    """Ringkasan dashboard 'Dapur Hari Ini' — pakai ML prediction."""
    today = date.today()
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    day_name = days[today.weekday()]

    # Ambil produk utama
    product = db.query(Product).first()

    # Prediksi produksi pake ML (fine-tuned model)
    pred = predictor.predict(today)

    # Stok alerts
    stocks = db.query(Stock).all()
    stock_alerts = []
    for s in stocks:
        if s.quantity < s.min_critical:
            status = "🔴 KRITIS - BELI!"
        elif s.quantity < s.min_warning:
            status = "🟡 WASPADA"
        else:
            status = "🟢 AMAN"
        stock_alerts.append({
            "name": s.ingredient_name,
            "qty": _fmt_qty(s.quantity, s.unit),
            "status": status
        })

    # Customer insights — berdasarkan total kuantitas, bukan jumlah record
    customer_insights = []
    customers = db.query(Customer).all()
    for c in customers:
        recent_orders = db.query(Order).filter(
            Order.customer_id == c.id,
            Order.date > today - timedelta(days=7)
        ).all()
        recent_qty = sum(o.quantity for o in recent_orders)

        prev_orders = db.query(Order).filter(
            Order.customer_id == c.id,
            Order.date <= today - timedelta(days=7),
            Order.date > today - timedelta(days=14)
        ).all()
        prev_qty = sum(o.quantity for o in prev_orders)

        if prev_qty > 0 and recent_qty < prev_qty * 0.8:
            customer_insights.append({
                "name": c.name,
                "trend": f"⬇️ turun {int((1 - recent_qty/prev_qty)*100)}%",
                "note": "Cek apakah ada masalah?"
            })

    # Hanya tampilkan insight yang benar-benar dari data — tanpa hardcode

    # Price alerts — dari service harga (Bapanas + fallback)
    from app.services.prices import get_price_alerts
    price_alerts = get_price_alerts()

    return DashboardResponse(
        greeting=f"🌅 Selamat pagi, Bu Sumi!",
        date=f"{day_name}, {today.strftime('%d %B %Y')}",
        recommendation={
            "product": product.name if product else "Tempe",
            "quantity": pred["prediction"],
            "lower_bound": pred["lower_bound"],
            "upper_bound": pred["upper_bound"],
            "confidence": pred["confidence_bar"],
            "fine_tuned": pred.get("fine_tuned", False),
            "data_points": pred.get("data_points", 0),
        },
        stock_alerts=stock_alerts if stock_alerts else [
            {"name": "Belum ada stok tercatat", "qty": "-", "status": "⚪ KOSONG"}
        ],
        customer_insights=customer_insights,
        price_alerts=price_alerts,
    )
