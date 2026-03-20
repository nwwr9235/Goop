"""
music_bot/main.py
نقطة انطلاق بوت الموسيقى

يشغّل ثلاثة أشياء معاً في نفس العملية:
  1. Pyrogram Client  (للانضمام إلى Voice Chat)
  2. PyTgCalls        (محرك الصوت)
  3. FastAPI + Uvicorn (خادم API الداخلي)
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
    # ─── 1. Pyrogram Client ──────────────────────────────────────
    pyrogram_client = Client(
        "music_bot_session",
        api_id=MusicConfig.API_ID,
        api_hash=MusicConfig.API_HASH,
        bot_token=MusicConfig.BOT_TOKEN,
    )

    # ─── 2. PyTgCalls ────────────────────────────────────────────
    tgcalls = PyTgCalls(pyrogram_client)

    # ─── 3. MusicPlayer ─────────────────────────────────────────
    player = MusicPlayer(tgcalls)

    # ─── 4. FastAPI ──────────────────────────────────────────────
    fastapi_app = build_app(player)

    config = uvicorn.Config(
        fastapi_app,
        host="0.0.0.0",
        port=MusicConfig.API_PORT,
        loop="asyncio",
        log_level="warning",
    )
    server = uvicorn.Server(config)

    # ─── تشغيل الكل معاً ─────────────────────────────────────────
    logger.info(f"🎵 بوت الموسيقى يعمل | API port: {MusicConfig.API_PORT}")
    await asyncio.gather(
        pyrogram_client.start(),
        tgcalls.start(),
        server.serve(),
    )


if __name__ == "__main__":
    asyncio.run(main())
