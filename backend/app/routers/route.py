"""Route Optimizer Endpoint — FR-LOG-001 Priority."""
from fastapi import APIRouter, Depends
from datetime import date
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, Order, Product
from app.schemas import RouteResponse, RouteStop
from app.services.route_optimizer import optimize_route

router = APIRouter(prefix="/api/routes", tags=["Route"])


@router.get("/today", response_model=RouteResponse)
def get_today_route(db: Session = Depends(get_db)):
    """Generate rute distribusi optimal untuk hari ini.

    Menggunakan Nearest Neighbor TSP + prioritasi shelf-life.
    Sesuai FR-LOG-001 dari PRD.
    """
    today = date.today()

    # Ambil semua pelanggan aktif
    customers = db.query(Customer).all()
    if not customers:
        return RouteResponse(
            date=str(today), total_stops=0, total_estimated_minutes=0,
            total_distance_km=0.0, stops=[]
        )

    # Ambil produk default (Tempe) untuk shelf-life
    product = db.query(Product).first()
    shelf_life_days = product.shelf_life_days if product else 2

    # Build daftar pelanggan dengan pesanan hari ini & koordinat
    customer_list = []
    for c in customers:
        # Cari pesanan hari ini
        order_qty = 0
        order = db.query(Order).filter(
            Order.customer_id == c.id,
            Order.date == today
        ).first()
        if order:
            order_qty = order.quantity
        else:
            # Fallback: cari rata-rata 7 hari terakhir
            from datetime import timedelta
            recent_orders = db.query(Order).filter(
                Order.customer_id == c.id,
                Order.date >= today - timedelta(days=7)
            ).all()
            if recent_orders:
                order_qty = int(sum(o.quantity for o in recent_orders) / len(recent_orders))
            else:
                continue  # skip customer without orders

        customer_list.append({
            "id": c.id,
            "name": c.name,
            "address": c.address or "",
            "latitude": c.latitude,
            "longitude": c.longitude,
            "quantity": order_qty,
            "product_name": product.name if product else "Tempe",
        })

    if not customer_list:
        return RouteResponse(
            date=str(today), total_stops=0, total_estimated_minutes=0,
            total_distance_km=0.0, stops=[]
        )

    # Optimasi rute
    result = optimize_route(
        customers=customer_list,
        shelf_life_hours=shelf_life_days * 24
    )

    stops = [
        RouteStop(**s) for s in result["stops"]
    ]

    return RouteResponse(
        date=str(today),
        total_stops=len(stops),
        total_estimated_minutes=result["total_minutes"],
        total_distance_km=result["total_distance_km"],
        stops=stops
    )
