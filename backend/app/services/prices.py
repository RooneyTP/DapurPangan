"""Price Service — Peringatan Harga Bahan Baku (FR-MFG-003).

Integrasi data harga komoditas pangan.
Sumber utama: PHIPS Bapanas (panelharga.badanpangan.go.id).
Fallback: data harga statis internal jika API eksternal gagal.

Struktur data konsisten — frontend tidak perlu tahu sumbernya.
"""
import json
import logging
import urllib.request
from datetime import date, timedelta

logger = logging.getLogger("daparpangan.prices")

# ---------------------------------------------------------------------------
# FALLBACK DATA — harga acuan nasional (Rp/kg) saat API luar tidak tersedia
# ---------------------------------------------------------------------------
FALLBACK_PRICES = {
    "kedelai":   {"name": "Kedelai",   "price": 11500, "unit": "kg", "date": "2026-07-16"},
    "cabai_rawit": {"name": "Cabai Rawit", "price": 38500, "unit": "kg", "date": "2026-07-16"},
    "cabai_merah": {"name": "Cabai Merah", "price": 42000, "unit": "kg", "date": "2026-07-16"},
    "bawang_merah": {"name": "Bawang Merah", "price": 35000, "unit": "kg", "date": "2026-07-16"},
    "tepung_terigu": {"name": "Tepung Terigu", "price": 12500, "unit": "kg", "date": "2026-07-16"},
    "telur_ayam": {"name": "Telur Ayam", "price": 28000, "unit": "kg", "date": "2026-07-16"},
    "gula":     {"name": "Gula Pasir", "price": 17500, "unit": "kg", "date": "2026-07-16"},
    "minyak_goreng": {"name": "Minyak Goreng", "price": 15000, "unit": "liter", "date": "2026-07-16"},
}

# ---------------------------------------------------------------------------
# KONFIGURASI KOMODITAS YANG DIPANTAU (sesuai kebutuhan IRTP)
# ---------------------------------------------------------------------------
MONITORED = {
    "kedelai": {"name": "Kedelai", "alias": ["kedelai", "tahu", "tempe"], "threshold_pct": 10.0},
    "cabai_rawit": {"name": "Cabai Rawit", "alias": ["cabai rawit", "cabe"], "threshold_pct": 10.0},
    "cabai_merah": {"name": "Cabai Merah", "alias": ["cabai merah", "cabe merah"], "threshold_pct": 10.0},
    "bawang_merah": {"name": "Bawang Merah", "alias": ["bawang"], "threshold_pct": 10.0},
    "tepung_terigu": {"name": "Tepung Terigu", "alias": ["tepung"], "threshold_pct": 10.0},
    "telur_ayam": {"name": "Telur Ayam", "alias": ["telur"], "threshold_pct": 10.0},
    "gula": {"name": "Gula Pasir", "alias": ["gula"], "threshold_pct": 10.0},
    "minyak_goreng": {"name": "Minyak Goreng", "alias": ["minyak"], "threshold_pct": 10.0},
}

# ---------------------------------------------------------------------------
# HARGA SEBELUMNYA (untuk kalkulasi tren) — basis fallback
# ---------------------------------------------------------------------------
PREV_PRICES = {
    "kedelai": 10200, "cabai_rawit": 42000, "cabai_merah": 45000,
    "bawang_merah": 33000, "tepung_terigu": 12000, "telur_ayam": 26000,
    "gula": 17000, "minyak_goreng": 14800,
}

BAPANAS_API = "https://panelharga.badanpangan.go.id/harga-pangan/"


def fetch_prices() -> dict:
    """Coba ambil harga real dari Bapanas. Gagal → fallback internal.

    Returns dict: {key: {"name", "price", "unit", "date"}}
    """
    try:
        req = urllib.request.Request(
            BAPANAS_API,
            headers={"User-Agent": "Mozilla/5.0 (DapurPangan/0.2)"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")

        # Upaya parse JSON (Bapanas punya beberapa varian endpoint)
        try:
            data = json.loads(raw)
            return _parse_bapanas(data)
        except json.JSONDecodeError:
            logger.info("Bapanas: respons bukan JSON murni — pakai fallback")
            return dict(FALLBACK_PRICES)

    except Exception as e:
        logger.warning(f"Bapanas tidak tersedia ({e}) — pakai fallback")
        return dict(FALLBACK_PRICES)


def _parse_bapanas(data) -> dict:
    """Parse struktur data Bapanas (beragam bentuk) ke format standar kita."""
    result = dict(FALLBACK_PRICES)
    try:
        # Bentuk umum: list of {kode, nama, harga, ...} atau dict {komoditas: {...}}
        items = data if isinstance(data, list) else data.get("data", [])
        if isinstance(items, dict):
            items = list(items.values())
        for item in items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("nama", item.get("name", ""))).lower()
            price = item.get("harga", item.get("price"))
            if not price:
                continue
            for key, cfg in MONITORED.items():
                if any(a in name for a in cfg["alias"]):
                    result[key] = {
                        "name": cfg["name"],
                        "price": float(price),
                        "unit": "kg",
                        "date": str(date.today()),
                    }
                    break
    except Exception as e:
        logger.warning(f"Parse Bapanas gagal ({e}) — pakai fallback")
    return result


def get_price_alerts() -> list[dict]:
    """Peringatan harga untuk dashboard.

    Komoditas yang naik/turun > threshold dibanding harga sebelumnya
    → direkomendasikan tindakan beli/sekarang/tunda.
    """
    prices = fetch_prices()
    alerts = []
    today = date.today()

    for key, price_info in prices.items():
        cfg = MONITORED.get(key)
        if not cfg:
            continue
        current = price_info["price"]
        prev = PREV_PRICES.get(key, current)
        change_pct = ((current - prev) / prev * 100) if prev else 0

        if abs(change_pct) >= cfg["threshold_pct"]:
            direction = "naik" if change_pct > 0 else "turun"
            action = (
                "beli stok SEKARANG sebelum naik lagi"
                if change_pct > 0
                else "waktu yang baik untuk beli — harga murah"
            )
            alerts.append({
                "commodity": cfg["name"],
                "change": f"{direction} {abs(change_pct):.0f}%",
                "detail": (
                    f"{price_info['name']} {direction} {abs(change_pct):.0f}% "
                    f"(Rp {prev:,.0f} → Rp {current:,.0f}/{price_info['unit']}). "
                    f"Rekomendasi: {action}."
                ),
                "price": current,
                "previous_price": prev,
                "date": price_info["date"],
            })
        elif key == "kedelai":  # selalu tampilkan kedelai (bahan utama Bu Sumi)
            alerts.append({
                "commodity": cfg["name"],
                "change": "stabil",
                "detail": (
                    f"Kedelai stabil di Rp {current:,.0f}/{price_info['unit']}. "
                    f"Tidak perlu aksi."
                ),
                "price": current,
                "previous_price": prev,
                "date": price_info["date"],
            })

    return alerts[:3]  # maksimal 3 alert biar dashboard tidak penuh


def search_price(query: str) -> dict | None:
    """Cari harga komoditas berdasarkan kata kunci (untuk chat)."""
    q = query.lower()
    prices = fetch_prices()
    for key, cfg in MONITORED.items():
        if any(a in q for a in cfg["alias"]):
            info = prices.get(key)
            if info:
                return {
                    "name": cfg["name"],
                    "price": info["price"],
                    "unit": info["unit"],
                    "date": info["date"],
                }
    return None
