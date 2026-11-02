import mimetypes
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.core.streaming import range_file_response
from app.core.security import decode_access_token
from app.models.user import User
from app.models.track import Track
from app.models.like import Like
from app.schemas.track import TrackOut

router = APIRouter(prefix="/tracks", tags=["tracks"])

ALLOWED_AUDIO_TYPES = {".mp3", ".m4a", ".wav", ".ogg", ".flac"}
ALLOWED_COVER_TYPES = {".jpg", ".jpeg", ".png", ".webp"}


def _ensure_storage_dirs():
    os.makedirs(os.path.join(settings.STORAGE_DIR, "audio"), exist_ok=True)
    os.makedirs(os.path.join(settings.STORAGE_DIR, "covers"), exist_ok=True)


@router.post("/{track_id}/like", status_code=status.HTTP_201_CREATED)
def like_track(track_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):

    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Трек не найден")

    existing = db.query(Like).filter(Like.user_id == current_user.id, Like.track_id == track_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Уже лайкнуто")

    db.add(Like(user_id=current_user.id, track_id=track_id))
    db.commit()
    return {"status": "ok"}


@router.delete("/{track_id}/like", status_code=status.HTTP_204_NO_CONTENT)
def unlike_track(track_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):

    like = db.query(Like).filter(Like.user_id == current_user.id, Like.track_id == track_id).first()
    if not like:
        raise HTTPException(status_code=404, detail="Лайк не найден")
    db.delete(like)
    db.commit()


@router.get("/liked/me", response_model=list[TrackOut])
def my_liked_tracks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):

    liked_rows = db.query(Like.track_id).filter(Like.user_id == current_user.id).all()
    id_list = [row[0] for row in liked_rows]
    if not id_list:
        return []
    return db.query(Track).filter(Track.id.in_(id_list)).order_by(Track.created_at.desc()).all()


@router.get("/search/query", response_model=list[TrackOut])
def search_tracks(q: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not q.strip():
        return []
    like_pattern = f"%{q.strip()}%"
    return (
        db.query(Track)
        .filter((Track.title.ilike(like_pattern)) | (Track.artist.ilike(like_pattern)))
        .limit(30)
        .all()
    )


@router.get("/wave/queue", response_model=list[TrackOut])
def wave_queue(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Волна: сначала треки лайкнутых артистов/похожие по артисту на лайкнутое,
    затем треки от артистов, на которых подписан, затем остальное — перемешанное."""
    import random
    from app.models.follow import Follow

    all_tracks = db.query(Track).all()
    if not all_tracks:
        return []

    liked_track_ids = {
        row[0] for row in db.query(Like.track_id).filter(Like.user_id == current_user.id).all()
    }
    liked_artists = {t.artist for t in all_tracks if t.id in liked_track_ids}

    followed_artist_ids = {
        row[0] for row in db.query(Follow.artist_id).filter(Follow.follower_id == current_user.id).all()
    }

    priority: list[Track] = []
    rest: list[Track] = []

    for t in all_tracks:
        if t.id in liked_track_ids:
            continue  # уже лайкнутое не повторяем в волне
        if t.artist in liked_artists or t.uploaded_by in followed_artist_ids:
            priority.append(t)
        else:
            rest.append(t)

    random.shuffle(priority)
    random.shuffle(rest)
    return priority + rest


@router.get("", response_model=list[TrackOut])
def list_tracks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Track).order_by(Track.created_at.desc()).all()


@router.post("/upload", response_model=TrackOut, status_code=status.HTTP_201_CREATED)
async def upload_track(
    title: str = Form(...),
    artist: str = Form(...),
    album: str | None = Form(None),
    duration_seconds: int = Form(0),
    file: UploadFile = File(...),
    cover: UploadFile | None = File(None),
    lyrics: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_storage_dirs()

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Формат {ext or 'неизвестен'} не поддерживается. Разрешены: {', '.join(sorted(ALLOWED_AUDIO_TYPES))}",
        )

    track_id = uuid.uuid4()
    audio_filename = f"{track_id}{ext}"
    audio_path = os.path.join(settings.STORAGE_DIR, "audio", audio_filename)

    with open(audio_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)

    cover_rel_path = None
    if cover is not None:
        cover_ext = os.path.splitext(cover.filename or "")[1].lower()
        if cover_ext in ALLOWED_COVER_TYPES:
            cover_filename = f"{track_id}{cover_ext}"
            cover_path = os.path.join(settings.STORAGE_DIR, "covers", cover_filename)
            with open(cover_path, "wb") as f:
                while chunk := await cover.read(1024 * 1024):
                    f.write(chunk)
            cover_rel_path = f"covers/{cover_filename}"

    lyrics_text = None
    if lyrics is not None:
        raw = await lyrics.read()
        try:
            lyrics_text = raw.decode("utf-8")
        except UnicodeDecodeError:
            lyrics_text = raw.decode("utf-8", errors="ignore")

    track = Track(
        id=track_id,
        title=title,
        artist=artist,
        album=album,
        duration_seconds=duration_seconds,
        file_path=f"audio/{audio_filename}",
        cover_path=cover_rel_path,
        lyrics_lrc=lyrics_text,
        uploaded_by=current_user.id,
    )
    db.add(track)
    db.commit()
    db.refresh(track)
    return track


@router.get("/{track_id}", response_model=TrackOut)
def get_track(track_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Трек не найден")
    return track


@router.get("/{track_id}/cover")
def get_cover(track_id: uuid.UUID, db: Session = Depends(get_db)):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track or not track.cover_path:
        raise HTTPException(status_code=404, detail="Обложка не найдена")
    full_path = os.path.join(settings.STORAGE_DIR, track.cover_path)
    media_type = mimetypes.guess_type(full_path)[0] or "image/jpeg"
    return FileResponse(full_path, media_type=media_type)


@router.get("/{track_id}/stream")
def stream_track(track_id: uuid.UUID, request: Request, token: str | None = None, db: Session = Depends(get_db)):
    # <audio> в браузере не может слать заголовок Authorization, поэтому здесь
    # дополнительно принимаем токен через query-параметр
    payload = decode_access_token(token) if token else None
    if not payload:
        raise HTTPException(status_code=401, detail="Требуется авторизация")

    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Трек не найден")

    full_path = os.path.join(settings.STORAGE_DIR, track.file_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Файл трека отсутствует на сервере")

    media_type = mimetypes.guess_type(full_path)[0] or "audio/mpeg"
    return range_file_response(full_path, request, media_type=media_type)


@router.patch("/{track_id}", response_model=TrackOut)
async def update_track(
    track_id: uuid.UUID,
    title: str | None = Form(None),
    artist: str | None = Form(None),
    album: str | None = Form(None),
    cover: UploadFile | None = File(None),
    lyrics: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Трек не найден")
    if track.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Можно редактировать только свои треки")

    if title is not None:
        track.title = title
    if artist is not None:
        track.artist = artist
    if album is not None:
        track.album = album

    if cover is not None:
        _ensure_storage_dirs()
        cover_ext = os.path.splitext(cover.filename or "")[1].lower()
        if cover_ext in ALLOWED_COVER_TYPES:
            if track.cover_path:
                old_cover = os.path.join(settings.STORAGE_DIR, track.cover_path)
                if os.path.exists(old_cover):
                    os.remove(old_cover)
            cover_filename = f"{track_id}{cover_ext}"
            cover_path = os.path.join(settings.STORAGE_DIR, "covers", cover_filename)
            with open(cover_path, "wb") as f:
                while chunk := await cover.read(1024 * 1024):
                    f.write(chunk)
            track.cover_path = f"covers/{cover_filename}"

    if lyrics is not None:
        raw = await lyrics.read()
        try:
            track.lyrics_lrc = raw.decode("utf-8")
        except UnicodeDecodeError:
            track.lyrics_lrc = raw.decode("utf-8", errors="ignore")

    db.commit()
    db.refresh(track)
    return track


@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_track(track_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Трек не найден")
    if track.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Можно удалять только свои треки")

    full_path = os.path.join(settings.STORAGE_DIR, track.file_path)
    if os.path.exists(full_path):
        os.remove(full_path)
    if track.cover_path:
        cover_full_path = os.path.join(settings.STORAGE_DIR, track.cover_path)
        if os.path.exists(cover_full_path):
            os.remove(cover_full_path)

    # Убираем все ссылки на трек, иначе удаление упадёт с ошибкой внешнего ключа
    from app.models.playlist import PlaylistTrack

    db.query(Like).filter(Like.track_id == track_id).delete()
    db.query(PlaylistTrack).filter(PlaylistTrack.track_id == track_id).delete()

    db.delete(track)
    db.commit()
