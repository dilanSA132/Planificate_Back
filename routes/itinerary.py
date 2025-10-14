from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.Trip import Trip
from models.POI import POI
from models.ItineraryItem import ItineraryItem
from schemas import ItineraryItemWrite, ItineraryItemRead
from database import get_db

router = APIRouter(prefix="/trips/{trip_id}/itinerary", tags=["Itinerary"])


@router.post("/", response_model=ItineraryItemRead, status_code=status.HTTP_201_CREATED)
def create_item(trip_id: int, payload: ItineraryItemWrite, db: Session = Depends(get_db)):
    if payload.trip_id != trip_id:
        raise HTTPException(status_code=400, detail="trip_id en body no coincide con el path")

    if not db.query(Trip).filter(Trip.id == trip_id).first():
        raise HTTPException(status_code=404, detail="Trip no existe")

    if payload.poi_id:
        poi = db.query(POI).filter_by(id=payload.poi_id, trip_id=trip_id).first()
        if not poi:
            raise HTTPException(status_code=404, detail="POI no existe en este trip")

    item = ItineraryItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/", response_model=List[ItineraryItemRead])
def list_items(trip_id: int, db: Session = Depends(get_db)):
    return db.query(ItineraryItem).filter(ItineraryItem.trip_id == trip_id).all()


@router.put("/{item_id}", response_model=ItineraryItemRead)
def update_item(trip_id: int, item_id: int, payload: ItineraryItemWrite, db: Session = Depends(get_db)):
    item = db.query(ItineraryItem).filter_by(id=item_id, trip_id=trip_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ítem no encontrado")

    if payload.poi_id:
        poi = db.query(POI).filter_by(id=payload.poi_id, trip_id=trip_id).first()
        if not poi:
            raise HTTPException(status_code=404, detail="POI no existe en este trip")

    if payload.trip_id != trip_id:
        raise HTTPException(status_code=400, detail="No se puede mover el ítem a otro trip desde este endpoint")

    for k, v in payload.model_dump().items():
        setattr(item, k, v)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(trip_id: int, item_id: int, db: Session = Depends(get_db)):
    item = db.query(ItineraryItem).filter_by(id=item_id, trip_id=trip_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ítem no encontrado")
    db.delete(item)
    db.commit()
