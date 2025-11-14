from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from models.Trip import Trip
from models.User import User
from models.TripMember import TripMember
from schemas import TripWrite, TripRead
from database import get_db
from utils.geocoding_helpers import (
    geocode_place_to_coords,
    reverse_geocode_coords,
    build_place_query
)
import json

router = APIRouter(prefix="/trips", tags=["Trips"])
@router.get("/by_owner/{firebase_uid}")
def get_trips_by_owner_or_member(firebase_uid: str, db: Session = Depends(get_db)):

    trips = (
        db.query(Trip)
        .options(
            joinedload(Trip.owner),
            joinedload(Trip.members).joinedload(TripMember.user),
            joinedload(Trip.pois),
        )
        .outerjoin(TripMember, Trip.id == TripMember.trip_id)
        .filter(
            or_(
                Trip.owner_id == firebase_uid,
                TripMember.user_id == firebase_uid
            )
        )
        .distinct()
        .all()
    )

    normalized = []

    for trip in trips:
        normalized.append({
            "id": trip.id,
            "owner_id": trip.owner_id,
            "title": trip.title,
            "description": trip.description,
            "start_date": trip.start_date,
            "end_date": trip.end_date,
            "center_lat": trip.center_lat,
            "center_lng": trip.center_lng,
            "city": trip.city,
            "country": trip.country,
            "address": trip.address,
            "is_public": trip.is_public,
            "created_at": trip.created_at,
            "updated_at": trip.updated_at,

            # ⭐ POIs SOLO id + name
            "pois": [
                {"id": p.id, "name": p.name}
                for p in trip.pois
            ],

            # ⭐ colaboradores completos
            "members": [
                {
                    "user_id": m.user.firebase_uid,
                    "username": m.user.username,
                    "email": m.user.email,
                    "profile_image_url": m.user.profile_image_url,
                    "role": m.role,
                    "joined_at": m.joined_at
                }
                for m in trip.members
            ],

            # ⭐ owner
            "owner": {
                "user_id": trip.owner.firebase_uid,
                "username": trip.owner.username,
                "email": trip.owner.email,
                "profile_image_url": trip.owner.profile_image_url,
            }
        })

    print("\n📤 Enviando trips normalizados:")
    print(json.dumps(normalized, default=str, ensure_ascii=False, indent=2))

    return normalized

@router.post("/", response_model=TripRead, status_code=status.HTTP_201_CREATED)
async def create_trip(payload: TripWrite, db: Session = Depends(get_db)):
    owner = db.query(User).filter(User.firebase_uid == payload.owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner no existe")

    data = payload.model_dump()

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
                if not data.get("address"):
                    data["address"] = display_name

    # Reverse geocode for missing fields
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
        owner = db.query(User).filter(User.firebase_uid == payload.owner_id).first()
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


@router.post("/{trip_id}/add-member")
def add_member_to_trip(
    trip_id: int, 
    email: str,
    invited_by_id: str = None,  # En producción, obtener del token de autenticación. Si no se proporciona, usar owner_id
    db: Session = Depends(get_db)
):
    """Enviar invitación a un colaborador (ahora crea una invitación en lugar de agregar directamente)"""
    from routes.trip_invitations import create_invitation
    from schemas import TripInvitationWrite
    
    # Si no se proporciona invited_by_id, usar el owner_id del viaje
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Viaje no encontrado")
    
    if not invited_by_id:
        invited_by_id = trip.owner_id
    
    payload = TripInvitationWrite(email=email, message=None)
    invitation = create_invitation(trip_id, payload, invited_by_id, db)
    return {"message": "Invitación enviada correctamente", "invitation_id": invitation["id"]}


@router.get("/{trip_id}/members")
def list_trip_members(trip_id: int, db: Session = Depends(get_db)):

    members = (
        db.query(TripMember)
        .join(User, TripMember.user_id == User.firebase_uid)
        .filter(TripMember.trip_id == trip_id)
        .all()
    )

    result = []
    for m in members:
        result.append({
            "user_id": m.user_id,
            "username": m.user.username,
            "email": m.user.email,
            "profile_image_url": m.user.profile_image_url,
            "role": m.role,
            "joined_at": m.joined_at
        })

    print(f"\n📌 Miembros del trip {trip_id}:")
    for r in result:
        print(f" → {r['username']} ({r['email']})")

    return result

@router.delete("/{trip_id}/remove-member/{user_id}")
def remove_member(trip_id: int, user_id: str, db: Session = Depends(get_db)):
    member = db.query(TripMember).filter(
        TripMember.trip_id == trip_id,
        TripMember.user_id == user_id
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Este usuario no es miembro del viaje")

    db.delete(member)
    db.commit()

    return {"message": "Colaborador eliminado correctamente"}
