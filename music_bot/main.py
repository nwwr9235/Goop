"""
music_bot/main.py
"""

import asyncio
import logging
import uvicorn
from pyrogram import Client
from pytgcalls import PyTgCalls

from shared.config import MusicConfig
from music_bot.player import MusicPlayer
from music_bot.api_server import build_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    # البوت المساعد
    assistant_client = Client(
        "music_assistant_session",
        api_id=MusicConfig.API_ID,
        api_hash=MusicConfig.API_HASH,
        bot_token=MusicConfig.ASSISTANT_BOT_TOKEN,
    )

    # PyTgCalls
    tgcalls = PyTgCalls(assistant_client)

    # ✅ تمرير assistant_client للـ MusicPlayer
    player = MusicPlayer(tgcalls, assistant_client)

    # FastAPI
    fastapi_app = build_app(player)

    config = uvicorn.Config(
        fastapi_app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        loop="asyncio",
        log_level="info",
    )
    server = uvicorn.Server(config)

    logger.info(f"🎵 Music Bot starting on port {config.port}")

    # تشغيل PyTgCalls أولاً
    await tgcalls.start()
    logger.info("✅ PyTgCalls started")
    
    # تشغيل Uvicorn
    await server.serve()


if __name__ == "__main__":
    import os
    asyncio.run(main())
