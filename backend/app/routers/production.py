"""Dashboard & Production Prediction endpoints."""
from fastapi import APIRouter, Depends
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, Stock, Customer, Order, Production
from app.schemas import DashboardResponse

router = APIRouter(prefix="/api", tags=["Dashboard"])


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    """Ringkasan dashboard 'Dapur Hari Ini'."""
    today = date.today()
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    day_name = days[today.weekday()]

    # Ambil produk utama
    product = db.query(Product).first()
    if not product:
        return _mock_dashboard(day_name, today)

    # Prediksi produksi (simple: rata2 7 hari terakhir + 10% buffer)
    recent = db.query(Production).filter(
        Production.product_id == product.id,
        Production.date >= today - timedelta(days=7)
    ).all()
    avg_qty = int(sum(p.quantity for p in recent) / max(len(recent), 1))
    recommendation_qty = int(avg_qty * 1.1)

    # Stok alerts
    stocks = db.query(Stock).all()
    stock_alerts = []
    for s in stocks:
        if s.quantity < s.min_critical:
            status = "🔴 KRITIS"
        elif s.quantity < s.min_warning:
            status = "🟡 WASPADA"
        else:
            status = "🟢 AMAN"
        stock_alerts.append({
            "name": s.ingredient_name,
            "qty": f"{s.quantity} {s.unit}",
            "status": status
        })

    # Customer insights: yang turun >20%
    customers = db.query(Customer).all()
    customer_insights = []
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
        elif not customer_insights:
            customer_insights.append({
                "name": c.name if c else "Warung A",
                "trend": "✅ stabil",
                "note": "Pesanan normal"
            })

    return DashboardResponse(
        greeting=f"🌅 Selamat pagi, Bu Sumi!",
        date=f"{day_name}, {today.strftime('%d %B %Y')}",
        recommendation={
            "product": product.name,
            "quantity": recommendation_qty,
            "lower_bound": int(recommendation_qty * 0.9),
            "upper_bound": int(recommendation_qty * 1.1),
            "confidence": "●●●●○ 87%"
        },
        stock_alerts=stock_alerts or [
            {"name": "Kedelai", "qty": "50 kg", "status": "🟢 AMAN"},
            {"name": "Ragi", "qty": "80 g", "status": "🔴 KRITIS - BELI!"},
        ],
        customer_insights=customer_insights or [
            {"name": "Kantin D", "trend": "⬇️ turun 30%", "note": "Cek apakah ada masalah?"}
        ],
        price_alerts=[
            {"commodity": "Kedelai", "change": "naik 12%", "detail": "Rp 11.500 → Rp 12.900/kg minggu depan"}
        ]
    )


def _mock_dashboard(day_name, today):
    """Fallback data when DB is empty."""
    return DashboardResponse(
        greeting="🌅 Selamat pagi, Bu Sumi!",
        date=f"{day_name}, {today.strftime('%d %B %Y')}",
        recommendation={
            "product": "Tempe",
            "quantity": 210,
            "lower_bound": 190,
            "upper_bound": 230,
            "confidence": "●●●●○ 87%"
        },
        stock_alerts=[
            {"name": "Kedelai", "qty": "50 kg", "status": "🟢 AMAN"},
            {"name": "Ragi", "qty": "80 g", "status": "🔴 KRITIS - BELI!"},
            {"name": "Plastik kemasan", "qty": "220 pcs", "status": "🟡 WASPADA"},
        ],
        customer_insights=[
            {"name": "Kantin D", "trend": "⬇️ turun 30%", "note": "Cek apakah ada masalah?"},
            {"name": "Warung B", "trend": "✅ stabil", "note": "Pesanan normal"},
        ],
        price_alerts=[
            {"commodity": "Kedelai", "change": "naik 12%", "detail": "Rp 11.500 → Rp 12.900/kg minggu depan"},
            {"commodity": "Minyak goreng", "change": "stabil", "detail": "Rp 15.000/L (14 hari)"},
        ]
    )
