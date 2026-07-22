"""SQLAlchemy models for DapurPangan."""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import date, datetime
import enum

from app.database import Base


class ProductCategory(str, enum.Enum):
    FERMENTASI = "fermentasi"
    SAMBAL = "sambal"
    KUE_BASAH = "kue_basah"
    KUE_KERING = "kue_kering"
    KERUPUK = "kerupuk"
    ROTI = "roti"
    MINUMAN = "minuman"
    LAUK = "lauk"


class StockStatus(str, enum.Enum):
    AMAN = "aman"
    WASPADA = "waspada"
    KRITIS = "kritis"


# --- Product (Resep & Produk) ---
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), default="fermentasi")
    shelf_life_days = Column(Integer, default=2)
    unit = Column(String(20), default="bungkus")
    default_production = Column(Integer, default=210)
    created_at = Column(DateTime, default=datetime.utcnow)

    recipes = relationship("Recipe", back_populates="product", cascade="all, delete-orphan")
    productions = relationship("Production", back_populates="product")


# --- Recipe (Resep Bahan Baku per Produk) ---
class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    ingredient_name = Column(String(100), nullable=False)
    quantity_per_unit = Column(Float, nullable=False)  # misal: 0.1 kg kedelai per tempe
    unit = Column(String(20), default="kg")

    product = relationship("Product", back_populates="recipes")


# --- Stock (Stok Bahan Baku) ---
class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_name = Column(String(100), nullable=False, unique=True)
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), default="kg")
    min_warning = Column(Float, default=5.0)  # threshold waspada
    min_critical = Column(Float, default=1.0)  # threshold kritis
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# --- Production (Catatan Produksi Harian) ---
class Production(Base):
    __tablename__ = "productions"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    quantity = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)

    product = relationship("Product", back_populates="productions")


# --- Customer (Pelanggan) ---
class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200), nullable=True)
    phone = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    orders = relationship("Order", back_populates="customer")


# --- Order (Pesanan Pelanggan) ---
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    quantity = Column(Integer, nullable=False)
    status = Column(String(20), default="pending")  # pending, delivered, cancelled

    customer = relationship("Customer", back_populates="orders")
    product = relationship("Product")
