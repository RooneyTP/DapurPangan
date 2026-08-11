"""Orders & Customer endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import date
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order, Customer, Product
from app.schemas import OrderCreate, OrderResponse, CustomerBase, CustomerResponse

router = APIRouter(prefix="/api", tags=["Orders"])


# --- Customers ---
@router.get("/customers", response_model=list[CustomerResponse])
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).all()


@router.post("/customers", response_model=CustomerResponse)
def create_customer(data: CustomerBase, db: Session = Depends(get_db)):
    c = Customer(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# --- Orders ---
@router.get("/orders", response_model=list[OrderResponse])
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


@router.post("/orders", response_model=OrderResponse)
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
