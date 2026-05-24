from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body, UploadFile, File, Response, Request, Depends
from pymongo import MongoClient
from pydantic import BaseModel
import os
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime,timedelta, timezone
from zoneinfo import ZoneInfo
import uuid
import json
import re
import time
from fastapi.staticfiles import StaticFiles
from auth import router
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError



ph = PasswordHasher()

app = FastAPI()
app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads"
)
last_seen = {}
app.include_router(router)

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

online_users = set()


# ---------------------------
# WebSocket Chat Route
# ---------------------------




UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):

    ext = file.filename.split(".")[-1]

    filename = f"{uuid.uuid4()}.{ext}"

    path = os.path.join(
        UPLOAD_DIR,
        filename
    )

    with open(path, "wb") as f:
        f.write(await file.read())

    return {
        "url":
        f"https://chatsun-production.up.railway.app/uploads/{filename}",

        "name":
        file.filename
    }

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

            # -------------------------
            # TYPING EVENT
            # -------------------------
            if data.get("type") == "typing":

                for conn in connections.get(
                    conversation_id,
                    []
                ):

                    try:

                        await conn.send_text(
                            json.dumps({
                                "type": "typing",
                                "sender": data["sender"]
                            })
                        )

                    except:
                        pass

                continue

            # -------------------------
            # NORMAL MESSAGE
            # -------------------------
            sender = data["sender"]

            text = data["text"]

            convo = conversations.find_one({
                "conversation_id": conversation_id
            })

            # -------------------------
            # GROUP / PRIVATE RECEIVERS
            # -------------------------
            if convo and convo.get("is_group"):

                receivers = [
                    u for u in convo["users"]
                    if u != sender
                ]

            else:

                users_list = conversation_id.split("_")

                receivers = [
                    u for u in users_list
                    if u != sender
                ]

            # -------------------------
            # CREATE MESSAGE
            # -------------------------
            message = {

                "message_id": str(uuid.uuid4()),

                "conversation_id": conversation_id,

                "sender": sender,

                "text": text,

                "type": data.get(
                    "type",
                    "text"
                ),

                "file_name": data.get(
                    "file_name"
                ),

                "seen_by": [sender],

                "timestamp": datetime.now(
                    ZoneInfo("Asia/Kolkata")
                ).isoformat()
            }

            # -------------------------
            # CREATE CONVERSATION
            # -------------------------
            if not convo:

                users_list = conversation_id.split("_")

                conversations.insert_one({

                    "conversation_id":
                        conversation_id,

                    "users":
                        users_list,

                    "messages":
                        [message],

                    "unread":
                        {
                            u: 0
                            for u in users_list
                        }
                })

            else:

                conversations.update_one(

                    {
                        "conversation_id":
                            conversation_id
                    },

                    {
                        "$push": {
                            "messages": message
                        }
                    }
                )

                # increment unread
                for receiver in receivers:

                    conversations.update_one(

                        {
                            "conversation_id":
                                conversation_id
                        },

                        {
                            "$inc": {
                                f"unread.{receiver}": 1
                            }
                        }
                    )

            # -------------------------
            # BROADCAST MESSAGE
            # -------------------------
            disconnected = []

            for conn in connections.get(
                conversation_id,
                []
            ):

                try:

                    await conn.send_text(
                        json.dumps(message)
                    )

                except:

                    disconnected.append(conn)

            # cleanup dead sockets
            for conn in disconnected:

                if conn in connections.get(
                    conversation_id,
                    []
                ):

                    connections[
                        conversation_id
                    ].remove(conn)

            # -------------------------
            # UNREAD UPDATE
            # -------------------------
            update = {

                "type": "unread_update",

                "conversation_id":
                    conversation_id,

                "receivers":
                    receivers
            }

            for conn in connections.get(
                conversation_id,
                []
            ):

                try:

                    await conn.send_text(
                        json.dumps(update)
                    )

                except:
                    pass

    except WebSocketDisconnect:

        print(
            "WS disconnected:",
            conversation_id
        )

        if ws in connections.get(
            conversation_id,
            []
        ):

            connections[
                conversation_id
            ].remove(ws)

    except Exception as e:

        print("WS ERROR:", e)

        if ws in connections.get(
            conversation_id,
            []
        ):

            connections[
                conversation_id
            ].remove(ws)

            
@app.post("/clear-unread/{conversation_id}/{user_id}")
async def clear_unread(conversation_id: str, user_id: str):

    conversations.update_one(
        {"conversation_id": conversation_id},
        {
            "$set": {
                f"unread.{user_id}": 0
            }
        }
    )

    return {"success": True}



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

@app.get("/conversation/{conversation_id}")
async def get_conversation(conversation_id: str):

    convo = conversations.find_one({
        "conversation_id": conversation_id
    })

    if not convo:
        return {
            "success": False
        }

    return {
        "success": True,

        "conversation_id":
            convo["conversation_id"],

        "is_group":
            convo.get("is_group", False),

        "group_name":
            convo.get("group_name"),

        "members":
            convo.get("users", []),

        "admins":
            convo.get("admins", [])
    }


@app.post("/online/{user_id}")
async def set_online(user_id: str):

    last_seen[user_id] = time.time()

    return {"success": True}


@app.get("/status/{user_id}")
async def get_status(user_id: str):

    online = False

    if user_id in last_seen:

        online = (
            time.time() - last_seen[user_id]
        ) < 30

    return {
        "online": online
    }

@app.post("/offline/{user_id}")
async def set_offline(user_id: str):

    online_users.discard(user_id)

    return {
        "success": True
    }


@app.get("/search/{query}")
async def search_user(query: str):

    query = query.strip()

    user = users.find_one({

        "$or": [

            {
                "user_id":
                    query.lower()
            },

            {
                "phone_number":
                    query
            }
        ]
    })

    if not user:

        return {
            "success": False
        }

    return {

        "success": True,

        "user": {

            "full_name":
                user["full_name"],

            "email":
                user["email"],

            "user_id":
                user["user_id"],

            "profile_picture":
                user.get(
                    "profile_picture",
                    ""
                ),

            "phone_number":
                user.get(
                    "phone_number",
                    ""
                )
        }
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

    conversations = list(
        db.conversations.find({
            "users": user_id
        })
    )

    chats = []

    for convo in conversations:

        messages = convo.get("messages", [])

        last_message = (
            messages[-1]
            if messages
            else None
        )

        # GROUP CHAT
        if convo.get("is_group"):

            chats.append({

                "conversation_id":   convo["conversation_id"],

                "is_group": True,

                "group_name" : convo.get(
                        "group_name",
                        "Group"
                    ),

                "group_avatar": convo.get(
                        "group_avatar"
                    ),

                "members":  convo.get(
                        "users",
                        []
                    ),

                "last_message":   last_message,

                "unread":  convo.get(
                        "unread",
                        {}
                    )
            })

        # PRIVATE CHAT
        else:

            other_user = next(
                (
                    u for u in convo["users"]
                    if u != user_id
                ),
                "Unknown"
            )

            chats.append({

                "conversation_id":  convo["conversation_id"],

                "is_group": False,

                "user_id":other_user,

                "last_message":  last_message,

                "unread":convo.get(
                        "unread",
                        {}
                    )
            })

    chats.sort(

        key=lambda x:

        x["last_message"]["timestamp"]

        if x["last_message"]

        else "",

        reverse=True
    )

    return chats


@app.post("/delivered/{message_id}")
async def mark_delivered(message_id: str):

    convo = conversations.find_one({
        "messages.message_id": message_id
    })

    if not convo:
        return {"success": False}

    conversations.update_one(
        {
            "messages.message_id": message_id
        },
        {
            "$set": {
                "messages.$.status": "delivered"
            }
        }
    )

    update_data = {
        "type": "status_update",
        "message_id": message_id,
        "status": "delivered"
    }

    disconnected = []

    for conn in connections.get(
        convo["conversation_id"],
        []
    ):

        try:

            await conn.send_text(
                json.dumps(update_data)
            )

        except:

            disconnected.append(conn)

    # cleanup dead sockets
    for conn in disconnected:

        if conn in connections[
            convo["conversation_id"]
        ]:

            connections[
                convo["conversation_id"]
            ].remove(conn)

    return {
        "success": True
    }
    
@app.get("/api/unread-count/{conversation_id}/{user_id}")
async def get_unread_count(conversation_id: str, user_id: str):

    chat = conversations.find_one({
        "conversation_id": conversation_id
    })

    if not chat:
        return {"unread_count": 0}

    unread_count = chat.get("unread", {}).get(user_id, 0)

    return {
        "conversation_id": conversation_id,
        "unread_count": unread_count
        }


@app.post("/create-group")
async def create_group(data: dict):

    creator = data["creator"]

    members = list(
        set(
            [creator] + data["members"]
        )
    )

    conversation_id = (
        "grp_" + str(uuid.uuid4())
    )

    group = {

        "conversation_id":
            conversation_id,

        "is_group": True,

        "group_name":
            data["group_name"],

        "group_avatar": "",

        "admins": [creator],

        "users": members,

        "messages": [],

        "created_by": creator
    }

    

    system_message = {
    "message_id": str(uuid.uuid4()),
    "conversation_id": conversation_id,
    "sender": "system",
    "text": f"{creator} added you",
    "type": "system",
    "file_name": None,
    "status": "sent",
    "timestamp": datetime.now(
                    ZoneInfo("Asia/Kolkata")
                ).isoformat()}
    
    group["messages"] = [system_message]

    group["unread"] = {}
    
    for member in members:
        if member != creator:
            group["unread"][member] = 1
        else:
            group["unread"][member] = 0

    conversations.insert_one(group)

    return {
        "success": True,
        "conversation_id":
            conversation_id
    }


@app.post("/read/{message_id}/{user_id}")
async def mark_read(message_id: str, user_id: str):

    convo = conversations.find_one({
        "messages.message_id": message_id
    })

    if not convo:
        return {"success": False}

    message = None

    for msg in convo["messages"]:

        if msg["message_id"] == message_id:
            message = msg
            break

    if not message:
        return {"success": False}

    seen_by = message.get("seen_by", [])

    # avoid duplicates
    if user_id not in seen_by:

        conversations.update_one(
            {
                "messages.message_id": message_id
            },
            {
                "$push": {
                    "messages.$.seen_by": user_id
                }
            }
        )

        seen_by.append(user_id)

    update_data = {
        "type": "seen_update",
        "message_id": message_id,
        "seen_by": seen_by
    }

    disconnected = []

    for conn in connections.get(
        convo["conversation_id"],
        []
    ):

        try:

            await conn.send_text(
                json.dumps(update_data)
            )

        except:
            disconnected.append(conn)

    for conn in disconnected:

        if conn in connections[
            convo["conversation_id"]
        ]:

            connections[
                convo["conversation_id"]
            ].remove(conn)

    return {"success": True}



@app.post("/group/name/{conversation_id}")
async def change_group_name(
    conversation_id: str,
    data: dict
):

    convo = conversations.find_one({
        "conversation_id": conversation_id
    })

    if not convo:
        return {"success": False}

    if data["user_id"] not in convo["admins"]:
        return {"success": False}

    conversations.update_one(
        {"conversation_id": conversation_id},
        {
            "$set": {
                "group_name": data["group_name"]
            }
        }
    )

    return {"success": True}


@app.post("/group/make-admin/{conversation_id}")
async def make_admin(
    conversation_id: str,
    data: dict
):

    convo = conversations.find_one({
        "conversation_id": conversation_id
    })

    if not convo:
        return {"success": False}

    if data["user_id"] not in convo["admins"]:
        return {"success": False}

    conversations.update_one(
        {"conversation_id": conversation_id},
        {
            "$addToSet": {
                "admins": data["member"]
            }
        }
    )

    return {"success": True}


@app.post("/group/remove-admin/{conversation_id}")
async def remove_admin(
    conversation_id: str,
    data: dict
):

    convo = conversations.find_one({
        "conversation_id": conversation_id
    })

    if not convo:
        return {"success": False}

    if data["user_id"] not in convo["admins"]:
        return {"success": False}

    conversations.update_one(
        {"conversation_id": conversation_id},
        {
            "$pull": {
                "admins": data["member"]
            }
        }
    )

    return {"success": True}


@app.post("/group/remove-member/{conversation_id}")
async def remove_member(
    conversation_id: str,
    data: dict
):

    convo = conversations.find_one({
        "conversation_id": conversation_id
    })

    if not convo:
        return {"success": False}

    if data["user_id"] not in convo["admins"]:
        return {"success": False}

    conversations.update_one(
        {"conversation_id": conversation_id},
        {
            "$pull": {
                "users": data["member"],
                "admins": data["member"]
            },

            "$unset": {
                f"unread.{data['member']}": ""
            }
        }
    )

    return {"success": True}


@app.get("/debug-cookies")
async def debug_cookies(request: Request):

    return request.cookies



@app.post("/group/add-member/{conversation_id}")
async def add_member(
    conversation_id: str,
    data: dict
):

    convo = conversations.find_one({
        "conversation_id": conversation_id
    })

    if not convo:
        return {
            "success": False
        }

    if data["user_id"] not in convo["admins"]:
        return {
            "success": False,
            "message": "Only admins can add"
        }

    # check user exists
    user_exists = users.find_one({
        "user_id": data["member"]
    })

    if not user_exists:
        return {
            "success": False,
            "message": "User not found"
        }

    conversations.update_one(
        {
            "conversation_id": conversation_id
        },
        {
            "$addToSet": {
                "users": data["member"]
            },

            "$set": {
                f"unread.{data['member']}": 0
            }
        }
    )

    return {
        "success": True
    }


@app.post("/edit-profile")
async def edit_profile(
    request: Request,
    data: dict
):

    user = get_current_user(request)

    if not user:
        return {
            "success": False
        }

    # user id already taken
    existing = users.find_one({
        "user_id": data["user_id"]
    })

    if (
        existing and
        existing["email"] != user["email"]
    ):

        return {
            "success": False,
            "message":
                "User ID already taken"
        }

    users.update_one(
        {
            "email":
                user["email"]
        },
        {
            "$set": {

                "full_name":
                    data["full_name"],

                "profile_picture":
                    data[
                        "profile_picture"
                    ],

                "user_id":
                    data["user_id"],

                "phone_number":
                    data["phone_number"]
            }
        }
    )

    return {
        "success": True
    }
    
