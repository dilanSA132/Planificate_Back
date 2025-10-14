from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.Trip import Trip
from models.TripMember import TripMember
from models.User import User
from schemas import TripMemberWrite, TripMemberRead
from database import get_db

router = APIRouter(prefix="/trips/{trip_id}/members", tags=["Trip Members"])


@router.post("/", response_model=TripMemberRead, status_code=status.HTTP_201_CREATED)
def add_member(trip_id: int, payload: TripMemberWrite, db: Session = Depends(get_db)):
    if payload.trip_id != trip_id:
        raise HTTPException(status_code=400, detail="trip_id en body no coincide con el path")

    if not db.query(Trip).filter(Trip.id == trip_id).first():
        raise HTTPException(status_code=404, detail="Trip no existe")

    if not db.query(User).filter(User.id == payload.user_id).first():
        raise HTTPException(status_code=404, detail="Usuario no existe")

    exists = db.query(TripMember).filter_by(trip_id=trip_id, user_id=payload.user_id).first()
    if exists:
        raise HTTPException(status_code=409, detail="El usuario ya es miembro de este viaje")

    tm = TripMember(**payload.model_dump())
    db.add(tm)
    db.commit()
    db.refresh(tm)
    return tm


@router.get("/", response_model=List[TripMemberRead])
def list_members(trip_id: int, db: Session = Depends(get_db)):
    return db.query(TripMember).filter(TripMember.trip_id == trip_id).all()


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(trip_id: int, member_id: int, db: Session = Depends(get_db)):
    tm = db.query(TripMember).filter_by(id=member_id, trip_id=trip_id).first()
    if not tm:
        raise HTTPException(status_code=404, detail="Miembro no encontrado")
    db.delete(tm)
    db.commit()
