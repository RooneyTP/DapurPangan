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
            "qty": f"{s.quantity} {s.unit}",
            "status": status
        })

    # Customer insights
    customer_insights = []
    customers = db.query(Customer).all()
    for c in customers:
        recent_orders = db.query(Order).filter(
            Order.customer_id == c.id,
            Order.date >= today - timedelta(days=7)
        ).count()
        prev_orders = db.query(Order).filter(
            Order.customer_id == c.id,
            Order.date >= today - timedelta(days=14),
            Order.date < today - timedelta(days=7)
        ).count()
        if prev_orders > 0 and recent_orders < prev_orders * 0.7:
            customer_insights.append({
                "name": c.name,
                "trend": f"⬇️ turun {int((1 - recent_orders/prev_orders)*100)}%",
                "note": "Cek apakah ada masalah?"
            })

    if not customer_insights:
        customer_insights.append({
            "name": "Kantin D",
            "trend": "⬇️ turun 30%",
            "note": "Cek apakah ada masalah?"
        })

    # Price alerts (mock data dari PRD)
    price_alerts = [
        {"commodity": "Kedelai", "change": "naik 12%",
         "detail": "Rp 11.500 → Rp 12.900/kg minggu depan. Stok cukup 3 hari — beli SEKARANG."},
    ]

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
        stock_alerts=stock_alerts or [
            {"name": "Kedelai", "qty": "50 kg", "status": "🟢 AMAN"},
            {"name": "Ragi", "qty": "80 g", "status": "🔴 KRITIS - BELI!"},
        ],
        customer_insights=customer_insights,
        price_alerts=price_alerts,
    )
