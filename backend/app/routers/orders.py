"""Orders & Customer endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order, Customer, Product
from app.schemas import OrderCreate, OrderResponse, CustomerBase, CustomerResponse
from app.services.predictor import predictor

router = APIRouter(prefix="/api", tags=["Orders"])


# --- Proyeksi pesanan ---
@router.get("/orders/projection")
def order_projection(db: Session = Depends(get_db)):
    """Proyeksi pesanan per pelanggan.

    Share tiap pelanggan dihitung dari proporsi total kuantitas 14 hari
    terakhir, lalu dikalikan prediksi produksi hari ini. Tren dihitung
    dari 7 hari terakhir vs 7 hari sebelumnya; alert muncul kalau tren
    turun ≥ 20% (pola sama seperti insight di production.py).
    """
    today = date.today()
    since14 = today - timedelta(days=14)
    since7 = today - timedelta(days=7)

    orders = db.query(Order).filter(Order.date > since14).all()
    pred = predictor.predict(today)
    pred_qty = pred["prediction"]

    if not orders:
        return {"predicted_total": pred_qty, "items": []}

    # Agregasi per pelanggan: qty 14 hari, 7 hari terakhir, 7 hari sebelumnya
    agg: dict[int, dict] = {}
    for o in orders:
        a = agg.setdefault(o.customer_id, {"qty14": 0, "recent": 0, "prev": 0})
        a["qty14"] += o.quantity
        if o.date > since7:
            a["recent"] += o.quantity
        else:
            a["prev"] += o.quantity

    total_qty_14 = sum(a["qty14"] for a in agg.values())
    customers = {c.id: c.name for c in db.query(Customer).all()}

    items = []
    for cid, a in agg.items():
        share = (a["qty14"] / total_qty_14) if total_qty_14 > 0 else 0.0
        projected_qty = round(pred_qty * share)

        recent, prev = a["recent"], a["prev"]
        if prev == 0 and recent == 0:
            trend, trend_pct = "stabil", 0
        elif prev == 0:
            trend, trend_pct = "naik", 100
        elif recent == prev:
            trend, trend_pct = "stabil", 0
        else:
            trend = "naik" if recent > prev else "turun"
            trend_pct = int(round(abs(recent - prev) / prev * 100))

        items.append({
            "customer_name": customers.get(cid, "Unknown"),
            "share_pct": round(share * 100, 1),
            "projected_qty": projected_qty,
            "trend": trend,
            "trend_pct": trend_pct,
            "alert": trend == "turun" and trend_pct >= 20,
        })

    items.sort(key=lambda it: it["projected_qty"], reverse=True)
    return {"predicted_total": pred_qty, "items": items}


# --- Customers ---
@router.get("/customers", response_model=list[CustomerResponse])
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).all()


@router.post("/customers", response_model=CustomerResponse)
def create_customer(data: CustomerBase, db: Session = Depends(get_db)):
    name = data.name.strip()
    if not name:
        raise HTTPException(422, "Nama pelanggan wajib diisi")
    payload = data.model_dump()
    payload["name"] = name
    c = Customer(**payload)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.put("/customers/{customer_id}", response_model=CustomerResponse)
def update_customer(customer_id: int, data: CustomerBase, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Pelanggan tidak ditemukan")
    name = data.name.strip()
    if not name:
        raise HTTPException(422, "Nama pelanggan wajib diisi")
    payload = data.model_dump()
    payload["name"] = name
    for field, value in payload.items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/customers/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(404, "Pelanggan tidak ditemukan")
    # Cek dulu pesanan terkait — jangan hapus kalau masih punya order
    order_count = db.query(Order).filter(Order.customer_id == customer_id).count()
    if order_count > 0:
        raise HTTPException(409, f"Pelanggan '{customer.name}' masih memiliki {order_count} pesanan. Hapus pesanannya dulu atau edit data pelanggan.")
    name = customer.name
    db.delete(customer)
    db.commit()
    return {"message": f"Pelanggan '{name}' dihapus"}


# --- Orders ---
@router.get("/orders/", response_model=list[OrderResponse])
def list_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).order_by(Order.date.desc()).limit(50).all()
    result = []
    for o in orders:
        customer = db.query(Customer).filter(Customer.id == o.customer_id).first()
        product = db.query(Product).filter(Product.id == o.product_id).first()
        result.append(OrderResponse(
            id=o.id,
            customer_id=o.customer_id,
            product_id=o.product_id,
            date=o.date,
            quantity=o.quantity,
            status=o.status,
            customer_name=customer.name if customer else "Unknown",
            product_name=product.name if product else "Unknown"
        ))
    return result


@router.get("/orders/today", response_model=list[OrderResponse])
def today_orders(db: Session = Depends(get_db)):
    today = date.today()
    orders = db.query(Order).filter(Order.date == today).all()
    result = []
    for o in orders:
        customer = db.query(Customer).filter(Customer.id == o.customer_id).first()
        product = db.query(Product).filter(Product.id == o.product_id).first()
        result.append(OrderResponse(
            id=o.id,
            customer_id=o.customer_id,
            product_id=o.product_id,
            date=o.date,
            quantity=o.quantity,
            status=o.status,
            customer_name=customer.name if customer else "Unknown",
            product_name=product.name if product else "Unknown"
        ))
    return result


@router.post("/orders/", response_model=OrderResponse)
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    # Validasi FK — customer & product harus ada (hindari orphan data)
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(404, f"Pelanggan {data.customer_id} tidak ditemukan")
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(404, f"Produk {data.product_id} tidak ditemukan")

    order = Order(**data.model_dump())
    db.add(order)
    db.commit()
    db.refresh(order)
    return OrderResponse(
        id=order.id,
        customer_id=order.customer_id,
        product_id=order.product_id,
        date=order.date,
        quantity=order.quantity,
        status=order.status,
        customer_name=customer.name if customer else "Unknown",
        product_name=product.name if product else "Unknown"
    )


@router.put("/orders/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, data: OrderCreate, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Pesanan tidak ditemukan")

    # Validasi FK — customer & product harus ada (sama seperti POST /orders/)
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(404, f"Pelanggan {data.customer_id} tidak ditemukan")
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(404, f"Produk {data.product_id} tidak ditemukan")

    for field, value in data.model_dump().items():
        setattr(order, field, value)
    db.commit()
    db.refresh(order)
    return OrderResponse(
        id=order.id,
        customer_id=order.customer_id,
        product_id=order.product_id,
        date=order.date,
        quantity=order.quantity,
        status=order.status,
        customer_name=customer.name if customer else "Unknown",
        product_name=product.name if product else "Unknown"
    )


@router.delete("/orders/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "Pesanan tidak ditemukan")
    db.delete(order)
    db.commit()
    return {"message": f"Pesanan {order_id} dihapus"}
