"""
music_bot/main.py
نقطة انطلاق بوت الموسيقى - محسّن لـ Railway
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
    # ─── 1. البوت المساعد ───────────────────────────
    assistant_client = Client(
        "music_assistant_session",
        api_id=MusicConfig.API_ID,
        api_hash=MusicConfig.API_HASH,
        bot_token=MusicConfig.ASSISTANT_BOT_TOKEN,
    )

    # ─── 2. PyTgCalls ─────────────────────────────────
    tgcalls = PyTgCalls(assistant_client)

    # ─── 3. MusicPlayer ─────────────────────────────────
    player = MusicPlayer(tgcalls, assistant_client)

    # ─── 4. FastAPI ─────────────────────────────────────
    fastapi_app = build_app(player)

    # ✅ إعدادات محسّنة لـ Railway
    config = uvicorn.Config(
        fastapi_app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),  # Railway يستخدم PORT
        loop="asyncio",
        log_level="info",  # تغيير لرؤية المزيد من التفاصيل
        # ✅ إضافات مهمة لـ Railway
        proxy_headers=True,
        forwarded_allow_ips="*",  # السماح بجميع الـ IPs
    )
    server = uvicorn.Server(config)

    logger.info(f"🎵 بوت الموسيقى يعمل | API port: {config.port}")
    logger.info("🤖 جاري بدء البوت...")

    # ✅ ترتيب صحيح: PyTgCalls أولاً ثم Uvicorn
    await tgcalls.start()
    logger.info("✅ PyTgCalls started")
    
    # تشغيل Uvicorn
    await server.serve()


if __name__ == "__main__":
    import os  # نقل الاستيراد هنا
    asyncio.run(main())
