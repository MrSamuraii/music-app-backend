import uuid
from datetime import datetime

from pydantic import BaseModel


class TrackOut(BaseModel):
    id: uuid.UUID
    title: str
    artist: str
    album: str | None = None
    duration_seconds: int
    cover_path: str | None = None
    lyrics_lrc: str | None = None
    uploaded_by: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
