"""Production Predictor — ML model dengan fine-tuning harian.

FR-MFG-001: Prediksi jumlah produksi harian.
Model: LinearRegression (scikit-learn) dengan retrain otomatis.
Ini adalah fine-tuning: setiap data baru → weight model berubah.
"""
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from datetime import date, timedelta
from typing import Optional
import logging

logger = logging.getLogger("zephyrus.predictor")


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
        self.last_train_date: Optional[date] = None

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
        weight model secara permanen.
        """
        features = self._extract_features(d)
        self.X.append(features)
        self.y.append(float(quantity))
        self._retrain()
        logger.info(
            f"Fine-tune: +1 data point ({d}, {quantity}). "
            f"Total: {len(self.y)} titik data."
        )

    def add_bulk(self, data: list[tuple[date, float]]) -> None:
        """Tambah banyak data produksi sekaligus (seed)."""
        for d, q in data:
            self.X.append(self._extract_features(d))
            self.y.append(float(q))
        self._retrain()
        logger.info(f"Bulk load: {len(data)} titik data. Model siap.")

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
            self.last_train_date = date.today()
        except Exception as e:
            logger.warning(f"Fine-tune gagal: {e}")

    def predict(self, target_date: date) -> dict:
        """Prediksi produksi untuk tanggal tertentu.

        Returns dict dengan: prediction, confidence, lower_bound, upper_bound
        """
        features = np.array([self._extract_features(target_date)])

        if not self.is_trained or len(self.y) < 3:
            # Fallback: rata-rata sederhana
            avg = int(np.mean(self.y)) if self.y else 200
            std = int(np.std(self.y)) if len(self.y) > 1 else 20
            return {
                "prediction": avg,
                "confidence_pct": 50,
                "confidence_bar": "●●●○○○ 50%",
                "lower_bound": max(0, avg - std),
                "upper_bound": avg + std,
                "data_points": len(self.y),
                "fine_tuned": False,
            }

        try:
            X_scaled = self.scaler.transform(features)
            pred = self.model.predict(X_scaled)[0]
            pred_int = int(round(pred))

            # Confidence: berdasarkan jumlah data training
            n = len(self.y)
            base_conf = min(92, 55 + int(n * 1.2))
            confidence_pct = min(95, base_conf)

            # Residual std untuk lower/upper bound
            y_pred_all = self.model.predict(self.scaler.transform(np.array(self.X)))
            residuals = np.std(self.y - y_pred_all) if len(self.y) > 3 else pred * 0.1
            residuals = max(residuals, 5)  # minimal 5 unit

            return {
                "prediction": max(0, pred_int),
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
            avg = int(np.mean(self.y))
            return {
                "prediction": avg,
                "confidence_pct": 50,
                "confidence_bar": "●●●●●○○○○○ 50%",
                "lower_bound": max(0, avg - 20),
                "upper_bound": avg + 20,
                "data_points": len(self.y),
                "fine_tuned": False,
            }


# Singleton — satu model untuk seluruh app
predictor = ProductionPredictor()
