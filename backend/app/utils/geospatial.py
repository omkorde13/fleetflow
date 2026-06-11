import math
from typing import Tuple


EARTH_RADIUS_KM = 6371.0


def haversine_distance(
    lat1: float, lng1: float, lat2: float, lng2: float
) -> float:
    """
    Calculate the great-circle distance between two points on Earth (in km).
    Uses the Haversine formula.
    """
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the initial bearing from point 1 to point 2 (degrees, 0–360).
    """
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlng = math.radians(lng2 - lng1)

    x = math.sin(dlng) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(
        lat2_r
    ) * math.cos(dlng)
    b = math.degrees(math.atan2(x, y))
    return (b + 360) % 360


def bounding_box(
    lat: float, lng: float, radius_km: float
) -> Tuple[float, float, float, float]:
    """
    Return approximate bounding box (min_lat, max_lat, min_lng, max_lng)
    for a circle of radius_km around a point. Used for fast DB pre-filter
    before exact haversine calculation.
    """
    lat_delta = math.degrees(radius_km / EARTH_RADIUS_KM)
    lng_delta = math.degrees(
        radius_km / (EARTH_RADIUS_KM * math.cos(math.radians(lat)))
    )
    return (
        lat - lat_delta,
        lat + lat_delta,
        lng - lng_delta,
        lng + lng_delta,
    )


def is_within_radius(
    center_lat: float,
    center_lng: float,
    point_lat: float,
    point_lng: float,
    radius_km: float,
) -> bool:
    """Check if a point is within radius_km of a center."""
    return haversine_distance(center_lat, center_lng, point_lat, point_lng) <= radius_km


def midpoint(
    lat1: float, lng1: float, lat2: float, lng2: float
) -> Tuple[float, float]:
    """Return the geographic midpoint between two coordinates."""
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlng = math.radians(lng2 - lng1)

    bx = math.cos(lat2_r) * math.cos(dlng)
    by = math.cos(lat2_r) * math.sin(dlng)

    mid_lat = math.atan2(
        math.sin(lat1_r) + math.sin(lat2_r),
        math.sqrt((math.cos(lat1_r) + bx) ** 2 + by ** 2),
    )
    mid_lng = math.radians(lng1) + math.atan2(by, math.cos(lat1_r) + bx)
    return math.degrees(mid_lat), math.degrees(mid_lng)
