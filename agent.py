from fastapi import FastAPI, Depends, HTTPException, status, Security, Request
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from typing import Dict
import logging
from datetime import datetime
import os
import uvicorn
import time
from dotenv import load_dotenv

load_dotenv()

# ---------------- Logging Setup ---------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
)
logger = logging.getLogger("coliving-ai-os")

# ---------------- Security Setup ---------------- #
API_KEY = os.getenv("API_KEY")
API_KEY_NAME = os.getenv("API_KEY_NAME")
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def get_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        logger.warning("Unauthorized access attempt detected.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return api_key

# ---------------- Data Model ---------------- #
class PayloadModel(BaseModel):
    text: str

class UserMessage(BaseModel):
    mid: str
    type: str
    msg_type: str
    sender_id: str
    agent_id: int
    payload: PayloadModel
    content: str
    username: str
    ts: int
    paused_diff_seconds: int
    id: int
    send_At: int
    receive_At: int | None = None
    tsDifference: int | None = None


# ---------------- FastAPI App ---------------- #
app = FastAPI(
    title="Coliving AI OS API",
    description="API for managing raw user messages securely.",
    version="1.0.0",
)

# ---------------- CORS Setup ---------------- #
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Middleware for Latency ---------------- #
latency_stats = {"count": 0, "total_ms": 0.0}

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000
    response.headers["X-Process-Time-ms"] = f"{process_time:.2f}"

    latency_stats["count"] += 1
    latency_stats["total_ms"] += process_time

    logger.info(f"Request {request.url.path} took {process_time:.2f} ms")
    return response


# In-memory storage (replace with DB in production)
db: Dict[int, UserMessage] = {}


# ---------------- Routes ---------------- #
@app.post("/coliving-ai-os/api/raw-user-message", dependencies=[Depends(get_api_key)])
async def post_user_message(message: UserMessage):
    """POST a new user message"""
    message.receive_At = int(time.time() * 1000)  # ms
    message.tsDifference = message.receive_At - message.send_At  # ms
    db[message.id] = message
    logger.info(
        f"Message stored: id={message.id}, sender={message.sender_id}, type={message.type}, latency={message.tsDifference}s"
    )
    return {
        "status": "success",
        "message_id": message.id,
        "stored_at": int(datetime.utcnow().timestamp()),
        "latency_seconds": message.tsDifference,
    }


@app.get("/coliving-ai-os/api/raw-user-message/{message_id}", dependencies=[Depends(get_api_key)])
async def fetch_user_message(message_id: int):
    """GET a user message by ID"""
    if message_id not in db:
        logger.error(f"Message with id={message_id} not found.")
        raise HTTPException(status_code=404, detail="Message not found")
    logger.info(f"Message fetched: id={message_id}")
    return db[message_id]


@app.get("/coliving-ai-os/api/raw-user-message/", dependencies=[Depends(get_api_key)])
async def fetch_messages(skip: int = 0, limit: int = 200):
    """GET paginated messages"""
    messages = list(db.values())
    return messages[skip: skip + limit]


# ---------------- Health Check ---------------- #
@app.get("/coliving-ai-os/api/health")
async def health_check():
    """Check API health and server status"""
    return {
        "status": 1,
        "timestamp": datetime.utcnow(),
        "message_count": len(db),
        "avg_latency_ms": round(latency_stats["total_ms"] / latency_stats["count"], 2) if latency_stats["count"] > 0 else 0
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 4001))
    host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run("agent:app", host=host, port=port, reload=True)


