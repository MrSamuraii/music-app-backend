import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    share_code = Column(String, unique=True, nullable=True, index=True)

    owner = relationship("User")
    tracks = relationship(
        "PlaylistTrack", back_populates="playlist", order_by="PlaylistTrack.position"
    )


class PlaylistTrack(Base):
    """Связь многие-ко-многим между плейлистом и треком + порядок трека в плейлисте."""

    __tablename__ = "playlist_tracks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    playlist_id = Column(UUID(as_uuid=True), ForeignKey("playlists.id"), nullable=False)
    track_id = Column(UUID(as_uuid=True), ForeignKey("tracks.id"), nullable=False)
    position = Column(Integer, nullable=False, default=0)

    playlist = relationship("Playlist", back_populates="tracks")
    track = relationship("Track")
