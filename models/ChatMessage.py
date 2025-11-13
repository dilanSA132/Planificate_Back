from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, func, String
from sqlalchemy.orm import relationship
from database import Base

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.firebase_uid", ondelete="CASCADE"), nullable=False, index=True)
    body = Column(Text, nullable=False)
    file_url = Column(String(500), nullable=True)  # URL del archivo adjunto
    file_type = Column(String(50), nullable=True)  # Tipo: 'image' o 'pdf'
    file_name = Column(String(255), nullable=True)  # Nombre original del archivo
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    trip = relationship("Trip", back_populates="chat_messages")
    user = relationship("User")
