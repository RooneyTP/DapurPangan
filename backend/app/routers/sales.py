"""Sales (Penjualan per Individu / B2C) endpoints.

Mencatat penjualan langsung ke konsumen perorangan: berapa individu
pembeli (individual_count) dan berapa unit yang dibeli tiap orang
(quantity_per_individual). Total unit per hari dihitung, tidak disimpan
— yaitu individual_count * quantity_per_individual.
"""
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Sale, Product
from app.schemas import SaleCreate, SaleResponse
from app.services.predictor import sales_predictor

router = APIRouter(prefix="/api/sales", tags=["Sales"])


def _to_response(sale: Sale, product_name: str = None) -> SaleResponse:
    """Bangun SaleResponse dengan product_name + total_quantity dari record Sale."""
    if product_name is None:
        product = sale.product or None
        product_name = product.name if product else "Unknown"
    return SaleResponse(
        id=sale.id,
        product_id=sale.product_id,
        date=sale.date,
        individual_count=sale.individual_count,
        quantity_per_individual=sale.quantity_per_individual,
        product_name=product_name,
        total_quantity=sale.individual_count * sale.quantity_per_individual,
    )


@router.get("/prediction")
def sales_prediction(db: Session = Depends(get_db)):
    """Prediksi penjualan BESOK: perkiraan unit terjual & jumlah pembeli.

    Unit diprediksi dengan model ML (sales_predictor) yang di-fine-tune
    dari total unit per hari; jumlah pembeli memakai rata-rata harian
    individu (pendekatan sederhana). Kalau belum ada data Sale sama
    sekali → kembalikan nol tanpa error.
    """
    tomorrow = date.today() + timedelta(days=1)
    sales = db.query(Sale).all()
    if not sales:
        return {
            "date": str(tomorrow),
            "predicted_units": 0,
            "predicted_individuals": 0,
            "data_points": 0,
            "confidence_pct": 0,
            "fine_tuned": False,
        }

    # Agregasi per hari: total unit & total individu
    per_day: dict[date, list[int]] = {}
    for s in sales:
        per_day.setdefault(s.date, []).append(s.individual_count * s.quantity_per_individual)

    daily_units = []
    daily_individuals = []
    for d, units in sorted(per_day.items()):
        daily_units.append((d, sum(units)))
        daily_individuals.append(sum(
            s.individual_count for s in sales if s.date == d
        ))

    # Fine-tune predictor sales dari data riil
    sales_predictor.reset()
    for d, total in daily_units:
        sales_predictor.add_data_point(d, total)

    p = sales_predictor.predict(tomorrow)
    avg_individuals = int(round(sum(daily_individuals) / len(daily_individuals)))

    return {
        "date": str(tomorrow),
        "predicted_units": p["prediction"],
        "predicted_individuals": avg_individuals,
        "data_points": p["data_points"],
        "confidence_pct": p["confidence_pct"],
        "fine_tuned": p["fine_tuned"],
    }


@router.get("/", response_model=list[SaleResponse])
def list_sales(db: Session = Depends(get_db)):
    """Daftar penjualan B2C terbaru (maks 50, tanggal terbaru dulu)."""
    sales = db.query(Sale).order_by(Sale.date.desc(), Sale.id.desc()).limit(50).all()
    result = []
    for s in sales:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        result.append(_to_response(s, product.name if product else "Unknown"))
    return result


@router.get("/today", response_model=list[SaleResponse])
def today_sales(db: Session = Depends(get_db)):
    """Penjualan B2C yang tercatat hari ini."""
    sales = db.query(Sale).filter(Sale.date == date.today()).all()
    result = []
    for s in sales:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        result.append(_to_response(s, product.name if product else "Unknown"))
    return result


@router.post("/", response_model=SaleResponse)
def create_sale(data: SaleCreate, db: Session = Depends(get_db)):
    """Catat penjualan B2C baru (validasi produk harus ada)."""
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(404, f"Produk {data.product_id} tidak ditemukan")

    sale = Sale(**data.model_dump())
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return _to_response(sale, product.name)


@router.put("/{sale_id}", response_model=SaleResponse)
def update_sale(sale_id: int, data: SaleCreate, db: Session = Depends(get_db)):
    """Ubah data penjualan B2C (semua field diupdate)."""
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(404, "Penjualan tidak ditemukan")
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(404, f"Produk {data.product_id} tidak ditemukan")

    for field, value in data.model_dump().items():
        setattr(sale, field, value)
    db.commit()
    db.refresh(sale)
    return _to_response(sale, product.name)


@router.delete("/{sale_id}")
def delete_sale(sale_id: int, db: Session = Depends(get_db)):
    """Hapus record penjualan B2C."""
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(404, "Penjualan tidak ditemukan")
    db.delete(sale)
    db.commit()
    return {"message": f"Penjualan {sale_id} dihapus"}
