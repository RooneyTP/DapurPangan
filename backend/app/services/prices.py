"""Price Service — Peringatan Harga Bahan Baku (FR-MFG-003).

Integrasi data harga komoditas pangan.
Sumber utama: PHIPS Bapanas (panelharga.badanpangan.go.id).
Fallback: data harga statis internal jika API eksternal gagal.

Struktur data konsisten — frontend tidak perlu tahu sumbernya.
"""
import copy
import json
import logging
import re
import urllib.request
from datetime import date

logger = logging.getLogger("daparpangan.prices")

# ---------------------------------------------------------------------------
# FALLBACK DATA — harga acuan nasional (Rp/kg) saat API luar tidak tersedia.
# Tanggal TIDAK disimpan di sini — selalu date.today() via _fallback_prices().
# ---------------------------------------------------------------------------
FALLBACK_PRICES = {
    "kedelai":   {"name": "Kedelai",   "price": 11500, "unit": "kg"},
    "cabai_rawit": {"name": "Cabai Rawit", "price": 38500, "unit": "kg"},
    "cabai_merah": {"name": "Cabai Merah", "price": 42000, "unit": "kg"},
    "bawang_merah": {"name": "Bawang Merah", "price": 35000, "unit": "kg"},
    "tepung_terigu": {"name": "Tepung Terigu", "price": 12500, "unit": "kg"},
    "telur_ayam": {"name": "Telur Ayam", "price": 28000, "unit": "kg"},
    "gula":     {"name": "Gula Pasir", "price": 17500, "unit": "kg"},
    "minyak_goreng": {"name": "Minyak Goreng", "price": 15000, "unit": "liter"},
}


def _fallback_prices() -> dict:
    """Deep-copy FALLBACK_PRICES per pemakaian + tanggal = hari ini."""
    data = copy.deepcopy(FALLBACK_PRICES)
    today = date.today().isoformat()
    for v in data.values():
        v["date"] = today
    return data


def _sanitize_number(raw) -> float:
    """Ubah string harga jadi float: '11.500'/'11,500' (ribuan) → 11500.0.

    Mendukung pemisah ribuan titik/koma, desimal '11,5' (Eropa) dan '11.5'.
    Raise ValueError kalau tidak bisa diparse.
    """
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip().replace('\u00a0', '').replace(' ', '')
    if not s:
        raise ValueError(f"harga kosong: {raw!r}")
    # Pola ribuan: 1.500 / 1,500 / 12.500.000 (dengan opsional desimal di akhir)
    m = re.fullmatch(r'(\d{1,3}(?:[.,]\d{3})+)(?:[.,](\d+))?', s)
    if m:
        int_part = m.group(1).replace('.', '').replace(',', '')
        frac = m.group(2) or ''
        s = int_part + (('.' + frac) if frac else '')
    else:
        # Koma desimal tunggal gaya Eropa: 11,5 → 11.5
        if ',' in s and '.' not in s:
            s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"harga tidak valid: {raw!r}")


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

# Cache sederhana: simpan hasil fetch 15 menit supaya dashboard tidak lambat
_cache = {"data": None, "ts": 0.0}
CACHE_TTL_SECONDS = 15 * 60

# Failure breaker: kalau Bapanas gagal, jangan coba lagi 5 menit (dashboard tetap cepat)
_fail = {"ts": 0.0}
FAIL_COOLDOWN_SECONDS = 5 * 60


def fetch_prices() -> dict:
    """Coba ambil harga real dari Bapanas (cache 15 menit + cooldown saat gagal).

    Returns dict: {key: {"name", "price", "unit", "date"}}
    """
    import time
    now = time.time()
    # 1) Pakai cache kalau masih segar
    if _cache["data"] is not None and (now - _cache["ts"]) < CACHE_TTL_SECONDS:
        return _cache["data"]
    # 2) Jangan coba network lagi kalau baru gagal (dalam cooldown)
    if now - _fail["ts"] < FAIL_COOLDOWN_SECONDS:
        return _fallback_prices()

    try:
        req = urllib.request.Request(
            BAPANAS_API,
            headers={"User-Agent": "Mozilla/5.0 (DapurPangan/0.2)"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")

        # Upaya parse JSON (Bapanas punya beberapa varian endpoint)
        try:
            data = json.loads(raw)
            result = _parse_bapanas(data)
            _cache["data"] = result
            _cache["ts"] = now
            return result
        except json.JSONDecodeError:
            logger.info("Bapanas: respons bukan JSON murni — pakai fallback")
            _fail["ts"] = now  # aktifkan cooldown supaya request berikutnya instan
            return _fallback_prices()

    except Exception as e:
        logger.warning(f"Bapanas tidak tersedia ({e}) — pakai fallback")
        _fail["ts"] = now  # aktifkan cooldown supaya request berikutnya instan
        return _fallback_prices()


def _parse_bapanas(data) -> dict:
    """Parse struktur data Bapanas (beragam bentuk) ke format standar kita.

    Satu item gagal diparse TIDAK membatalkan item lain (try/continue per item).
    """
    result = _fallback_prices()
    try:
        # Bentuk umum: list of {kode, nama, harga, ...} atau dict {komoditas: {...}}
        items = data if isinstance(data, list) else data.get("data", [])
        if isinstance(items, dict):
            items = list(items.values())
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                name = str(item.get("nama", item.get("name", ""))).lower()
                price = item.get("harga", item.get("price"))
                if price is None or price == "":
                    continue
                price_f = _sanitize_number(price)
                # Pilih komoditas dengan alias TERPANJANG yang match —
                # hindari 'Cabe Merah' salah masuk ke 'cabai rawit' (alias 'cabe')
                best_key, best_len = None, 0
                for key, cfg in MONITORED.items():
                    for a in cfg["alias"]:
                        if a in name and len(a) > best_len:
                            best_key, best_len = key, len(a)
                if best_key:
                    result[best_key] = {
                        "name": MONITORED[best_key]["name"],
                        "price": price_f,
                        "unit": "kg",
                        "date": str(date.today()),
                    }
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Item Bapanas dilewati ({type(e).__name__}: {e}): {item}"
                )
                continue
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
