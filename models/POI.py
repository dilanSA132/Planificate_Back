from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class POI(Base):
    __tablename__ = "pois"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    notes = Column(Text)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    trip = relationship("Trip", back_populates="pois")
    estimates = relationship("PoiCostEstimate", back_populates="poi", cascade="all, delete-orphan")
    itinerary_items = relationship("ItineraryItem", back_populates="poi")
