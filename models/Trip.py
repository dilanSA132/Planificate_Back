from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, func, Float, Boolean
from sqlalchemy.orm import relationship
from database import Base

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("users.firebase_uid", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    center_lat = Column(Float, nullable=True)
    center_lng = Column(Float, nullable=True)
    # Location/place fields (human-readable)
    city = Column(String(100), nullable=True)  # Main city/destination
    country = Column(String(100), nullable=True)
    address = Column(String(250), nullable=True)  # Optional detailed address
    is_public = Column(Boolean, default=False, nullable=False)  # Social feature: public routes
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner = relationship("User", lazy="joined")
    members = relationship("TripMember", back_populates="trip", cascade="all, delete-orphan")
    pois = relationship("POI", back_populates="trip", cascade="all, delete-orphan")
    itinerary_items = relationship("ItineraryItem", back_populates="trip", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="trip", cascade="all, delete-orphan")
