"""
Geocoding helper utilities for auto-resolving place names to coordinates
and vice-versa using the internal OSM services.
"""
import httpx
from typing import Optional, Tuple


async def geocode_place_to_coords(
    place_query: str,
    timeout: float = 10.0
) -> Optional[Tuple[float, float, str]]:
    """
    Convert a place name/address to coordinates using internal Nominatim endpoint.
    
    Returns:
        (lat, lon, display_name) or None if geocoding fails
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": place_query,
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 1
                },
                headers={"User-Agent": "PlanificateApp/1.0"}
            )
            resp.raise_for_status()
            data = resp.json()
            
            if data:
                result = data[0]
                lat = float(result["lat"])
                lon = float(result["lon"])
                display_name = result["display_name"]
                return (lat, lon, display_name)
    except Exception:
        pass
    
    return None


async def reverse_geocode_coords(
    lat: float,
    lon: float,
    timeout: float = 10.0
) -> Optional[dict]:
    """
    Convert coordinates to address using internal Nominatim endpoint.
    
    Returns:
        Dict with keys: display_name, city, country, address or None
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "lat": lat,
                    "lon": lon,
                    "format": "json",
                    "addressdetails": 1
                },
                headers={"User-Agent": "PlanificateApp/1.0"}
            )
            resp.raise_for_status()
            data = resp.json()
            
            if "error" not in data:
                address_parts = data.get("address", {})
                return {
                    "display_name": data.get("display_name", ""),
                    "city": (
                        address_parts.get("city") or
                        address_parts.get("town") or
                        address_parts.get("village") or
                        address_parts.get("municipality") or
                        ""
                    ),
                    "country": address_parts.get("country", ""),
                    "address": data.get("display_name", "")
                }
    except Exception:
        pass
    
    return None


def build_place_query(city: Optional[str] = None, country: Optional[str] = None, address: Optional[str] = None) -> Optional[str]:
    """Build a place query string from city, country, address fields."""
    parts = []
    if address:
        parts.append(address)
    if city:
        parts.append(city)
    if country:
        parts.append(country)
    
    return ", ".join(parts) if parts else None


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on the Earth
    (specified in decimal degrees) using the Haversine formula.
    
    Returns:
        Distance in meters
    """
    from math import radians, cos, sin, asin, sqrt
    
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in meters
    r = 6371000
    
    return c * r
