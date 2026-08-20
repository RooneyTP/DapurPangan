"""Pydantic schemas for DapurPangan API."""
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Literal, Optional


# --- Stock ---
class StockBase(BaseModel):
    ingredient_name: str = Field(max_length=100)
    quantity: float = Field(ge=0, allow_inf_nan=False, description="Tidak boleh negatif")
    unit: str = Field("kg", max_length=20)
    price_per_unit: Optional[float] = Field(None, ge=0, allow_inf_nan=False)
    min_warning: float = Field(5.0, ge=0, allow_inf_nan=False)
    min_critical: float = Field(1.0, ge=0, allow_inf_nan=False)


class StockUpdate(BaseModel):
    """PUT /api/stocks/{id}: field opsional None = pertahankan nilai lama."""
    ingredient_name: str = Field(max_length=100)
    quantity: float = Field(ge=0, allow_inf_nan=False)
    unit: Optional[str] = Field(None, max_length=20)
    price_per_unit: Optional[float] = Field(None, ge=0, allow_inf_nan=False)
    min_warning: Optional[float] = Field(None, ge=0, allow_inf_nan=False)
    min_critical: Optional[float] = Field(None, ge=0, allow_inf_nan=False)


class StockResponse(StockBase):
    id: int
    status: str = Field("aman", max_length=20)
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# --- Pricing (FR-COM-002) ---
class PriceBreakdown(BaseModel):
    ingredient: str = Field(max_length=100)
    quantity_per_unit: float = Field(gt=0, allow_inf_nan=False)
    unit: str = Field(max_length=20)
    price_per_unit: float
    cost_per_unit: float

class PriceRecommendation(BaseModel):
    product_id: int
    product_name: str = Field(max_length=100)
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
    name: str = Field(max_length=100)
    address: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
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
    quantity: int = Field(ge=1, le=1_000_000, description="Minimal 1")
    status: Literal["pending", "delivered", "cancelled"] = "pending"

class OrderResponse(OrderCreate):
    id: int
    customer_name: Optional[str] = Field(None, max_length=100)
    product_name: Optional[str] = Field(None, max_length=100)
    class Config:
        from_attributes = True


# --- Sale (Penjualan per Individu / B2C) ---
class SaleCreate(BaseModel):
    product_id: int
    date: date
    individual_count: int = Field(ge=1, le=100_000, description="Minimal 1 orang")
    quantity_per_individual: int = Field(ge=1, le=100, description="Minimal 1 per orang")

class SaleResponse(SaleCreate):
    id: int
    product_name: Optional[str] = Field(None, max_length=100)
    total_quantity: int = 0
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
    message: str = Field(max_length=500)

class ChatResponse(BaseModel):
    reply: str

class ChatHistoryItem(BaseModel):
    role: str = Field(max_length=10)
    content: str
