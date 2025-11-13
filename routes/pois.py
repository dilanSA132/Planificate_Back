from typing import List
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models.Trip import Trip
from models.POI import POI
from models.ItineraryItem import ItineraryItem
from schemas import POIWrite, POIRead, POIUpdate
from database import get_db
from utils.geocoding_helpers import geocode_place_to_coords, reverse_geocode_coords, build_place_query, haversine_distance

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

    # Validar que no exista un POI duplicado (mismo lugar, mismo viaje, mismo día)
    if data.get("lat") and data.get("lng"):
        # Buscar POIs existentes en el mismo viaje con coordenadas cercanas
        existing_pois = db.query(POI).filter(
            POI.trip_id == trip_id,
            POI.lat.isnot(None),
            POI.lng.isnot(None)
        ).all()
        
        # Distancia máxima para considerar que es el mismo lugar (100 metros)
        MAX_DISTANCE_METERS = 100
        
        # Obtener la fecha del nuevo POI si tiene scheduled_at
        new_poi_date = None
        if data.get("scheduled_at"):
            if isinstance(data["scheduled_at"], datetime):
                new_poi_date = data["scheduled_at"].date()
            elif isinstance(data["scheduled_at"], str):
                try:
                    # Intentar parsear el string como datetime
                    new_poi_date = datetime.fromisoformat(data["scheduled_at"].replace('Z', '+00:00')).date()
                except (ValueError, AttributeError):
                    pass
        
        for existing_poi in existing_pois:
            if existing_poi.lat is None or existing_poi.lng is None:
                continue
                
            # Calcular distancia entre el nuevo POI y el POI existente
            distance = haversine_distance(
                data["lat"], data["lng"],
                existing_poi.lat, existing_poi.lng
            )
            
            # Si están muy cerca (mismo lugar)
            if distance <= MAX_DISTANCE_METERS:
                # Obtener la fecha del POI existente
                existing_poi_date = None
                
                # Si el POI existente tiene scheduled_at directamente, usar esa fecha
                if existing_poi.scheduled_at:
                    if isinstance(existing_poi.scheduled_at, datetime):
                        existing_poi_date = existing_poi.scheduled_at.date()
                
                # Si el POI existente no tiene scheduled_at, verificar si tiene ItineraryItems programados
                if not existing_poi_date:
                    # Buscar ItineraryItems asociados a este POI con start_ts
                    itinerary_item = db.query(ItineraryItem).filter(
                        ItineraryItem.poi_id == existing_poi.id,
                        ItineraryItem.start_ts.isnot(None)
                    ).order_by(ItineraryItem.start_ts).first()
                    
                    if itinerary_item and itinerary_item.start_ts:
                        existing_poi_date = itinerary_item.start_ts.date()
                
                # Caso 1: Ambos POIs tienen fecha programada y es el mismo día
                if new_poi_date and existing_poi_date and new_poi_date == existing_poi_date:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Ya existe un POI en este lugar programado para el mismo día ({new_poi_date.strftime('%d/%m/%Y')}). El POI existente es: {existing_poi.name}"
                    )
                
                # Caso 2: Ninguno tiene fecha programada (POIs no programados) - rechazar para evitar duplicados
                elif not new_poi_date and not existing_poi_date:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Ya existe un POI no programado en este lugar. El POI existente es: {existing_poi.name}"
                    )
                
                # Caso 3: Uno tiene fecha y el otro no, o fechas diferentes - permitir (pueden ser para diferentes días)

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
def update_poi_by_id(poi_id: int, payload: POIUpdate, db: Session = Depends(get_db)):
    """Actualizar POI por ID directamente (sin requerir trip_id en la ruta)"""
    poi = db.query(POI).filter_by(id=poi_id).first()
    if not poi:
        raise HTTPException(status_code=404, detail="POI no encontrado")

    # Solo actualizar campos que fueron proporcionados
    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
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
