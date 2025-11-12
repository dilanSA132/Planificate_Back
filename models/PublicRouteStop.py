from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, ARRAY
from sqlalchemy.orm import relationship
from database import Base

class PublicRouteStop(Base):
    __tablename__ = "public_route_stops"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("public_routes.id", ondelete="CASCADE"), nullable=False, index=True)
    order_index = Column(Integer, nullable=False)  # orden en la ruta
    
    # Stop info
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    address = Column(String(250), nullable=True)
    place_name = Column(String(200), nullable=True)
    
    # Duration and cost
    duration_minutes = Column(Integer, nullable=True)
    estimated_cost = Column(Float, nullable=True)
    
    # Photos
    photos = Column(ARRAY(String), nullable=True)  # Array de URLs
    
    # Relationship
    route = relationship("PublicRoute", back_populates="stops")

