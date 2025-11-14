from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum, func, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base
import enum

class InvitationStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class TripInvitation(Base):
    __tablename__ = "trip_invitations"
    __table_args__ = (
        UniqueConstraint("trip_id", "invited_user_id", name="uq_trip_invitation"),
    )

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    invited_user_id = Column(String, ForeignKey("users.firebase_uid", ondelete="CASCADE"), nullable=False, index=True)
    invited_by_id = Column(String, ForeignKey("users.firebase_uid", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(SQLEnum(InvitationStatus), default=InvitationStatus.PENDING, nullable=False, index=True)
    message = Column(String(500), nullable=True)  # Mensaje opcional de invitación
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    responded_at = Column(DateTime(timezone=True), nullable=True)

    trip = relationship("Trip", back_populates="invitations")
    invited_user = relationship("User", foreign_keys=[invited_user_id])
    invited_by = relationship("User", foreign_keys=[invited_by_id])
