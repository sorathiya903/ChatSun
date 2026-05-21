from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from pymongo import MongoClient
from pydantic import BaseModel
import os
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid
import json
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "https://chatsun.netlify.app"
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)

# MongoDB Connection
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
            # typing event
            if data.get("type") == "typing":
                for conn in connections[conversation_id]:
                    await conn.send_text(json.dumps({ "type": "typing", "sender": data["sender"]  }))
                    
                continue

# normal message
            message = {
                "message_id": str(uuid.uuid4()),
                "conversation_id": conversation_id,
                "sender": data["sender"],
                "text": data["text"],
                "timestamp": datetime.now(  ZoneInfo("Asia/Kolkata")  ).isoformat()
          
            }

            

            # find conversation
            convo = conversations.find_one({
                "conversation_id": conversation_id
            })

            # create if not exists
            if not convo:

                conversations.insert_one({

                    "conversation_id":
                        conversation_id,

                    "users":
                        conversation_id.split("_"),

                    "messages":
                        [message]
                })

            else:

                conversations.update_one(
                    {
                        "conversation_id":
                            conversation_id
                    },
                    {
                        "$push": {
                            "messages":
                                message
                        }
                    }
                )

            disconnected = []

            # send to all sockets
            for conn in connections[conversation_id]:

                try:

                    await conn.send_text(
                        json.dumps(message)
                    )

                except:

                    disconnected.append(conn)

            # cleanup
            for conn in disconnected:

                if conn in connections[conversation_id]:

                    connections[conversation_id].remove(conn)

    except WebSocketDisconnect:

        if ws in connections[conversation_id]:

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



@app.get("/status/{user_id}")
async def get_status(user_id: str):

    return {
        "online": user_id in online_users
    }

@app.post("/online/{user_id}")
async def set_online(user_id: str):

    online_users.add(user_id)

    return {
        "success": True
    }

@app.post("/offline/{user_id}")
async def set_offline(user_id: str):

    online_users.discard(user_id)

    return {
        "success": True
    }

# -----------------------------
# MODELS
# -----------------------------

class RegisterModel(BaseModel):
    full_name: str
    email: str
    password: str
    user_id: str

class LoginModel(BaseModel):
    email: str
    password: str

# -----------------------------
# VALIDATION
# -----------------------------

def validate_email(email):

    pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"

    return re.match(pattern, email)

def validate_user_id(user_id):

    pattern = r"^[a-z0-9_]{3,20}$"

    return re.match(pattern, user_id)

# -----------------------------
# REGISTER
# -----------------------------

@app.post("/register")
async def register(data: RegisterModel):

    full_name = data.full_name.strip()

    email = data.email.strip().lower()

    password = data.password.strip()

    user_id = data.user_id.strip().lower()

    # -----------------------------
    # SECURITY CHECKS
    # -----------------------------

    if (
        not full_name or
        not email or
        not password or
        not user_id
    ):
        return {
            "success": False,
            "message": "All fields required"
        }

    if len(full_name) < 2:
        return {
            "success": False,
            "message": "Invalid full name"
        }

    if not validate_email(email):
        return {
            "success": False,
            "message": "Invalid email"
        }

    if not validate_user_id(user_id):
        return {
            "success": False,
            "message":
            "User ID must contain only lowercase letters, numbers and underscore"
        }

    if len(password) < 6:
        return {
            "success": False,
            "message":
            "Password must be at least 6 characters"
        }

    # -----------------------------
    # CHECK EXISTING
    # -----------------------------

    email_exists = users.find_one({
        "email": email
    })

    if email_exists:
        return {
            "success": False,
            "message": "Email already exists"
        }

    id_exists = users.find_one({
        "user_id": user_id
    })

    if id_exists:
        return {
            "success": False,
            "message": "User ID already taken"
        }

    # -----------------------------
    # CREATE USER
    # -----------------------------

    users.insert_one({
        "full_name": full_name,
        "email": email,
        "password": password,
        "user_id": user_id
    })

    return {
        "success": True,
        "user": {
            "full_name": full_name,
            "email": email,
            "user_id": user_id
        }
    }

# -----------------------------
# LOGIN
# -----------------------------

@app.post("/login")
async def login(data: LoginModel):

    email = data.email.strip().lower()

    password = data.password.strip()

    # -----------------------------
    # SECURITY CHECKS
    # -----------------------------

    if not email or not password:
        return {
            "success": False,
            "message": "All fields required"
        }

    if not validate_email(email):
        return {
            "success": False,
            "message": "Invalid email"
        }

    if len(password) < 6:
        return {
            "success": False,
            "message": "Invalid password"
        }

    # -----------------------------
    # FIND USER
    # -----------------------------

    user = users.find_one({
        "email": email,
        "password": password
    })

    if not user:
        return {
            "success": False,
            "message": "Wrong email or password"
        }

    return {
        "success": True,
        "user": {
            "full_name": user["full_name"],
            "email": user["email"],
            "user_id": user["user_id"]
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

    convo = conversations.find_one({
        "conversation_id": conversation_id
    })

    if not convo:

        return []

    return convo["messages"]


@app.put("/message/{message_id}")
async def edit_message(message_id: str, data: dict = Body(...)):

    result = conversations.update_one(
        {"messages.message_id": message_id},
        {
            "$set": {
                "messages.$.text": data["text"]
            }
        }
    )

    if result.modified_count == 0:
        return {"success": False}

    return {"success": True}

@app.delete("/message/{message_id}")
async def delete_message(message_id: str):

    result = conversations.update_one(
        {"messages.message_id": message_id},
        {"$pull": {"messages": {"message_id": message_id}}}
    )

    if result.modified_count == 0:
        return {"success": False}

    return {"success": True}

@app.get("/chats/{user_id}")
async def get_chats(user_id: str):

    all_conversations = conversations.find({
        "users": user_id
    })

    result = []

    for convo in all_conversations:

        other_user = next(
            u for u in convo["users"]
            if u != user_id
        )

        last_message = None

        if convo["messages"]:

            last_message = convo["messages"][-1]

        result.append({

            "conversation_id":convo["conversation_id"],

            "user_id":other_user,

            "last_message": last_message
        })

    return result
