import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)  # может быть пустым для входа через Google
    created_at = Column(DateTime, default=datetime.utcnow)

    # Email-верификация при регистрации
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_code = Column(String, nullable=True)
    verification_expires = Column(DateTime, nullable=True)

    # Вход через Google
    google_id = Column(String, unique=True, nullable=True)
    auth_provider = Column(String, default="local", nullable=False)  # "local" | "google"

    # "Сейчас слушает" — для живой активности друзей
    now_playing_track_id = Column(UUID(as_uuid=True), nullable=True)
    now_playing_updated_at = Column(DateTime, nullable=True)

    # Закреплённый трек в профиле (как избранное на видном месте)
    pinned_track_id = Column(UUID(as_uuid=True), ForeignKey("tracks.id"), nullable=True)
    pinned_track = relationship("Track", foreign_keys=[pinned_track_id])
