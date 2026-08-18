"""DapurPangan API — Main application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal
from app.models import Product, Stock, Customer, Recipe, Order, Production, Sale
from datetime import date, timedelta
import os

app = FastAPI(
    title="DapurPangan API",
    description="Pusat Komando Digital untuk IRTP",
    version="0.1.0",
    docs_url="/docs",
)

# CORS — allow frontend from anywhere (PWA). Tanpa auth/cookie, jadi
# allow_credentials=False (wildcard + credentials melanggar spec CORS)
import json as _json
try:
    origins = _json.loads(os.getenv("CORS_ORIGINS", '["*"]'))
except (ValueError, TypeError):
    origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Import routers ---
from app.routers import production
from app.routers import stock
from app.routers import orders
from app.routers import chat
from app.routers import pricing
from app.routers import prices
from app.routers import recipe
from app.routers import importer
from app.routers import sales
from app.services.predictor import predictor as prod_predictor
from app.services.predictor import sales_predictor
app.include_router(production.router)
app.include_router(stock.router)
app.include_router(orders.router)
app.include_router(chat.router)
app.include_router(pricing.router)
app.include_router(prices.router)
app.include_router(recipe.router)
app.include_router(importer.router)
app.include_router(sales.router)


@app.on_event("startup")
def startup():
    """Create tables + seed data on first run."""
    Base.metadata.create_all(bind=engine)
    _seed_if_empty()
    # SELALU seed predictor dari DB (fine-tune ulang tiap restart) —
    # jangan hanya saat DB kosong, karena restart server harus tetap punya model
    _seed_predictor()
    _seed_sales_if_empty()
    _seed_sales_predictor()


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

    # 3. Stocks (dengan harga per unit)
    db.add(Stock(ingredient_name="Kedelai", quantity=50.0, unit="kg",
                 price_per_unit=11500, min_warning=15.0, min_critical=5.0))
    db.add(Stock(ingredient_name="Ragi", quantity=0.080, unit="kg",
                 price_per_unit=62500, min_warning=0.2, min_critical=0.1))
    db.add(Stock(ingredient_name="Plastik kemasan", quantity=220, unit="pcs",
                 price_per_unit=150, min_warning=50, min_critical=20))

    # 4. Customers
    wa = Customer(name="Warung A", address="Jl. Mawar No. 12", phone="0812-xxxx-xxxx")
    wb = Customer(name="Warung B", address="Jl. Melati No. 45", phone="0813-xxxx-xxxx")
    pc = Customer(name="Pasar C", address="Pasar Induk Lamongan", phone="-")
    kd = Customer(name="Kantin D", address="SMK N 1 Lamongan", phone="0814-xxxx-xxxx")
    db.add_all([wa, wb, pc, kd])
    db.flush()

    # 5. Orders (14 hari terakhir — 7 hari lalu untuk baseline trend)
    today = date.today()
    # Baseline: 7 hari sebelumnya (hari -14 s/d -8)
    for i in range(7, 14):
        d = today - timedelta(days=i)
        db.add(Order(customer_id=wa.id, product_id=tempe.id, date=d, quantity=30, status="delivered"))
        db.add(Order(customer_id=wb.id, product_id=tempe.id, date=d, quantity=50, status="delivered"))
        db.add(Order(customer_id=pc.id, product_id=tempe.id, date=d, quantity=100, status="delivered"))
        db.add(Order(customer_id=kd.id, product_id=tempe.id, date=d, quantity=35, status="delivered"))  # dulu 35/hr

    # 7 hari terakhir — Kantin D turun 30→20
    for i in range(7):
        d = today - timedelta(days=6 - i)
        db.add(Order(customer_id=wa.id, product_id=tempe.id, date=d, quantity=30, status="delivered"))
        db.add(Order(customer_id=wb.id, product_id=tempe.id, date=d, quantity=50, status="delivered"))
        db.add(Order(customer_id=pc.id, product_id=tempe.id, date=d, quantity=100 + i * 5, status="delivered"))
        qty_kd = max(20, 30 - i * 2)  # turun gradually 30→20
        db.add(Order(customer_id=kd.id, product_id=tempe.id, date=d, quantity=qty_kd, status="delivered"))

    # 6. Production history (14 hari — untuk training ML lebih baik)
    for i in range(7, 14):
        d = today - timedelta(days=i)
        db.add(Production(product_id=tempe.id, date=d, quantity=200))
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
        # Reset dulu supaya restart server tidak double-count data lama
        prod_predictor.reset()
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


def _seed_sales_if_empty():
    """Seed data penjualan B2C 14 hari terakhir kalau tabel sales masih kosong.

    Tiap hari 1 record: produk pertama yang ada di DB, jumlah individu
    bervariasi (80 + i*4 + (i%3)*2) supaya ada pola naik untuk training ML,
    quantity_per_individual = 1. Kalau belum ada produk → tidak seed apa-apa.
    """
    db = SessionLocal()
    try:
        if db.query(Sale).count() > 0:
            return
        product = db.query(Product).first()
        if not product:
            return

        today = date.today()
        for i in range(14):  # hari ini mundur 13 hari → 14 hari data
            d = today - timedelta(days=13 - i)
            individuals = 80 + i * 4 + (i % 3) * 2
            db.add(Sale(
                product_id=product.id,
                date=d,
                individual_count=individuals,
                quantity_per_individual=1,
            ))
        db.commit()
        print("🛒 Sales B2C: seeded 14 hari data penjualan per individu")
    finally:
        db.close()


def _seed_sales_predictor(db: SessionLocal = None):
    """Seed sales_predictor dengan total unit per hari dari tabel Sale.

    Dipanggil tiap startup (bukan hanya saat DB kosong) supaya restart
    server tetap punya model yang fine-tuned dari data aktual.
    """
    from app.database import SessionLocal as DB
    s = db or DB()
    try:
        history = s.query(Sale).order_by(Sale.date).all()
        # Agregasi total unit per hari
        per_day: dict = {}
        for sale in history:
            per_day[sale.date] = per_day.get(sale.date, 0) + \
                sale.individual_count * sale.quantity_per_individual

        sales_predictor.reset()
        for d, total in sorted(per_day.items()):
            sales_predictor.add_data_point(d, total)
        n = len(per_day)
        if n > 0:
            test = sales_predictor.predict(date.today())
            print(f"🛒 Sales Predictor: fine-tuned with {n} data points | "
                  f"Prediksi unit besok: {test['prediction']} "
                  f"(confidence {test['confidence_pct']}%)")
        else:
            print("🛒 Sales Predictor: no historical sales data yet")
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
