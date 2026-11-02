import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.friend import FriendRequest
from app.schemas.friend import FriendRequestCreate, FriendRequestOut, UserPublic

router = APIRouter(prefix="/friends", tags=["friends"])


@router.get("/search", response_model=list[UserPublic])
def search_users(q: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not q.strip():
        return []
    return (
        db.query(User)
        .filter(User.username.ilike(f"%{q}%"), User.id != current_user.id)
        .limit(20)
        .all()
    )


@router.post("/requests", response_model=FriendRequestOut, status_code=status.HTTP_201_CREATED)
def send_request(
    payload: FriendRequestCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    target = db.query(User).filter(User.username == payload.username).first()
    if not target:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя добавить самого себя в друзья")

    existing = (
        db.query(FriendRequest)
        .filter(
            or_(
                and_(FriendRequest.from_user_id == current_user.id, FriendRequest.to_user_id == target.id),
                and_(FriendRequest.from_user_id == target.id, FriendRequest.to_user_id == current_user.id),
            ),
            FriendRequest.status.in_(["pending", "accepted"]),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Заявка уже отправлена или вы уже друзья")

    req = FriendRequest(from_user_id=current_user.id, to_user_id=target.id, status="pending")
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get("/requests/incoming", response_model=list[FriendRequestOut])
def incoming_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(FriendRequest)
        .filter(FriendRequest.to_user_id == current_user.id, FriendRequest.status == "pending")
        .all()
    )


@router.get("/requests/outgoing", response_model=list[FriendRequestOut])
def outgoing_requests(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(FriendRequest)
        .filter(FriendRequest.from_user_id == current_user.id, FriendRequest.status == "pending")
        .all()
    )


@router.post("/requests/{request_id}/accept", response_model=FriendRequestOut)
def accept_request(
    request_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    req = (
        db.query(FriendRequest)
        .filter(FriendRequest.id == request_id, FriendRequest.to_user_id == current_user.id)
        .first()
    )
    if not req:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    req.status = "accepted"
    db.commit()
    db.refresh(req)
    return req


@router.post("/requests/{request_id}/reject", response_model=FriendRequestOut)
def reject_request(
    request_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    req = (
        db.query(FriendRequest)
        .filter(FriendRequest.id == request_id, FriendRequest.to_user_id == current_user.id)
        .first()
    )
    if not req:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    req.status = "rejected"
    db.commit()
    db.refresh(req)
    return req


@router.get("", response_model=list[UserPublic])
def list_friends(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    accepted = (
        db.query(FriendRequest)
        .filter(
            or_(FriendRequest.from_user_id == current_user.id, FriendRequest.to_user_id == current_user.id),
            FriendRequest.status == "accepted",
        )
        .all()
    )
    friends = []
    for req in accepted:
        other = req.to_user if req.from_user_id == current_user.id else req.from_user
        friends.append(other)
    return friends


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_friend(
    user_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    req = (
        db.query(FriendRequest)
        .filter(
            or_(
                and_(FriendRequest.from_user_id == current_user.id, FriendRequest.to_user_id == user_id),
                and_(FriendRequest.from_user_id == user_id, FriendRequest.to_user_id == current_user.id),
            ),
            FriendRequest.status == "accepted",
        )
        .first()
    )
    if not req:
        raise HTTPException(status_code=404, detail="Вы не друзья с этим пользователем")
    db.delete(req)
    db.commit()
