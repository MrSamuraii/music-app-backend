import uuid

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.deps import get_current_user
from app.core.security import decode_access_token
from app.core.ws_manager import manager
from app.models.user import User
from app.models.friend import FriendRequest
from app.models.message import Message
from app.schemas.message import MessageOut

router = APIRouter(prefix="/chats", tags=["chats"])


def _are_friends(db: Session, user_a: uuid.UUID, user_b: uuid.UUID) -> bool:
    return (
        db.query(FriendRequest)
        .filter(
            or_(
                and_(FriendRequest.from_user_id == user_a, FriendRequest.to_user_id == user_b),
                and_(FriendRequest.from_user_id == user_b, FriendRequest.to_user_id == user_a),
            ),
            FriendRequest.status == "accepted",
        )
        .first()
        is not None
    )


@router.get("/{other_user_id}", response_model=list[MessageOut])
def get_history(
    other_user_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if not _are_friends(db, current_user.id, other_user_id):
        raise HTTPException(status_code=403, detail="Переписка доступна только с друзьями")

    return (
        db.query(Message)
        .filter(
            or_(
                and_(Message.from_user_id == current_user.id, Message.to_user_id == other_user_id),
                and_(Message.from_user_id == other_user_id, Message.to_user_id == current_user.id),
            )
        )
        .order_by(Message.created_at.asc())
        .all()
    )


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket, token: str):
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4401)
        return

    user_id = uuid.UUID(payload["sub"])
    await manager.connect(user_id, websocket)

    db = SessionLocal()
    try:
        while True:
            data = await websocket.receive_json()
            to_user_id = uuid.UUID(data["to_user_id"])
            content = str(data["content"]).strip()

            if not content:
                continue
            if not _are_friends(db, user_id, to_user_id):
                await websocket.send_json({"error": "Переписка доступна только с друзьями"})
                continue

            message = Message(from_user_id=user_id, to_user_id=to_user_id, content=content)
            db.add(message)
            db.commit()
            db.refresh(message)

            payload_out = {
                "id": str(message.id),
                "from_user_id": str(message.from_user_id),
                "to_user_id": str(message.to_user_id),
                "content": message.content,
                "created_at": message.created_at.isoformat(),
            }

            # отправляем и получателю (если онлайн), и обратно отправителю (для синхронизации между вкладками)
            await manager.send_to(to_user_id, payload_out)
            await manager.send_to(user_id, payload_out)
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    finally:
        db.close()
