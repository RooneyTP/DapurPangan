"""Route Optimizer — Nearest Neighbor TSP + shelf-life priority.

Sesusai PRD FR-LOG-001: Rule-based TSP heuristic.
Cukup untuk 5-30 titik per rute.
Tidak pakai Google Maps API berbayar.
"""
import math
from datetime import date, timedelta
from typing import Optional

# Koordinat home base — Dapur Bu Sumi di Lamongan
HOME_LAT, HOME_LNG = -7.1098, 112.4165
AVG_SPEED_KMPH = 25        # kecepatan rata-rata motor di kota
MIN_PER_STOP = 5            # waktu bongkar per titik (menit)
PROD_SHELF_LIFE_HOURS = 48  # shelf-life tempe = 2 hari


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Jarak antar dua titik koordinat (km)."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def estimate_travel_minutes(km: float) -> int:
    """Estimasi waktu tempuh dalam menit."""
    return max(1, int(km / AVG_SPEED_KMPH * 60))


def optimize_route(
    customers: list[dict],
    home_lat: float = HOME_LAT,
    home_lng: float = HOME_LNG,
    shelf_life_hours: int = PROD_SHELF_LIFE_HOURS
) -> dict:
    """
    Optimasi rute pakai Nearest Neighbor + shelf-life priority.
    
    Args:
        customers: list of dict dengan keys:
            - id, name, address, latitude, longitude, quantity
        home_lat, home_lng: koordinat dapur
        shelf_life_hours: masa simpan produk dalam jam
    
    Returns:
        dict dengan keys: stops, total_minutes, total_distance_km
    """
    if not customers:
        return {"stops": [], "total_minutes": 0, "total_distance_km": 0.0}

    # Filter hanya yg punya koordinat
    valid = [c for c in customers if c.get("latitude") and c.get("longitude")]
    if not valid:
        return {"stops": [], "total_minutes": 0, "total_distance_km": 0.0}

    # Nearest Neighbor dari home base
    unvisited = list(valid)
    current_lat, current_lng = home_lat, home_lng
    ordered = []
    total_distance_km = 0.0

    while unvisited:
        # Cari customer terdekat dari posisi sekarang
        nearest = None
        nearest_dist = float("inf")
        for c in unvisited:
            d = haversine_km(current_lat, current_lng, c["latitude"], c["longitude"])
            if d < nearest_dist:
                nearest_dist = d
                nearest = c

        if nearest is None:
            break

        ordered.append(nearest)
        total_distance_km += nearest_dist
        current_lat, current_lng = nearest["latitude"], nearest["longitude"]
        unvisited.remove(nearest)

    # Tambah jarak pulang ke home
    if ordered:
        total_distance_km += haversine_km(
            current_lat, current_lng, home_lat, home_lng
        )

    # Build stops dengan estimasi waktu & flag shelf-life
    stops = []
    running_minutes = 0
    for i, c in enumerate(ordered):
        dist_to_stop = haversine_km(
            home_lat if i == 0 else ordered[i-1]["latitude"],
            home_lng if i == 0 else ordered[i-1]["longitude"],
            c["latitude"], c["longitude"]
        )
        travel_min = estimate_travel_minutes(dist_to_stop)
        running_minutes += travel_min + MIN_PER_STOP

        # Flag risiko basi: kalau total waktu dari awal > shelf-life * 0.75
        if running_minutes > shelf_life_hours * 60 * 0.75:
            shelf_flag = "⚠️ risiko basi — prioritaskan"
        else:
            shelf_flag = "✅ shelf-life aman"

        stops.append({
            "order": i + 1,
            "customer_id": c["id"],
            "customer_name": c["name"],
            "address": c.get("address", ""),
            "quantity": c.get("quantity", 0),
            "product_name": c.get("product_name", "Tempe"),
            "estimated_minutes": running_minutes,
            "travel_minutes": travel_min,
            "shelf_life_flag": shelf_flag,
        })

    return {
        "stops": stops,
        "total_minutes": running_minutes,
        "total_distance_km": round(total_distance_km, 1),
    }
