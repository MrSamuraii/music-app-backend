import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.friend import FriendRequest
from app.models.track import Track
from app.schemas.track import TrackOut

router = APIRouter(prefix="/presence", tags=["presence"])

ACTIVE_WINDOW = timedelta(minutes=5)


class NowPlayingUpdate(BaseModel):
    track_id: uuid.UUID | None = None


class FriendActivity(BaseModel):
    user_id: uuid.UUID
    username: str
    track: TrackOut | None = None
    updated_at: datetime | None = None


@router.post("")
def update_now_playing(
    payload: NowPlayingUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    current_user.now_playing_track_id = payload.track_id
    current_user.now_playing_updated_at = datetime.utcnow() if payload.track_id else None
    db.commit()
    return {"status": "ok"}


@router.get("/friends", response_model=list[FriendActivity])
def friends_activity(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    accepted = (
        db.query(FriendRequest)
        .filter(
            or_(FriendRequest.from_user_id == current_user.id, FriendRequest.to_user_id == current_user.id),
            FriendRequest.status == "accepted",
        )
        .all()
    )

    friend_ids = [
        req.to_user_id if req.from_user_id == current_user.id else req.from_user_id for req in accepted
    ]
    if not friend_ids:
        return []

    friends = db.query(User).filter(User.id.in_(friend_ids)).all()
    cutoff = datetime.utcnow() - ACTIVE_WINDOW

    result = []
    for f in friends:
        track = None
        is_active = (
            f.now_playing_track_id is not None
            and f.now_playing_updated_at is not None
            and f.now_playing_updated_at >= cutoff
        )
        if is_active:
            track = db.query(Track).filter(Track.id == f.now_playing_track_id).first()

        result.append(
            FriendActivity(
                user_id=f.id,
                username=f.username,
                track=track if track else None,
                updated_at=f.now_playing_updated_at if is_active else None,
            )
        )
    return result
