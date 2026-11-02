import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.track import TrackOut


class PlaylistCreate(BaseModel):
    name: str


class PlaylistOut(BaseModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    created_at: datetime
    track_count: int = 0
    share_code: str | None = None

    class Config:
        from_attributes = True


class PlaylistDetailOut(BaseModel):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    owner_username: str | None = None
    created_at: datetime
    share_code: str | None = None
    tracks: list[TrackOut]

    class Config:
        from_attributes = True


class AddTrackToPlaylist(BaseModel):
    track_id: uuid.UUID


class ReorderTracksRequest(BaseModel):
    track_ids: list[uuid.UUID]  # полный новый порядок треков в плейлисте
