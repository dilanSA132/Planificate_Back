# schemas.py (Pydantic v1)
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime


# ---------- Users ----------
class UserBase(BaseModel):
    firebase_uid: str
    username: str
    email: EmailStr
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None

class UserWrite(UserBase):
    pass

class UserUpdate(BaseModel):
    """Partial update for users"""
    username: Optional[str] = None
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None

class UserRead(UserBase):
    followers_count: int
    following_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class UserProfileRead(UserRead):
    """Extended user profile with follow status"""
    is_following: Optional[bool] = None  # True if current user follows this user
    is_followed_by: Optional[bool] = None  # True if this user follows current user


# ---------- Trips ----------
class TripBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    # Can provide coords OR place name; coords will be geocoded if missing
    center_lat: Optional[float] = None
    center_lng: Optional[float] = None
    city: Optional[str] = None
    country: Optional[str] = None
    address: Optional[str] = None
    is_public: Optional[bool] = False

class TripWrite(TripBase):
    owner_id: str

class TripRead(TripBase):
    id: int
    owner_id: str
    center_lat: Optional[float] = None
    center_lng: Optional[float] = None
    city: Optional[str] = None
    country: Optional[str] = None
    address: Optional[str] = None
    is_public: bool
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
    # Can provide coords OR address/place; will geocode if only address provided
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    place_name: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None  # How long to spend at this POI (in minutes)
    estimated_cost: Optional[float] = None  # Estimated cost for this POI

class POIWrite(POIBase):
    trip_id: int

class POIUpdate(BaseModel):
    """Schema for partial updates (PATCH) - all fields optional"""
    name: Optional[str] = None
    notes: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    place_name: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    estimated_cost: Optional[float] = None

class POIRead(POIBase):
    id: int
    trip_id: int
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    place_name: Optional[str] = None

    class Config:
        orm_mode = True


# ---------- Itinerary Items ----------
class ItineraryItemBase(BaseModel):
    name: Optional[str] = None  # For activities without POI
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


# ---------- Schedule (Combined POIs and ItineraryItems) ----------
class ScheduleActivity(BaseModel):
    """Represents an activity in the schedule (POI or ItineraryItem)"""
    id: str  # "poi_{id}" or "item_{id}"
    type: str  # "poi" or "itinerary_item"
    name: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    poi_id: Optional[int] = None
    itinerary_item_id: Optional[int] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    estimated_cost: Optional[float] = None
    description: Optional[str] = None

class FreeTimeSlot(BaseModel):
    """Represents free time between activities"""
    start_time: datetime
    end_time: datetime
    duration_minutes: int

class ScheduleDay(BaseModel):
    """Schedule for a specific day"""
    date: date
    activities: List[ScheduleActivity] = []
    free_time_slots: List[FreeTimeSlot] = []

class TripSchedule(BaseModel):
    """Complete schedule for a trip"""
    trip_id: int
    days: List[ScheduleDay] = []
    unscheduled_pois: List[POIRead] = []  # POIs without scheduled_at
    unscheduled_items: List[ItineraryItemRead] = []  # ItineraryItems without start_ts


# ---------- Chat Messages ----------
class ChatMessageBase(BaseModel):
    body: str = ""  # Permitir body vacío si hay archivo
    file_url: Optional[str] = None
    file_type: Optional[str] = None
    file_name: Optional[str] = None  # Nombre original del archivo

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


# ---------- Public Routes (Social Feature) ----------

class PublicRouteStopBase(BaseModel):
    name: str
    description: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    address: Optional[str] = None
    place_name: Optional[str] = None
    duration_minutes: Optional[int] = None
    estimated_cost: Optional[float] = None
    photos: Optional[List[str]] = None

class PublicRouteStopCreate(PublicRouteStopBase):
    order_index: int

class PublicRouteStopRead(PublicRouteStopBase):
    id: int
    route_id: int
    order_index: int

    class Config:
        orm_mode = True


class PublicRouteBase(BaseModel):
    title: str
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    total_distance_km: Optional[float] = None
    total_duration_hours: Optional[float] = None
    estimated_total_cost: Optional[float] = None
    difficulty_level: Optional[str] = None  # easy, moderate, hard
    tags: Optional[List[str]] = None
    season: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    center_lat: Optional[float] = None
    center_lng: Optional[float] = None

class PublicRouteCreate(PublicRouteBase):
    original_trip_id: Optional[int] = None
    stops: List[PublicRouteStopCreate]

class PublicRouteUpdate(BaseModel):
    """Partial update for public routes"""
    title: Optional[str] = None
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    difficulty_level: Optional[str] = None
    tags: Optional[List[str]] = None
    season: Optional[str] = None

class PublicRouteRead(PublicRouteBase):
    id: int
    original_trip_id: Optional[int] = None
    author_id: str
    author_username: Optional[str] = None  # Username del autor
    author_profile_image_url: Optional[str] = None  # Foto de perfil del autor
    views_count: int
    likes_count: int
    saves_count: int
    is_published: bool
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Include stops
    stops: List[PublicRouteStopRead] = []

    class Config:
        orm_mode = True


# ---------- Follows ----------
class FollowCreate(BaseModel):
    following_id: str  # ID del usuario a seguir

class FollowRead(BaseModel):
    id: int
    follower_id: str
    following_id: str
    created_at: datetime

    class Config:
        orm_mode = True


# ---------- Route Interactions ----------
class RouteLikeCreate(BaseModel):
    route_id: int

class RouteLikeRead(BaseModel):
    id: int
    route_id: int
    user_id: str
    created_at: datetime

    class Config:
        orm_mode = True


class RouteSaveCreate(BaseModel):
    route_id: int

class RouteSaveRead(BaseModel):
    id: int
    route_id: int
    user_id: str
    created_at: datetime

    class Config:
        orm_mode = True
