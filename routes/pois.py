from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.Trip import Trip
from models.POI import POI
from schemas import POIWrite, POIRead
from database import get_db
from utils.geocoding_helpers import geocode_place_to_coords, reverse_geocode_coords, build_place_query

router = APIRouter(prefix="/trips/{trip_id}/pois", tags=["POIs"])


@router.post("/", response_model=POIRead, status_code=status.HTTP_201_CREATED)
async def create_poi(trip_id: int, payload: POIWrite, db: Session = Depends(get_db)):
    if payload.trip_id != trip_id:
        raise HTTPException(status_code=400, detail="trip_id en body no coincide con el path")

    if not db.query(Trip).filter(Trip.id == trip_id).first():
        raise HTTPException(status_code=404, detail="Trip no existe")

    data = payload.model_dump()
    
    # Auto-geocode: if no coords but address/place provided, geocode to get coords
    if data.get("lat") is None or data.get("lng") is None:
        place_query = build_place_query(
            city=data.get("city"),
            country=data.get("country"),
            address=data.get("address") or data.get("place_name")
        )
        if place_query:
            result = await geocode_place_to_coords(place_query)
            if result:
                lat, lon, display_name = result
                data["lat"] = lat
                data["lng"] = lon
                # Fill in address if not provided
                if not data.get("address"):
                    data["address"] = display_name
    
    # Auto-reverse-geocode: if coords provided but no city/country, reverse geocode
    if data.get("lat") and data.get("lng"):
        if not data.get("city") or not data.get("country"):
            result = await reverse_geocode_coords(data["lat"], data["lng"])
            if result:
                if not data.get("city"):
                    data["city"] = result.get("city")
                if not data.get("country"):
                    data["country"] = result.get("country")
                if not data.get("address"):
                    data["address"] = result.get("address")

    poi = POI(**data)
    db.add(poi)
    db.commit()
    db.refresh(poi)
    return poi


@router.get("/", response_model=List[POIRead])
def list_pois(trip_id: int, db: Session = Depends(get_db)):
    return db.query(POI).filter(POI.trip_id == trip_id).all()


@router.put("/{poi_id}", response_model=POIRead)
def update_poi(trip_id: int, poi_id: int, payload: POIWrite, db: Session = Depends(get_db)):
    poi = db.query(POI).filter_by(id=poi_id, trip_id=trip_id).first()
    if not poi:
        raise HTTPException(status_code=404, detail="POI no encontrado")

    if payload.trip_id != trip_id:
        raise HTTPException(status_code=400, detail="No se puede mover el POI a otro trip desde este endpoint")

    for k, v in payload.model_dump().items():
        setattr(poi, k, v)

    db.commit()
    db.refresh(poi)
    return poi


@router.delete("/{poi_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_poi(trip_id: int, poi_id: int, db: Session = Depends(get_db)):
    poi = db.query(POI).filter_by(id=poi_id, trip_id=trip_id).first()
    if not poi:
        raise HTTPException(status_code=404, detail="POI no encontrado")
    db.delete(poi)
    db.commit()


# Endpoints adicionales para operaciones sin necesidad de trip_id
router2 = APIRouter(prefix="/pois", tags=["POIs"])


@router2.patch("/{poi_id}", response_model=POIRead)
def update_poi_by_id(poi_id: int, payload: POIWrite, db: Session = Depends(get_db)):
    """Actualizar POI por ID directamente (sin requerir trip_id en la ruta)"""
    poi = db.query(POI).filter_by(id=poi_id).first()
    if not poi:
        raise HTTPException(status_code=404, detail="POI no encontrado")

    for k, v in payload.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(poi, k, v)

    db.commit()
    db.refresh(poi)
    return poi


@router2.delete("/{poi_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_poi_by_id(poi_id: int, db: Session = Depends(get_db)):
    """Eliminar POI por ID directamente (sin requerir trip_id en la ruta)"""
    poi = db.query(POI).filter_by(id=poi_id).first()
    if not poi:
        raise HTTPException(status_code=404, detail="POI no encontrado")
    db.delete(poi)
    db.commit()
