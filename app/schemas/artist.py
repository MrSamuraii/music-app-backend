import uuid

from pydantic import BaseModel

from app.schemas.track import TrackOut


class ArtistSummary(BaseModel):
    id: uuid.UUID
    username: str
    track_count: int
    follower_count: int


class ArtistDetail(BaseModel):
    id: uuid.UUID
    username: str
    track_count: int
    follower_count: int
    is_following: bool
    tracks: list[TrackOut]
