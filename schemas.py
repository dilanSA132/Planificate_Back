# schemas.py (Pydantic v1)
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime


# ---------- Users ----------
class UserBase(BaseModel):
    firebase_uid: str
    username: str
    email: EmailStr

class UserWrite(UserBase):
    pass

class UserRead(UserBase):
    class Config:
        orm_mode = True


# ---------- Trips ----------
class TripBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None

class TripWrite(TripBase):
    owner_id: str

class TripRead(TripBase):
    id: int
    owner_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# ---------- Trip Members ----------
class TripMemberBase(BaseModel):
    role: Optional[str] = None

class TripMemberWrite(TripMemberBase):
    trip_id: int
    user_id: str

class TripMemberRead(TripMemberBase):
    id: int
    trip_id: int
    user_id: str
    joined_at: datetime

    class Config:
        orm_mode = True


# ---------- POIs ----------
class POIBase(BaseModel):
    name: str
    notes: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

class POIWrite(POIBase):
    trip_id: int

class POIRead(POIBase):
    id: int
    trip_id: int

    class Config:
        orm_mode = True


# ---------- Itinerary Items ----------
class ItineraryItemBase(BaseModel):
    start_ts: datetime
    end_ts: Optional[datetime] = None
    status: Optional[str] = None

class ItineraryItemWrite(ItineraryItemBase):
    trip_id: int
    poi_id: Optional[int] = None

class ItineraryItemRead(ItineraryItemBase):
    id: int
    trip_id: int
    poi_id: Optional[int] = None

    class Config:
        orm_mode = True


# ---------- Chat Messages ----------
class ChatMessageBase(BaseModel):
    body: str

class ChatMessageWrite(ChatMessageBase):
    trip_id: int
    user_id: str

class ChatMessageRead(ChatMessageBase):
    id: int
    trip_id: int
    user_id: str
    created_at: datetime

    class Config:
        orm_mode = True


# ---------- POI Cost Estimates ----------
class PoiCostEstimateBase(BaseModel):
    amount: float
    currency: str = "USD"

class PoiCostEstimateWrite(PoiCostEstimateBase):
    poi_id: int
    user_id: str

class PoiCostEstimateRead(PoiCostEstimateBase):
    id: int
    poi_id: int
    user_id: str

    class Config:
        orm_mode = True
