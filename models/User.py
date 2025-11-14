from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    firebase_uid = Column(String(64), primary_key=True, unique=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    bio = Column(Text, nullable=True)  # Biografía del usuario
    profile_image_url = Column(String(500), nullable=True)  # URL de imagen de perfil
    followers_count = Column(Integer, default=0, nullable=False)  # Contador de seguidores
    following_count = Column(Integer, default=0, nullable=False)  # Contador de seguidos
    fcm_token = Column(String(500), nullable=True)  # Firebase Cloud Messaging token
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    following = relationship("Follow", foreign_keys="Follow.follower_id", back_populates="follower", cascade="all, delete-orphan")
    followers = relationship("Follow", foreign_keys="Follow.following_id", back_populates="following_user", cascade="all, delete-orphan")
