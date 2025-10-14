from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.Trip import Trip
from models.User import User
from schemas import TripWrite, TripRead
from database import get_db

router = APIRouter(prefix="/trips", tags=["Trips"])


@router.post("/", response_model=TripRead, status_code=status.HTTP_201_CREATED)
def create_trip(payload: TripWrite, db: Session = Depends(get_db)):
    owner = db.query(User).filter(User.id == payload.owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner no existe")

    trip = Trip(**payload.model_dump())
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


@router.get("/", response_model=List[TripRead])
def list_trips(db: Session = Depends(get_db)):
    return db.query(Trip).all()


@router.get("/{trip_id}", response_model=TripRead)
def get_trip(trip_id: int, db: Session = Depends(get_db)):
    t = db.query(Trip).filter(Trip.id == trip_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Viaje no encontrado")
    return t


@router.put("/{trip_id}", response_model=TripRead)
def update_trip(trip_id: int, payload: TripWrite, db: Session = Depends(get_db)):
    t = db.query(Trip).filter(Trip.id == trip_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Viaje no encontrado")

    if payload.owner_id != t.owner_id:
        owner = db.query(User).filter(User.id == payload.owner_id).first()
        if not owner:
            raise HTTPException(status_code=404, detail="Owner no existe")

    for k, v in payload.model_dump().items():
        setattr(t, k, v)

    db.commit()
    db.refresh(t)
    return t


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(trip_id: int, db: Session = Depends(get_db)):
    t = db.query(Trip).filter(Trip.id == trip_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Viaje no encontrado")
    db.delete(t)
    db.commit()
