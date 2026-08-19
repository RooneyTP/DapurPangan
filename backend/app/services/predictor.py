"""Production Predictor — ML model dengan fine-tuning harian.

FR-MFG-001: Prediksi jumlah produksi harian.
Model: LinearRegression (scikit-learn) dengan retrain otomatis.
Ini adalah fine-tuning: setiap data baru → weight model berubah.
"""
import math
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from datetime import date
import logging

logger = logging.getLogger("daparpangan.predictor")


def _isfinite(x) -> bool:
    """True kalau x bisa jadi float yang finite (bukan nan/inf)."""
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


class ProductionPredictor:
    """Model prediksi produksi dengan fine-tuning otomatis.

    Cara kerja:
    1. Setiap ada data produksi baru → model di-retrain (fine-tune)
    2. Features: hari, tren, event (Lebaran)
    3. Output: prediksi + confidence + upper/lower bound
    """

    def __init__(self):
        self.model = LinearRegression()
        self.scaler = StandardScaler()
        self.is_trained = False
        self.X: list[list[float]] = []  # feature matrix
        self.y: list[float] = []         # target values

    def reset(self) -> None:
        """Kosongkan data training (dipakai saat re-seed dari DB)."""
        self.model = LinearRegression()
        self.scaler = StandardScaler()
        self.is_trained = False
        self.X = []
        self.y = []

    def _extract_features(self, d: date) -> list[float]:
        """Ekstrak fitur dari tanggal untuk prediksi."""
        return [
            float(d.weekday()),                        # 0=Senin .. 6=Minggu
            float(d.day),                               # tanggal (1-31)
            float(d.month),                             # bulan (1-12)
            float(1 if d.month == 12 and d.day >= 20 else 0),  # musim liburan
        ]

    def add_data_point(self, d: date, quantity: float) -> None:
        """Tambah data produksi baru → fine-tune model.

        Ini adalah fine-tuning: setiap titik data baru mengubah
        weight model secara permanen. Input non-finite (nan/inf)
        diabaikan supaya tidak meracuni model.
        """
        if not _isfinite(quantity):
            logger.warning(f"Data point diabaikan (quantity non-finite): ({d}, {quantity})")
            return
        features = self._extract_features(d)
        self.X.append(features)
        self.y.append(float(quantity))
        self._retrain()
        logger.info(
            f"Fine-tune: +1 data point ({d}, {quantity}). "
            f"Total: {len(self.y)} titik data."
        )

    def _retrain(self) -> None:
        """Fine-tune: retrain model dengan semua data yang ada."""
        n = len(self.X)
        if n < 3:
            return  # butuh minimal 3 titik data

        X_arr = np.array(self.X)
        y_arr = np.array(self.y)

        try:
            self.scaler.fit(X_arr)
            X_scaled = self.scaler.transform(X_arr)
            self.model.fit(X_scaled, y_arr)
            self.is_trained = True
        except Exception as e:
            logger.warning(f"Fine-tune gagal: {e}")

    def predict(self, target_date: date) -> dict:
        """Prediksi produksi untuk tanggal tertentu.

        Returns dict dengan: prediction, confidence, lower_bound, upper_bound.
        Kalau BELUM ADA data sama sekali → prediction None + confidence 0
        (indikator "belum cukup data", bukan angka fiktif).
        """
        # Tidak ada data → jujur bilang belum bisa prediksi (bukan 200/50% fiktif)
        if not self.y:
            return {
                "prediction": None,
                "confidence_pct": 0,
                "confidence_bar": "Belum cukup data",
                "lower_bound": None,
                "upper_bound": None,
                "data_points": 0,
                "fine_tuned": False,
            }

        features = np.array([self._extract_features(target_date)])

        if not self.is_trained or len(self.y) < 3:
            # Fallback: rata-rata sederhana dari data riil yang ada
            avg = float(np.mean(self.y))
            std = float(np.std(self.y)) if len(self.y) > 1 else 0.0
            avg_int = int(round(avg)) if _isfinite(avg) else 0
            std_int = int(round(std)) if _isfinite(std) else 0
            return {
                "prediction": avg_int,
                "confidence_pct": 50,
                "confidence_bar": "●●●○○○ 50%",
                "lower_bound": max(0, avg_int - std_int),
                "upper_bound": avg_int + std_int,
                "data_points": len(self.y),
                "fine_tuned": False,
            }

        try:
            X_scaled = self.scaler.transform(features)
            pred = float(self.model.predict(X_scaled)[0])
            if not _isfinite(pred):
                raise ValueError(f"Prediksi non-finite: {pred}")

            n = len(self.y)
            # Confidence: berdasarkan jumlah data training (satu clamp saja)
            confidence_pct = min(92, 55 + int(n * 1.2))

            # Residual std untuk lower/upper bound
            y_pred_all = self.model.predict(self.scaler.transform(np.array(self.X)))
            residuals = float(np.std(self.y - y_pred_all)) if len(self.y) > 3 else pred * 0.1
            if not _isfinite(residuals):
                residuals = 5.0
            residuals = max(residuals, 5)  # minimal 5 unit

            pred_int = max(0, int(round(pred)))
            return {
                "prediction": pred_int,
                "confidence_pct": confidence_pct,
                "confidence_bar": "●" * (confidence_pct // 10) + "○" * (10 - confidence_pct // 10) + f" {confidence_pct}%",
                "lower_bound": max(0, int(round(pred_int - residuals * 1.5))),
                "upper_bound": int(round(pred_int + residuals * 1.5)),
                "data_points": n,
                "fine_tuned": True,
                "model_type": "LinearRegression (fine-tuned daily)",
            }
        except Exception as e:
            logger.warning(f"Prediksi error: {e}")
            avg = float(np.mean(self.y))
            avg_int = int(round(avg)) if _isfinite(avg) else 0
            return {
                "prediction": avg_int,
                "confidence_pct": 50,
                "confidence_bar": "●●●●●○○○○○ 50%",
                "lower_bound": max(0, avg_int - 20),
                "upper_bound": avg_int + 20,
                "data_points": len(self.y),
                "fine_tuned": False,
            }


# Singleton — satu model untuk seluruh app
predictor = ProductionPredictor()

# Instance kedua — khusus prediksi penjualan B2C (Sale per individu).
# Dipisah dari `predictor` karena data latihnya berbeda (unit terjual harian),
# sehingga fine-tuning satu model tidak mencemari model yang lain.
sales_predictor = ProductionPredictor()
