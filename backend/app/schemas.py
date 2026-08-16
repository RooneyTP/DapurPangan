"""Pydantic schemas for DapurPangan API."""
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional


# --- Stock ---
class StockBase(BaseModel):
    ingredient_name: str
    quantity: float = Field(ge=0, description="Tidak boleh negatif")
    unit: str = "kg"
    price_per_unit: Optional[float] = None
    min_warning: float = 5.0
    min_critical: float = 1.0

class StockResponse(StockBase):
    id: int
    status: str = "aman"
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# --- Pricing (FR-COM-002) ---
class PriceBreakdown(BaseModel):
    ingredient: str
    quantity_per_unit: float
    unit: str
    price_per_unit: float
    cost_per_unit: float

class PriceRecommendation(BaseModel):
    product_id: int
    product_name: str
    production_cost: float          # biaya produksi per unit (Rp)
    breakdown: list[PriceBreakdown]
    margin_pct: float               # margin target user
    price_minimum: float            # harga minimal (margin target)
    price_optimal: float            # harga optimal (margin + 10%)
    market_price_low: float
    market_price_high: float
    note: str


# --- Customer ---
class CustomerBase(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None

class CustomerResponse(CustomerBase):
    id: int
    class Config:
        from_attributes = True


# --- Order ---
class OrderCreate(BaseModel):
    customer_id: int
    product_id: int
    date: date
    quantity: int = Field(ge=1, description="Minimal 1")
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
