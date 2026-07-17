"""Stock management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Stock
from app.schemas import StockBase, StockResponse

router = APIRouter(prefix="/api/stocks", tags=["Stock"])


@router.get("/", response_model=list[StockResponse])
def list_stocks(db: Session = Depends(get_db)):
    stocks = db.query(Stock).all()
    result = []
    for s in stocks:
        if s.quantity < s.min_critical:
            status = "kritis"
        elif s.quantity < s.min_warning:
            status = "waspada"
        else:
            status = "aman"
        result.append(StockResponse(
            id=s.id,
            ingredient_name=s.ingredient_name,
            quantity=s.quantity,
            unit=s.unit,
            min_warning=s.min_warning,
            min_critical=s.min_critical,
            status=status,
            updated_at=s.updated_at
        ))
    return result


@router.post("/", response_model=StockResponse)
def create_stock(data: StockBase, db: Session = Depends(get_db)):
    stock = Stock(**data.model_dump())
    db.add(stock)
    db.commit()
    db.refresh(stock)
    status = "aman"
    if stock.quantity < stock.min_critical:
        status = "kritis"
    elif stock.quantity < stock.min_warning:
        status = "waspada"
    return StockResponse(id=stock.id, **data.model_dump(), status=status)


@router.patch("/{stock_id}/adjust")
def adjust_stock(stock_id: int, delta: float, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.id == stock_id).first()
    if not stock:
        raise HTTPException(404, "Stok tidak ditemukan")
    stock.quantity = max(0, stock.quantity + delta)
    db.commit()
    db.refresh(stock)
    return {"message": f"Stok {stock.ingredient_name} = {stock.quantity} {stock.unit}"}
