
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.Trip import Trip
from models.User import User
from schemas import TripWrite, TripRead
from database import get_db
from utils.geocoding_helpers import geocode_place_to_coords, reverse_geocode_coords, build_place_query

router = APIRouter(prefix="/trips", tags=["Trips"])

@router.get("/by_owner/{firebase_uid}", response_model=List[TripRead])
def get_trips_by_owner(firebase_uid: str, db: Session = Depends(get_db)):
    trips = db.query(Trip).filter(Trip.owner_id == firebase_uid).all()
    return trips

@router.post("/", response_model=TripRead, status_code=status.HTTP_201_CREATED)
async def create_trip(payload: TripWrite, db: Session = Depends(get_db)):
    owner = db.query(User).filter(User.firebase_uid == payload.owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner no existe")

    data = payload.model_dump()
    
    # Auto-geocode: if no coords but city/country provided, geocode to get coords
    if data.get("center_lat") is None or data.get("center_lng") is None:
        place_query = build_place_query(
            city=data.get("city"),
            country=data.get("country"),
            address=data.get("address")
        )
        if place_query:
            result = await geocode_place_to_coords(place_query)
            if result:
                lat, lon, display_name = result
                data["center_lat"] = lat
                data["center_lng"] = lon
                # Fill in address if not provided
                if not data.get("address"):
                    data["address"] = display_name
    
    # Auto-reverse-geocode: if coords provided but no city/country, reverse geocode
    if data.get("center_lat") and data.get("center_lng"):
        if not data.get("city") or not data.get("country"):
            result = await reverse_geocode_coords(data["center_lat"], data["center_lng"])
            if result:
                if not data.get("city"):
                    data["city"] = result.get("city")
                if not data.get("country"):
                    data["country"] = result.get("country")
                if not data.get("address"):
                    data["address"] = result.get("address")

    trip = Trip(**data)
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
