import uuid
from datetime import datetime

from pydantic import BaseModel


class UserPublic(BaseModel):
    id: uuid.UUID
    username: str

    class Config:
        from_attributes = True


class FriendRequestCreate(BaseModel):
    username: str


class FriendRequestOut(BaseModel):
    id: uuid.UUID
    from_user: UserPublic
    to_user: UserPublic
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
