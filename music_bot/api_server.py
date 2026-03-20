"""
music_bot/api_server.py
خادم FastAPI — يستقبل الأوامر من بوت الإدارة عبر HTTP
"""

import logging
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from shared.config import MusicConfig

logger = logging.getLogger(__name__)

# ─── نماذج البيانات ───────────────────────────────────────────────

class PlayRequest(BaseModel):
    chat_id:  int
    user_id:  int
    query:    str

class ChatRequest(BaseModel):
    chat_id: int
    user_id: int = 0

class QueueRequest(BaseModel):
    chat_id: int


# ─── التحقق من المفتاح السري ─────────────────────────────────────

async def verify_secret(request: Request):
    """رفض أي طلب لا يحمل المفتاح الصحيح"""
    secret = request.headers.get("X-Internal-Secret", "")
    if secret != MusicConfig.INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")


# ─── بناء التطبيق ────────────────────────────────────────────────

def build_app(player) -> FastAPI:
    """
    player: مثيل MusicPlayer يُمرَّر عند إنشاء التطبيق
    """
    app = FastAPI(
        title="Music Bot Internal API",
        docs_url=None,    # إخفاء Swagger في الإنتاج
        redoc_url=None,
    )

    # ── /play ──────────────────────────────────────────────────────
    @app.post("/play", dependencies=[Depends(verify_secret)])
    async def play(body: PlayRequest):
        result = await player.play(body.chat_id, body.query, body.user_id)
        return JSONResponse(result)

    # ── /stop ──────────────────────────────────────────────────────
    @app.post("/stop", dependencies=[Depends(verify_secret)])
    async def stop(body: ChatRequest):
        result = await player.stop(body.chat_id)
        return JSONResponse(result)

    # ── /skip ──────────────────────────────────────────────────────
    @app.post("/skip", dependencies=[Depends(verify_secret)])
    async def skip(body: ChatRequest):
        result = await player.skip(body.chat_id)
        return JSONResponse(result)

    # ── /pause ─────────────────────────────────────────────────────
    @app.post("/pause", dependencies=[Depends(verify_secret)])
    async def pause(body: ChatRequest):
        result = await player.pause(body.chat_id)
        return JSONResponse(result)

    # ── /resume ────────────────────────────────────────────────────
    @app.post("/resume", dependencies=[Depends(verify_secret)])
    async def resume(body: ChatRequest):
        result = await player.resume(body.chat_id)
        return JSONResponse(result)

    # ── /queue ─────────────────────────────────────────────────────
    @app.post("/queue", dependencies=[Depends(verify_secret)])
    async def queue(body: QueueRequest):
        result = player.get_queue(body.chat_id)
        return JSONResponse(result)

    # ── health check ───────────────────────────────────────────────
    @app.get("/health")
    async def health():
        return {"status": "ok", "bot": "music"}

    return app
