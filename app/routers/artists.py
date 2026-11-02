import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.track import Track
from app.models.follow import Follow
from app.schemas.artist import ArtistSummary, ArtistDetail

router = APIRouter(prefix="/artists", tags=["artists"])


@router.get("", response_model=list[ArtistSummary])
def list_artists(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(Track.uploaded_by, func.count(Track.id).label("track_count"))
        .group_by(Track.uploaded_by)
        .all()
    )
    result = []
    for uploader_id, track_count in rows:
        user = db.query(User).filter(User.id == uploader_id).first()
        if not user:
            continue
        follower_count = db.query(Follow).filter(Follow.artist_id == uploader_id).count()
        result.append(
            ArtistSummary(
                id=user.id, username=user.username, track_count=track_count, follower_count=follower_count
            )
        )
    return result


@router.get("/{artist_id}", response_model=ArtistDetail)
def get_artist(
    artist_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    artist = db.query(User).filter(User.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Артист не найден")

    tracks = db.query(Track).filter(Track.uploaded_by == artist_id).order_by(Track.created_at.desc()).all()
    follower_count = db.query(Follow).filter(Follow.artist_id == artist_id).count()
    is_following = (
        db.query(Follow)
        .filter(Follow.artist_id == artist_id, Follow.follower_id == current_user.id)
        .first()
        is not None
    )

    return ArtistDetail(
        id=artist.id,
        username=artist.username,
        track_count=len(tracks),
        follower_count=follower_count,
        is_following=is_following,
        tracks=tracks,
    )


@router.post("/{artist_id}/follow", status_code=status.HTTP_201_CREATED)
def follow_artist(
    artist_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if artist_id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя подписаться на самого себя")

    artist = db.query(User).filter(User.id == artist_id).first()
    if not artist:
        raise HTTPException(status_code=404, detail="Артист не найден")

    existing = (
        db.query(Follow)
        .filter(Follow.artist_id == artist_id, Follow.follower_id == current_user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Уже подписан")

    follow = Follow(follower_id=current_user.id, artist_id=artist_id)
    db.add(follow)
    db.commit()
    return {"status": "ok"}


@router.delete("/{artist_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
def unfollow_artist(
    artist_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    follow = (
        db.query(Follow)
        .filter(Follow.artist_id == artist_id, Follow.follower_id == current_user.id)
        .first()
    )
    if not follow:
        raise HTTPException(status_code=404, detail="Вы не подписаны на этого артиста")
    db.delete(follow)
    db.commit()
