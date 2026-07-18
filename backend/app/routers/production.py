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

    # Prediksi produksi — Prophet (ML dengan fine-tuning harian)
    records_raw = db.query(Production).filter(
        Production.product_id == product.id,
        Production.date >= today - timedelta(days=60)  # data 60 hari
    ).order_by(Production.date).all()

    records = [
        {"date": str(r.date), "quantity": r.quantity, "product_id": r.product_id}
        for r in records_raw
    ]

    from app.services.predictor import train_and_predict
    pred_result = train_and_predict(
        product_id=product.id,
        production_records=records,
        forecast_days=1,
    )

    if pred_result["predictions"]:
        p = pred_result["predictions"][0]
        recommendation_qty = p["predicted"]
        lower_bound = p["lower_bound"]
        upper_bound = p["upper_bound"]
        confidence = pred_result["confidence"]
    else:
        recommendation_qty = product.default_production
        lower_bound = int(recommendation_qty * 0.9)
        upper_bound = int(recommendation_qty * 1.1)
        confidence = "●●●○○ 65%"

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
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "confidence": confidence
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
