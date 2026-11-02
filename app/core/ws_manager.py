import uuid

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active: dict[uuid.UUID, WebSocket] = {}

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket):
        await websocket.accept()
        self.active[user_id] = websocket

    def disconnect(self, user_id: uuid.UUID):
        self.active.pop(user_id, None)

    async def send_to(self, user_id: uuid.UUID, payload: dict):
        ws = self.active.get(user_id)
        if ws:
            await ws.send_json(payload)

    def is_online(self, user_id: uuid.UUID) -> bool:
        return user_id in self.active


manager = ConnectionManager()
