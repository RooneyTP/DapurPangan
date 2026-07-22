"""DapurPangan API — Main application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal
from app.models import Product, Stock, Customer, Recipe, Order, Production
from datetime import date, timedelta
import os

app = FastAPI(
    title="DapurPangan API",
    description="Pusat Komando Digital untuk IRTP",
    version="0.1.0",
    docs_url="/docs",
)

# CORS — allow frontend from anywhere (PWA)
origins = eval(os.getenv("CORS_ORIGINS", '["*"]'))
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Import routers ---
from app.routers import production
from app.routers import stock
from app.routers import orders
from app.routers import chat
from app.services.predictor import predictor as prod_predictor
app.include_router(production.router)
app.include_router(stock.router)
app.include_router(orders.router)
app.include_router(chat.router)


@app.on_event("startup")
def startup():
    """Create tables + seed data on first run."""
    Base.metadata.create_all(bind=engine)
    _seed_if_empty()


def _seed_if_empty():
    db = SessionLocal()
    if db.query(Product).count() > 0:
        db.close()
        return

    # 1. Product
    tempe = Product(name="Tempe", category="fermentasi", shelf_life_days=2, unit="bungkus", default_production=210)
    db.add(tempe)
    db.flush()

    # 2. Recipes
    db.add(Recipe(product_id=tempe.id, ingredient_name="Kedelai", quantity_per_unit=0.1, unit="kg"))
    db.add(Recipe(product_id=tempe.id, ingredient_name="Ragi", quantity_per_unit=0.0005, unit="kg"))

    # 3. Stocks
    db.add(Stock(ingredient_name="Kedelai", quantity=50.0, unit="kg", min_warning=15.0, min_critical=5.0))
    db.add(Stock(ingredient_name="Ragi", quantity=0.080, unit="kg", min_warning=0.2, min_critical=0.1))
    db.add(Stock(ingredient_name="Plastik kemasan", quantity=220, unit="pcs", min_warning=50, min_critical=20))

    # 4. Customers
    wa = Customer(name="Warung A", address="Jl. Mawar No. 12", phone="0812-xxxx-xxxx")
    wb = Customer(name="Warung B", address="Jl. Melati No. 45", phone="0813-xxxx-xxxx")
    pc = Customer(name="Pasar C", address="Pasar Induk Lamongan", phone="-")
    kd = Customer(name="Kantin D", address="SMK N 1 Lamongan", phone="0814-xxxx-xxxx")
    db.add_all([wa, wb, pc, kd])
    db.flush()

    # 5. Orders (7 hari terakhir)
    today = date.today()
    for i in range(7):
        d = today - timedelta(days=6 - i)
        db.add(Order(customer_id=wa.id, product_id=tempe.id, date=d, quantity=30, status="delivered"))
        db.add(Order(customer_id=wb.id, product_id=tempe.id, date=d, quantity=50, status="delivered"))
        db.add(Order(customer_id=pc.id, product_id=tempe.id, date=d, quantity=100 + i * 5, status="delivered"))
        qty_kd = max(15, 30 - i * 2)  # turun gradually
        db.add(Order(customer_id=kd.id, product_id=tempe.id, date=d, quantity=qty_kd, status="delivered"))

    # 6. Production history
    for i in range(7):
        d = today - timedelta(days=6 - i)
        db.add(Production(product_id=tempe.id, date=d, quantity=200 + i * 5))

    db.commit()
    db.close()

    # Seed predictor dengan data historis (fine-tuning awal)
    _seed_predictor()


def _seed_predictor(db: SessionLocal = None):
    """Seed predictor dengan data produksi historis untuk fine-tuning awal."""
    from app.database import SessionLocal as DB
    s = db or DB()
    try:
        history = s.query(Production).order_by(Production.date).all()
        for p in history:
            prod_predictor.add_data_point(p.date, p.quantity)
        n = len(history)
        if n > 0:
            # Test prediksi
            test = prod_predictor.predict(date.today())
            print(f"📊 Predictor: fine-tuned with {n} data points | "
                  f"Prediksi besok: {test['prediction']} "
                  f"(confidence {test['confidence_pct']}%)")
        else:
            print("📊 Predictor: no historical data yet")
    finally:
        if not db:
            s.close()


@app.get("/")
def root():
    return {
        "app": "DapurPangan",
        "version": "0.1.0",
        "docs": "/docs",
        "dashboard": "/api/dashboard"
    }


@app.get("/health")
def health():
    return {"status": "ok"}
