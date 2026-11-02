import uuid
from datetime import datetime

from pydantic import BaseModel


class MessageOut(BaseModel):
    id: uuid.UUID
    from_user_id: uuid.UUID
    to_user_id: uuid.UUID
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    to_user_id: uuid.UUID
    content: str
