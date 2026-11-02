import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.track import Track
from app.models.playlist import Playlist, PlaylistTrack
from app.schemas.playlist import (
    PlaylistCreate,
    PlaylistOut,
    PlaylistDetailOut,
    AddTrackToPlaylist,
    ReorderTracksRequest,
)

router = APIRouter(prefix="/playlists", tags=["playlists"])


def _generate_share_code() -> str:
    return secrets.token_hex(4).upper()


@router.get("", response_model=list[PlaylistOut])
def list_playlists(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    playlists = (
        db.query(Playlist)
        .filter(Playlist.owner_id == current_user.id)
        .order_by(Playlist.created_at.desc())
        .all()
    )
    result = []
    for p in playlists:
        count = db.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == p.id).count()
        item = PlaylistOut.model_validate(p)
        item.track_count = count
        result.append(item)
    return result


@router.post("", response_model=PlaylistOut, status_code=status.HTTP_201_CREATED)
def create_playlist(
    payload: PlaylistCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    playlist = Playlist(name=payload.name, owner_id=current_user.id, share_code=_generate_share_code())
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    item = PlaylistOut.model_validate(playlist)
    item.track_count = 0
    return item


@router.get("/{playlist_id}", response_model=PlaylistDetailOut)
def get_playlist(
    playlist_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    playlist = (
        db.query(Playlist)
        .options(joinedload(Playlist.tracks).joinedload(PlaylistTrack.track))
        .filter(Playlist.id == playlist_id, Playlist.owner_id == current_user.id)
        .first()
    )
    if not playlist:
        raise HTTPException(status_code=404, detail="Плейлист не найден")

    return PlaylistDetailOut(
        id=playlist.id,
        name=playlist.name,
        owner_id=playlist.owner_id,
        owner_username=current_user.username,
        created_at=playlist.created_at,
        share_code=playlist.share_code,
        tracks=[pt.track for pt in playlist.tracks],
    )


@router.post("/{playlist_id}/tracks", status_code=status.HTTP_201_CREATED)
def add_track(
    playlist_id: uuid.UUID,
    payload: AddTrackToPlaylist,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    playlist = (
        db.query(Playlist).filter(Playlist.id == playlist_id, Playlist.owner_id == current_user.id).first()
    )
    if not playlist:
        raise HTTPException(status_code=404, detail="Плейлист не найден")

    track = db.query(Track).filter(Track.id == payload.track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Трек не найден")

    existing = (
        db.query(PlaylistTrack)
        .filter(PlaylistTrack.playlist_id == playlist_id, PlaylistTrack.track_id == payload.track_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Трек уже в этом плейлисте")

    max_position = (
        db.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == playlist_id).count()
    )
    entry = PlaylistTrack(playlist_id=playlist_id, track_id=payload.track_id, position=max_position)
    db.add(entry)
    db.commit()
    return {"status": "ok"}


@router.delete("/{playlist_id}/tracks/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_track(
    playlist_id: uuid.UUID,
    track_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    playlist = (
        db.query(Playlist).filter(Playlist.id == playlist_id, Playlist.owner_id == current_user.id).first()
    )
    if not playlist:
        raise HTTPException(status_code=404, detail="Плейлист не найден")

    entry = (
        db.query(PlaylistTrack)
        .filter(PlaylistTrack.playlist_id == playlist_id, PlaylistTrack.track_id == track_id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Трека нет в этом плейлисте")

    db.delete(entry)
    db.commit()


@router.patch("/{playlist_id}/reorder", status_code=status.HTTP_200_OK)
def reorder_tracks(
    playlist_id: uuid.UUID,
    payload: ReorderTracksRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    playlist = (
        db.query(Playlist).filter(Playlist.id == playlist_id, Playlist.owner_id == current_user.id).first()
    )
    if not playlist:
        raise HTTPException(status_code=404, detail="Плейлист не найден")

    entries = (
        db.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == playlist_id).all()
    )
    entries_by_track = {e.track_id: e for e in entries}

    if set(payload.track_ids) != set(entries_by_track.keys()):
        raise HTTPException(status_code=400, detail="Список треков не совпадает с содержимым плейлиста")

    for position, track_id in enumerate(payload.track_ids):
        entries_by_track[track_id].position = position

    db.commit()
    return {"status": "ok"}


@router.get("/shared/{share_code}", response_model=PlaylistDetailOut)
def get_shared_playlist(
    share_code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    playlist = (
        db.query(Playlist)
        .options(joinedload(Playlist.tracks).joinedload(PlaylistTrack.track))
        .filter(Playlist.share_code == share_code.strip().upper())
        .first()
    )
    if not playlist:
        raise HTTPException(status_code=404, detail="Плейлист с таким кодом не найден")

    owner = db.query(User).filter(User.id == playlist.owner_id).first()

    return PlaylistDetailOut(
        id=playlist.id,
        name=playlist.name,
        owner_id=playlist.owner_id,
        owner_username=owner.username if owner else None,
        created_at=playlist.created_at,
        share_code=playlist.share_code,
        tracks=[pt.track for pt in playlist.tracks],
    )


@router.post("/shared/{share_code}/import", response_model=PlaylistOut, status_code=status.HTTP_201_CREATED)
def import_shared_playlist(
    share_code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    source = (
        db.query(Playlist)
        .options(joinedload(Playlist.tracks))
        .filter(Playlist.share_code == share_code.strip().upper())
        .first()
    )
    if not source:
        raise HTTPException(status_code=404, detail="Плейлист с таким кодом не найден")

    new_playlist = Playlist(
        name=source.name, owner_id=current_user.id, share_code=_generate_share_code()
    )
    db.add(new_playlist)
    db.commit()
    db.refresh(new_playlist)

    for position, pt in enumerate(sorted(source.tracks, key=lambda x: x.position)):
        db.add(PlaylistTrack(playlist_id=new_playlist.id, track_id=pt.track_id, position=position))
    db.commit()

    item = PlaylistOut.model_validate(new_playlist)
    item.track_count = len(source.tracks)
    return item


@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playlist(
    playlist_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    playlist = (
        db.query(Playlist).filter(Playlist.id == playlist_id, Playlist.owner_id == current_user.id).first()
    )
    if not playlist:
        raise HTTPException(status_code=404, detail="Плейлист не найден")

    db.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == playlist_id).delete()
    db.delete(playlist)
    db.commit()
