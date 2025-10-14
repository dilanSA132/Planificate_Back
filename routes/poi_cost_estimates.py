from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.Trip import Trip
from models.POI import POI
from models.PoiCostEstimate import PoiCostEstimate
from schemas import PoiCostEstimateWrite, PoiCostEstimateRead
from database import get_db

router = APIRouter(prefix="/trips/{trip_id}/pois/{poi_id}/estimates", tags=["POI Cost Estimates"])


@router.post("/", response_model=PoiCostEstimateRead, status_code=status.HTTP_201_CREATED)
def create_estimate(trip_id: int, poi_id: int, payload: PoiCostEstimateWrite, db: Session = Depends(get_db)):
    if payload.poi_id != poi_id:
        raise HTTPException(status_code=400, detail="poi_id en body no coincide con el path")

    if not db.query(Trip).filter(Trip.id == trip_id).first():
        raise HTTPException(status_code=404, detail="Trip no existe")

    if not db.query(POI).filter_by(id=poi_id, trip_id=trip_id).first():
        raise HTTPException(status_code=404, detail="POI no existe en este trip")

    est = PoiCostEstimate(**payload.model_dump())
    db.add(est)
    db.commit()
    db.refresh(est)
    return est


@router.get("/", response_model=List[PoiCostEstimateRead])
def list_estimates(trip_id: int, poi_id: int, db: Session = Depends(get_db)):
    if not db.query(POI).filter_by(id=poi_id, trip_id=trip_id).first():
        raise HTTPException(status_code=404, detail="POI no existe en este trip")
    return db.query(PoiCostEstimate).filter(PoiCostEstimate.poi_id == poi_id).all()


@router.put("/{estimate_id}", response_model=PoiCostEstimateRead)
def update_estimate(trip_id: int, poi_id: int, estimate_id: int, payload: PoiCostEstimateWrite, db: Session = Depends(get_db)):
    est = db.query(PoiCostEstimate).filter_by(id=estimate_id, poi_id=poi_id).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estimate no encontrado")

    if payload.poi_id != poi_id:
        raise HTTPException(status_code=400, detail="No se puede mover el estimate a otro POI desde este endpoint")

    if not db.query(POI).filter_by(id=poi_id, trip_id=trip_id).first():
        raise HTTPException(status_code=404, detail="POI no existe en este trip")

    for k, v in payload.model_dump().items():
        setattr(est, k, v)

    db.commit()
    db.refresh(est)
    return est


@router.delete("/{estimate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_estimate(trip_id: int, poi_id: int, estimate_id: int, db: Session = Depends(get_db)):
    est = db.query(PoiCostEstimate).filter_by(id=estimate_id, poi_id=poi_id).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estimate no encontrado")
    db.delete(est)
    db.commit()
