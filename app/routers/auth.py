import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.models.track import Track
from app.schemas.user import (
    UserRegister,
    GoogleAuthRequest,
    UserLogin,
    UserOut,
    Token,
    PinTrackRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    existing = (
        db.query(User)
        .filter((User.email == payload.email) | (User.username == payload.username))
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email или username уже существует",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        auth_provider="local",
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=token)


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or user.auth_provider != "local" or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )
    token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=token)


@router.post("/google", response_model=Token)
def google_login(payload: GoogleAuthRequest, db: Session = Depends(get_db)):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Вход через Google не настроен на сервере (нет GOOGLE_CLIENT_ID/SECRET в .env)",
        )

    # Меняем код авторизации от Google на токены
    token_res = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": payload.code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": payload.redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    if token_res.status_code != 200:
        raise HTTPException(status_code=400, detail="Не удалось подтвердить код Google")

    tokens = token_res.json()
    id_token_str = tokens.get("id_token")
    if not id_token_str:
        raise HTTPException(status_code=400, detail="Google не вернул id_token")

    try:
        idinfo = google_id_token.verify_oauth2_token(
            id_token_str, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Не удалось проверить токен Google")

    google_id = idinfo["sub"]
    email = idinfo.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google-аккаунт без email")

    user = db.query(User).filter(User.google_id == google_id).first()
    if not user:
        # Возможно, юзер уже регистрировался локально с тем же email — привязываем аккаунт
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.google_id = google_id
            user.auth_provider = "google"
            user.is_verified = True
        else:
            base_username = email.split("@")[0]
            username = base_username
            suffix = 1
            while db.query(User).filter(User.username == username).first():
                suffix += 1
                username = f"{base_username}{suffix}"

            user = User(
                email=email,
                username=username,
                hashed_password=None,
                google_id=google_id,
                auth_provider="google",
                is_verified=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/me/pinned-track", response_model=UserOut)
def pin_track(
    payload: PinTrackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    track = db.query(Track).filter(Track.id == payload.track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Трек не найден")

    current_user.pinned_track_id = payload.track_id
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me/pinned-track", response_model=UserOut)
def unpin_track(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.pinned_track_id = None
    db.commit()
    db.refresh(current_user)
    return current_user
