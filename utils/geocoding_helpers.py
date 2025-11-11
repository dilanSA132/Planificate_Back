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
