from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pymongo import MongoClient

app = FastAPI()

# MongoDB setup
client = MongoClient("mongodb://Aditya:Qu1IZrvVdB0ajaCm@ac-zqtl0lb-shard-00-00.fz0oqsr.mongodb.net:27017,ac-zqtl0lb-shard-00-01.fz0oqsr.mongodb.net:27017,ac-zqtl0lb-shard-00-02.fz0oqsr.mongodb.net:27017/?ssl=true&replicaSet=atlas-10lbo4-shard-0&authSource=admin&appName=Cluster0")
db = client.chatsun
messages = db.messages

# In-memory active connections
connections = {}

@app.websocket("/ws/{conversation_id}")
async def chat(ws: WebSocket, conversation_id: str):

    await ws.accept()

    if conversation_id not in connections:
        connections[conversation_id] = []

    connections[conversation_id].append(ws)

    try:
        while True:
            data = await ws.receive_text()

            # save message in MongoDB
            messages.insert_one({
                "conversation_id": conversation_id,
                "text": data
            })

            # broadcast to same chat
            for conn in connections[conversation_id]:
                await conn.send_text(data)

    except WebSocketDisconnect:
        connections[conversation_id].remove(ws)
