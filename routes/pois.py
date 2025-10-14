from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.Trip import Trip
from models.POI import POI
from schemas import POIWrite, POIRead
from database import get_db

router = APIRouter(prefix="/trips/{trip_id}/pois", tags=["POIs"])


@router.post("/", response_model=POIRead, status_code=status.HTTP_201_CREATED)
def create_poi(trip_id: int, payload: POIWrite, db: Session = Depends(get_db)):
    if payload.trip_id != trip_id:
        raise HTTPException(status_code=400, detail="trip_id en body no coincide con el path")

    if not db.query(Trip).filter(Trip.id == trip_id).first():
        raise HTTPException(status_code=404, detail="Trip no existe")

    poi = POI(**payload.model_dump())
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
