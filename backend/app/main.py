from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import config
from app.api.stream import RateLimiter, run_chat
from app.graph.build import build_graph
from app.memory import store

app = FastAPI(title="AlphaDesk API")
app.add_middleware(CORSMiddleware, allow_origins=config.ALLOWED_ORIGINS, allow_methods=["*"], allow_headers=["*"])
graph = build_graph()
limiter = RateLimiter(config.RATE_LIMIT_PER_HOUR)


class ChatIn(BaseModel):
    user_id: str = Field(min_length=8, max_length=64)
    thread_id: str = Field(min_length=8, max_length=64)
    message: str = Field(min_length=1, max_length=500)


class ProfileIn(BaseModel):
    risk_profile: str


@app.get("/health")
def health():
    return {"status": "ok", "model": config.MODEL_NAME}


@app.post("/chat/stream")
def chat_stream(body: ChatIn, request: Request):
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0].strip()
    if not limiter.allow(ip):
        raise HTTPException(429, "Too many requests. Try again later.")
    return StreamingResponse(
        run_chat(graph, body.user_id, body.thread_id, body.message.strip()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/memory/{user_id}")
def get_memory(user_id: str):
    return {**store.get_profile(user_id), "recent_summaries": store.recent(user_id)}


@app.put("/memory/{user_id}/profile")
def put_profile(user_id: str, body: ProfileIn):
    try:
        store.set_risk(user_id, body.risk_profile)
    except ValueError:
        raise HTTPException(422, "risk_profile must be conservative, balanced or aggressive")
    return store.get_profile(user_id)


@app.delete("/memory/{user_id}")
def delete_memory(user_id: str):
    store.delete_user(user_id)
    return {"deleted": True}
