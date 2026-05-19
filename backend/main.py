from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pymongo import MongoClient
from pydantic import BaseModel
import os
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uuid
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=False,

    allow_methods=["*"],

    allow_headers=["*"],
)

# MongoDB Connection
# Replace with your Atlas URL if env variable is not set
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://<user>:<pass>@cluster.mongodb.net/"
)

client = MongoClient(MONGO_URI)

db = client["chatsun"]

messages = db["messages"]
conversations = db["conversations"]
users = db["users"]

# Active WebSocket connections
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
            raw = await ws.receive_text()
            data = json.loads(raw)
            message = { "message_id": str(uuid.uuid4()), "conversation_id": conversation_id, "sender": data["sender"],  "text": data["text"],  "timestamp": datetime.utcnow().isoformat()}
            messages.insert_one(message)
            
            for conn in connections[conversation_id]:
                await conn.send_text(json.dumps(message))


    except WebSocketDisconnect:
        connections[conversation_id].remove(ws)


@app.get("/users")
async def get_users():

    all_users = users.find()

    return [
        {
            "email": u["email"],
            "user_id": u["user_id"]
        }
        for u in all_users
    ]


class User(BaseModel):
    email: str
    password: str
    user_id: str
    

@app.post("/login")
async def login(user: User):

    # Existing user login
    existing = users.find_one({
        "email": user.email,
        "password": user.password
    })

    if existing:
        return {
            "success": True,
            "user": {
                "email": existing["email"],
                "user_id": existing["user_id"]
            }
        }

    # Email already exists
    email_exists = users.find_one({
        "email": user.email
    })

    if email_exists:
        return {
            "success": False,
            "message": "Wrong password"
        }

    # User ID already taken
    id_exists = users.find_one({
        "user_id": user.user_id
    })

    if id_exists:
        return {
            "success": False,
            "message": "User ID already taken"
        }

    # Register new user
    users.insert_one({
        "email": user.email,
        "password": user.password,
        "user_id": user.user_id
    })

    return {
        "success": True,
        "user": {
            "email": user.email,
            "user_id": user.user_id
        }
    }


@app.get("/search/{user_id}")
async def search_user(user_id: str):

    user = users.find_one({
        "user_id": user_id.lower()
    })

    if not user:
        return {
            "success": False
        }

    return {
        "success": True,
        "user": {
            "email": user["email"],
            "user_id": user["user_id"]
        }
    }

@app.get("/messages/{conversation_id}")
async def get_messages(conversation_id: str):

    msgs = messages.find({
        "conversation_id": conversation_id
    })

    return [
        {
            "message_id": m["message_id"],
            "sender": m["sender"],
            "text": m["text"],
            "timestamp": m["timestamp"]
        }
        for m in msgs
    ]
