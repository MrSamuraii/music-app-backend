import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.track import TrackOut


class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str


class GoogleAuthRequest(BaseModel):
    code: str
    redirect_uri: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    username: str
    created_at: datetime
    pinned_track: TrackOut | None = None

    class Config:
        from_attributes = True


class PinTrackRequest(BaseModel):
    track_id: uuid.UUID


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
