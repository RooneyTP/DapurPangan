"""Pydantic schemas for Zephyrus API."""
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


# --- Product ---
class ProductBase(BaseModel):
    name: str
    category: str = "fermentasi"
    shelf_life_days: int = 2
    unit: str = "bungkus"
    default_production: int = 210

class ProductResponse(ProductBase):
    id: int
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# --- Recipe ---
class RecipeResponse(BaseModel):
    id: int
    product_id: int
    ingredient_name: str
    quantity_per_unit: float
    unit: str
    class Config:
        from_attributes = True


# --- Stock ---
class StockBase(BaseModel):
    ingredient_name: str
    quantity: float
    unit: str = "kg"
    min_warning: float = 5.0
    min_critical: float = 1.0

class StockResponse(StockBase):
    id: int
    status: str = "aman"
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# --- Production ---
class ProductionCreate(BaseModel):
    product_id: int
    date: date
    quantity: int
    notes: Optional[str] = None

class ProductionResponse(ProductionCreate):
    id: int
    class Config:
        from_attributes = True


# --- Customer ---
class CustomerBase(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class CustomerResponse(CustomerBase):
    id: int
    class Config:
        from_attributes = True


# --- Order ---
class OrderCreate(BaseModel):
    customer_id: int
    product_id: int
    date: date
    quantity: int
    status: str = "pending"

class OrderResponse(OrderCreate):
    id: int
    customer_name: Optional[str] = None
    product_name: Optional[str] = None
    class Config:
        from_attributes = True


# --- Dashboard ---
class DashboardResponse(BaseModel):
    greeting: str
    date: str
    recommendation: dict
    stock_alerts: list
    customer_insights: list
    price_alerts: list


# --- Chat ---
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str


# --- Route ---
class RouteStop(BaseModel):
    order: int
    customer_id: int
    customer_name: str
    address: Optional[str] = None
    quantity: int
    product_name: str = "Tempe"
    estimated_minutes: int
    shelf_life_flag: str = "✅ aman"  # ✅ aman / ⚠️ risiko basi

class RouteResponse(BaseModel):
    date: str
    total_stops: int
    total_estimated_minutes: int
    total_distance_km: float
    stops: list[RouteStop]
