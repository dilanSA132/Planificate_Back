from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, func, Boolean, ARRAY
from sqlalchemy.orm import relationship
from database import Base

class PublicRoute(Base):
    __tablename__ = "public_routes"

    id = Column(Integer, primary_key=True, index=True)
    original_trip_id = Column(Integer, ForeignKey("trips.id", ondelete="SET NULL"), nullable=True, index=True)
    author_id = Column(String, ForeignKey("users.firebase_uid", ondelete="CASCADE"), nullable=False, index=True)
    
    # Route info
    title = Column(String(150), nullable=False)
    description = Column(Text)
    cover_image_url = Column(String(500), nullable=True)
    
    # Metadata de la ruta
    total_distance_km = Column(Float, nullable=True)
    total_duration_hours = Column(Float, nullable=True)
    estimated_total_cost = Column(Float, nullable=True)
    difficulty_level = Column(String(20), nullable=True)  # easy, moderate, hard
    
    # Categorización
    tags = Column(ARRAY(String), nullable=True)  # Array de tags
    season = Column(String(20), nullable=True)  # best season to visit
    
    # Engagement metrics
    views_count = Column(Integer, default=0, nullable=False)
    likes_count = Column(Integer, default=0, nullable=False)
    saves_count = Column(Integer, default=0, nullable=False)
    
    # Estado
    is_published = Column(Boolean, default=False, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Location info (from original trip)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    center_lat = Column(Float, nullable=True)
    center_lng = Column(Float, nullable=True)
    
    # Relationships
    author = relationship("User", lazy="joined")
    original_trip = relationship("Trip")
    stops = relationship("PublicRouteStop", back_populates="route", cascade="all, delete-orphan")
    likes = relationship("RouteLike", back_populates="route", cascade="all, delete-orphan")
    saves = relationship("RouteSave", back_populates="route", cascade="all, delete-orphan")

