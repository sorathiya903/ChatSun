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
