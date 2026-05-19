from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pymongo import MongoClient
import os

app = FastAPI()

# 🔗 MongoDB Connection (replace with your Atlas URL)
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://<user>:<pass>@cluster.mongodb.net/")

client = MongoClient(MONGO_URL)
db = client.chatsun

messages = db.messages
conversations = db.conversations
users = db.users

# 🔥 Active WebSocket connections
connections = {}

# ---------------------------
# WebSocket Chat Route
# ---------------------------
@app.websocket("/ws/{conversation_id}")
async def chat(ws: WebSocket, conversation_id: str):

    await ws.accept()

    if conversation_id not in connections:
        connections[conversation_id] = []

    connections[conversation_id].append(ws)

    try:
        while True:
            data = await ws.receive_text()

            # 💾 Save message in MongoDB
            messages.insert_one({
                "conversation_id": conversation_id,
                "text": data
            })

            # 📡 Broadcast to same conversation
            for conn in connections[conversation_id]:
                await conn.send_text(data)

    except WebSocketDisconnect:
        connections[conversation_id].remove(ws)


@app.get("/users")
async def get_users():

    all_users = users.find()

    return [
        {"email": u["email"]}
        for u in all_users
    ]

    from pydantic import BaseModel

class User(BaseModel):
    email: str
    password: str


@app.post("/login")
async def login(user: User):

    existing = users.find_one({
        "email": user.email,
        "password": user.password
    })

    if existing:
        return {
            "success": True,
            "user": {
                "email": existing["email"]
            }
        }

    # register if not exists
    users.insert_one({
        "email": user.email,
        "password": user.password
    })

    return {
        "success": True,
        "user": {"email": user.email}
    }
