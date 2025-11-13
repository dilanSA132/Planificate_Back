"""
Routes for OpenStreetMap-based services: Overpass (POIs), OSRM (routing), Nominatim (geocoding).
Uses public APIs with caching and rate limiting for development.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import httpx
import hashlib
import json
from datetime import datetime, timedelta
from utils.logger import setup_api_logger

logger = setup_api_logger()
router = APIRouter(prefix="/osm", tags=["OSM Services"])

# Simple in-memory cache (for production use Redis)
_cache: Dict[str, tuple[Any, datetime]] = {}
CACHE_TTL = timedelta(hours=1)


def _get_cache(key: str) -> Optional[Any]:
    """Get cached value if not expired."""
    if key in _cache:
        value, expiry = _cache[key]
        if datetime.utcnow() < expiry:
            return value
        del _cache[key]
    return None


def _set_cache(key: str, value: Any):
    """Cache value with TTL."""
    _cache[key] = (value, datetime.utcnow() + CACHE_TTL)


# --- Overpass (POI search) ---

class POISearchRequest(BaseModel):
    """Search POIs using Overpass API."""
    # bbox: south,west,north,east or around: lat,lon,radius
    bbox: Optional[str] = Field(None, description="Bounding box: south,west,north,east")
    around: Optional[str] = Field(None, description="Around point: lat,lon,radius_meters")
    tags: Dict[str, str] = Field(
        default_factory=lambda: {"amenity": "restaurant"},
        description="OSM tags to filter (e.g., {'amenity': 'restaurant'})"
    )
    limit: int = Field(100, ge=1, le=500, description="Max results")


class POIResult(BaseModel):
    """Normalized POI result."""
    osm_id: int
    lat: float
    lon: float
    tags: Dict[str, str]
    name: Optional[str] = None
    type: Optional[str] = None


@router.post("/pois/search", response_model=List[POIResult])
async def search_pois(req: POISearchRequest):
    """
    Search for POIs using Overpass API.
    Caches results to avoid rate limits.
    """
    # Build Overpass query
    tag_filters = "".join([f'["{k}"="{v}"]' for k, v in req.tags.items()])
    
    if req.around:
        parts = req.around.split(",")
        if len(parts) != 3:
            raise HTTPException(400, "around must be lat,lon,radius")
        lat, lon, radius = parts
        spatial = f"(around:{radius},{lat},{lon})"
    elif req.bbox:
        parts = req.bbox.split(",")
        if len(parts) != 4:
            raise HTTPException(400, "bbox must be south,west,north,east")
        spatial = f"({','.join(parts)})"
    else:
        raise HTTPException(400, "Provide bbox or around parameter")
    
    query = f"[out:json][timeout:25];(node{tag_filters}{spatial};way{tag_filters}{spatial};);out center {req.limit};"
    
    # Check cache
    cache_key = hashlib.md5(query.encode()).hexdigest()
    cached = _get_cache(cache_key)
    if cached:
        return cached
    
    # Call Overpass
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://overpass-api.de/api/interpreter",
                params={"data": query}
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Overpass API error: {str(e)}")
    
    # Normalize results
    results = []
    for elem in data.get("elements", []):
        lat = elem.get("lat") or elem.get("center", {}).get("lat")
        lon = elem.get("lon") or elem.get("center", {}).get("lon")
        if not lat or not lon:
            continue
        
        tags = elem.get("tags", {})
        results.append(POIResult(
            osm_id=elem["id"],
            lat=lat,
            lon=lon,
            tags=tags,
            name=tags.get("name"),
            type=elem["type"]
        ))
    
    _set_cache(cache_key, results)
    return results


# --- OSRM (Routing) ---

class RouteRequest(BaseModel):
    """Calculate route between points."""
    points: List[List[float]] = Field(..., description="List of [lat, lon] coordinates", min_length=2)
    profile: str = Field("driving", description="OSRM profile: driving, walking, cycling")


class RouteResponse(BaseModel):
    """Route result."""
    distance: float = Field(..., description="Distance in meters")
    duration: float = Field(..., description="Duration in seconds")
    geometry: str = Field(..., description="Encoded polyline")
    waypoints: List[Dict[str, Any]] = Field(default_factory=list)
    legs: List[Dict[str, Any]] = Field(default_factory=list, description="Segments between waypoints")


@router.post("/route/calculate", response_model=RouteResponse)
async def calculate_route(req: RouteRequest):
    """
    Calculate route using OSRM public demo.
    Returns polyline geometry.
    """
    if len(req.points) < 2:
        raise HTTPException(400, "Need at least 2 points")
    
    # Build coordinate string (lon,lat format for OSRM)
    coords = ";".join([f"{p[1]},{p[0]}" for p in req.points])
    cache_key = hashlib.md5(f"{req.profile}:{coords}".encode()).hexdigest()
    
    cached = _get_cache(cache_key)
    if cached:
        return cached
    
    url = f"https://router.project-osrm.org/route/v1/{req.profile}/{coords}"
    params = {
        "overview": "full",
        "geometries": "polyline",
        "steps": "false"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        logger.error(f"OSRM API error: {str(e)}")
        raise HTTPException(502, f"OSRM API error: {str(e)}")
    
    if data.get("code") != "Ok":
        logger.error(f"OSRM returned error: {data.get('message', 'Unknown')}")
        raise HTTPException(400, f"OSRM error: {data.get('message', 'Unknown')}")
    
    route = data["routes"][0]
    
    result = RouteResponse(
        distance=route["distance"],
        duration=route["duration"],
        geometry=route["geometry"],
        waypoints=data.get("waypoints", []),
        legs=route.get("legs", [])
    )
    
    _set_cache(cache_key, result)
    return result


class OptimizeRequest(BaseModel):
    """Optimize visit order (TSP)."""
    points: List[List[float]] = Field(..., description="List of [lat, lon] coordinates", min_length=2)
    profile: str = Field("driving", description="OSRM profile")
    roundtrip: bool = Field(True, description="Return to start")


class OptimizeResponse(BaseModel):
    """Optimized route result."""
    distance: float
    duration: float
    geometry: str
    waypoints: List[Dict[str, Any]]
    trips: List[Dict[str, Any]]


@router.post("/route/optimize", response_model=OptimizeResponse)
async def optimize_route(req: OptimizeRequest):
    """
    Optimize visit order using TSP algorithm (Nearest Neighbor).
    Since OSRM public server doesn't support /trip endpoint, we implement our own TSP.
    """
    if len(req.points) < 2:
        raise HTTPException(400, "Need at least 2 points")
    
    # Cache key basado en los puntos y parámetros
    coords_str = ";".join([f"{p[1]},{p[0]}" for p in req.points])
    cache_key = hashlib.md5(f"tsp:{req.profile}:{coords_str}:{req.roundtrip}".encode()).hexdigest()
    
    cached = _get_cache(cache_key)
    if cached:
        return cached
    
    # Si solo hay 2 puntos, no hay optimización que hacer
    if len(req.points) == 2:
        coords = ";".join([f"{p[1]},{p[0]}" for p in req.points])
        url = f"https://router.project-osrm.org/route/v1/{req.profile}/{coords}"
        params = {"overview": "full", "geometries": "polyline", "steps": "false"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError as e:
            raise HTTPException(502, f"OSRM API error: {str(e)}")
        
        if data.get("code") != "Ok":
            raise HTTPException(400, f"OSRM error: {data.get('message', 'Unknown')}")
        
        route = data["routes"][0]
        waypoints = [{"waypoint_index": 0}, {"waypoint_index": 1}]
        
        result = OptimizeResponse(
            distance=route["distance"],
            duration=route["duration"],
            geometry=route["geometry"],
            waypoints=waypoints,
            trips=[route]
        )
        
        _set_cache(cache_key, result)
        return result
    
    # Calcular matriz de distancias usando fórmula de Haversine (más precisa para coordenadas geográficas)
    # Para una mejor precisión, podríamos usar OSRM /table, pero es más lento
    from math import radians, sin, cos, sqrt, atan2
    
    def haversine_distance(lat1, lon1, lat2, lon2):
        """Calcular distancia entre dos puntos usando fórmula de Haversine (en grados)"""
        # Convertir a radianes
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)
        
        # Diferencia de latitud y longitud
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Fórmula de Haversine
        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        # Retornar distancia (aproximada, suficiente para comparar)
        return c
    
    n = len(req.points)
    distances = [[0.0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(i + 1, n):
            # Distancia usando Haversine
            lat1, lon1 = req.points[i]
            lat2, lon2 = req.points[j]
            dist = haversine_distance(lat1, lon1, lat2, lon2)
            distances[i][j] = dist
            distances[j][i] = dist
    
    # Algoritmo Nearest Neighbor para TSP
    visited = [False] * n
    order = [0]  # Empezar desde el primer punto
    visited[0] = True
    
    for _ in range(n - 1):
        current = order[-1]
        nearest = None
        min_dist = float('inf')
        
        for j in range(n):
            if not visited[j] and distances[current][j] < min_dist:
                min_dist = distances[current][j]
                nearest = j
        
        if nearest is not None:
            order.append(nearest)
            visited[nearest] = True
    
    # Si roundtrip, agregar regreso al inicio
    if req.roundtrip:
        order.append(order[0])
    
    # Reordenar puntos según el orden optimizado (sin el punto final si es roundtrip)
    optimized_points = [req.points[i] for i in (order[:-1] if req.roundtrip else order)]
    
    # Calcular ruta con el orden optimizado usando /route de OSRM
    coords = ";".join([f"{p[1]},{p[0]}" for p in optimized_points])
    url = f"https://router.project-osrm.org/route/v1/{req.profile}/{coords}"
    params = {"overview": "full", "geometries": "polyline", "steps": "false"}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"OSRM API error: {str(e)}")
    
    if data.get("code") != "Ok":
        raise HTTPException(400, f"OSRM error: {data.get('message', 'Unknown')}")
    
    route = data["routes"][0]
    
    # Crear waypoints con los índices originales en el orden optimizado
    # El orden ya está optimizado, así que los waypoints reflejan ese orden
    waypoints = [{"waypoint_index": idx} for idx in (order[:-1] if req.roundtrip else order)]
    
    result = OptimizeResponse(
        distance=route["distance"],
        duration=route["duration"],
        geometry=route["geometry"],
        waypoints=waypoints,
        trips=[route]
    )
    
    _set_cache(cache_key, result)
    return result


# --- Nominatim (Geocoding) ---

class GeocodeRequest(BaseModel):
    """Forward geocoding request."""
    query: str = Field(..., description="Address or place name to geocode")
    limit: int = Field(5, ge=1, le=50)


class ReverseGeocodeRequest(BaseModel):
    """Reverse geocoding request."""
    lat: float
    lon: float


class GeocodeResult(BaseModel):
    """Geocoding result."""
    lat: float
    lon: float
    display_name: str
    osm_id: Optional[int] = None
    osm_type: Optional[str] = None
    place_id: Optional[int] = None
    importance: Optional[float] = None


@router.post("/geocode/forward", response_model=List[GeocodeResult])
async def geocode_forward(req: GeocodeRequest):
    """
    Forward geocoding: address -> coordinates using Nominatim.
    """
    cache_key = hashlib.md5(f"fwd:{req.query}:{req.limit}".encode()).hexdigest()
    cached = _get_cache(cache_key)
    if cached:
        return cached
    
    params = {
        "q": req.query,
        "format": "json",
        "limit": req.limit,
        "addressdetails": 1
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params=params,
                headers={"User-Agent": "PlanificateApp/1.0"}
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Nominatim API error: {str(e)}")
    
    results = [
        GeocodeResult(
            lat=float(item["lat"]),
            lon=float(item["lon"]),
            display_name=item["display_name"],
            osm_id=item.get("osm_id"),
            osm_type=item.get("osm_type"),
            place_id=item.get("place_id"),
            importance=item.get("importance")
        )
        for item in data
    ]
    
    _set_cache(cache_key, results)
    return results


@router.post("/geocode/reverse", response_model=GeocodeResult)
async def geocode_reverse(req: ReverseGeocodeRequest):
    """
    Reverse geocoding: coordinates -> address using Nominatim.
    """
    cache_key = hashlib.md5(f"rev:{req.lat},{req.lon}".encode()).hexdigest()
    cached = _get_cache(cache_key)
    if cached:
        return cached
    
    params = {
        "lat": req.lat,
        "lon": req.lon,
        "format": "json",
        "addressdetails": 1
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params=params,
                headers={"User-Agent": "PlanificateApp/1.0"}
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Nominatim API error: {str(e)}")
    
    if "error" in data:
        raise HTTPException(404, "No results found")
    
    result = GeocodeResult(
        lat=float(data["lat"]),
        lon=float(data["lon"]),
        display_name=data["display_name"],
        osm_id=data.get("osm_id"),
        osm_type=data.get("osm_type"),
        place_id=data.get("place_id"),
        importance=data.get("importance")
    )
    
    _set_cache(cache_key, result)
    return result
