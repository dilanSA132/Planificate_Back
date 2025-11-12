from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base

class RouteLike(Base):
    __tablename__ = "route_likes"
    __table_args__ = (
        UniqueConstraint("route_id", "user_id", name="uq_route_like"),
    )

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("public_routes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.firebase_uid", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    route = relationship("PublicRoute", back_populates="likes")
    user = relationship("User")

