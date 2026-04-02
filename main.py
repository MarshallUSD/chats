from datetime import datetime
import json

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()


with open("index.html", "r", encoding="utf-8") as f:
    html = f.read()


class RoomPayload(BaseModel):
    name: str


class ConnectionManager:
    def __init__(self):
        self.active: dict[WebSocket, str] = {}

    async def connect(self, ws: WebSocket, username: str):
        await ws.accept()
        self.active[ws] = username

    def disconnect(self, ws: WebSocket) -> str:
        return self.active.pop(ws, "Anonymous")

    async def broadcast(self, message: dict):
        data = json.dumps(message, ensure_ascii=False)
        for ws in list(self.active.keys()):
            try:
                await ws.send_text(data)
            except Exception:
                pass

    def get_users(self) -> list[str]:
        return list(self.active.values())

    def count(self) -> int:
        return len(self.active)


class Room:
    def __init__(self, name: str):
        self.name = name
        self.manager = ConnectionManager()

    def get_users(self) -> list[str]:
        return self.manager.get_users()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "online": self.manager.count(),
            "users": self.get_users(),
        }


rooms: dict[str, Room] = {}


def normalize_room_name(room_name: str) -> str:
    cleaned = " ".join(room_name.strip().split())
    if not cleaned:
        raise HTTPException(status_code=400, detail="Room name is required.")
    return cleaned[:30]


def list_rooms() -> list[dict]:
    return [rooms[name].to_dict() for name in sorted(rooms)]


def get_existing_room(room_name: str) -> Room:
    normalized = normalize_room_name(room_name)
    room = rooms.get(normalized)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found.")
    return room


def create_room(room_name: str) -> Room:
    normalized = normalize_room_name(room_name)
    if normalized in rooms:
        raise HTTPException(status_code=409, detail="Room already exists.")
    room = Room(normalized)
    rooms[normalized] = room
    return room


def system_message(text: str, users: list[str], room_name: str) -> dict:
    return {
        "type": "system",
        "text": text,
        "time": datetime.now().strftime("%H:%M"),
        "room": room_name,
        "users": users,
    }


create_room("general")


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.get("/api/rooms")
async def get_rooms():
    return {"rooms": list_rooms()}


@app.post("/api/rooms", status_code=201)
async def post_room(payload: RoomPayload):
    room = create_room(payload.name)
    return room.to_dict()


@app.delete("/api/rooms/{room_name}")
async def delete_room(room_name: str):
    room = get_existing_room(room_name)
    if room.manager.count() > 0:
        raise HTTPException(status_code=409, detail="Room is not empty.")
    if room.name == "general":
        raise HTTPException(status_code=400, detail="The general room cannot be deleted.")
    rooms.pop(room.name, None)
    return {"deleted": room.name}


@app.websocket("/ws/{room_name}/{username}")
async def websocket_endpoint(ws: WebSocket, room_name: str, username: str):
    try:
        room = get_existing_room(room_name)
    except HTTPException:
        await ws.close(code=4404, reason="Room not found")
        return

    manager = room.manager
    await manager.connect(ws, username)

    await manager.broadcast(
        system_message(f"{username} joined the room", manager.get_users(), room.name)
    )

    await ws.send_text(
        json.dumps(
            {
                **system_message(
                    f"Welcome, {username}! Room: {room.name}",
                    manager.get_users(),
                    room.name,
                ),
                "room_list": list_rooms(),
            },
            ensure_ascii=False,
        )
    )

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)

            await manager.broadcast(
                {
                    "type": "message",
                    "username": username,
                    "text": msg["text"],
                    "time": datetime.now().strftime("%H:%M"),
                    "room": room.name,
                }
            )

    except WebSocketDisconnect:
        name = manager.disconnect(ws)
        await manager.broadcast(
            system_message(f"{name} left the room", manager.get_users(), room.name)
        )
