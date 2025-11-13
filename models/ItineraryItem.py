from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class ItineraryItem(Base):
    __tablename__ = "itinerary_items"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    poi_id = Column(Integer, ForeignKey("pois.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(150), nullable=True)  # For activities without POI
    start_ts = Column(DateTime(timezone=True), nullable=False)
    end_ts = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(40), nullable=True)

    trip = relationship("Trip", back_populates="itinerary_items")
    poi = relationship("POI", back_populates="itinerary_items")
