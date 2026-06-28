from math import radians, sin, cos, sqrt, atan2
from inference.loader import get_state

_EARTH_RADIUS_M = 6_371_000


def haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distancia en metros entre dos puntos en grados decimales."""
    lat1_r, lng1_r = radians(lat1), radians(lng1)
    lat2_r, lng2_r = radians(lat2), radians(lng2)
    dlat = lat2_r - lat1_r
    dlng = lng2_r - lng1_r
    a = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlng / 2) ** 2
    return _EARTH_RADIUS_M * 2 * atan2(sqrt(a), sqrt(1 - a))


def assign_zone(lat: float, lng: float) -> dict:
    """
    Asigna la zona más cercana a las coordenadas dadas.

    Retorna:
        zone_id          - int o None si outlier / sin modelo
        distance_meters  - float o None si sin modelo
        assigned         - bool
        mode             - 'normal' | 'no_model'
    """
    state = get_state()

    if not state["centroids"]:
        return {
            "zone_id": None,
            "distance_meters": None,
            "assigned": False,
            "mode": "no_model",
        }

    eps = state["eps_meters"]
    distances = [
        {
            "zone_id": c["zone_id"],
            "distance": haversine_meters(lat, lng, float(c["centroid_lat"]), float(c["centroid_lng"])),
        }
        for c in state["centroids"]
    ]

    nearest = min(distances, key=lambda x: x["distance"])

    if nearest["distance"] <= eps:
        return {
            "zone_id": int(nearest["zone_id"]),
            "distance_meters": round(nearest["distance"], 2),
            "assigned": True,
            "mode": "normal",
        }

    return {
        "zone_id": None,
        "distance_meters": round(nearest["distance"], 2),
        "assigned": False,
        "mode": "normal",
    }
