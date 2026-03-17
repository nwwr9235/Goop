"""
ArabBot - Arabic Telegram Supergroup Bot
Combines moderation, protection, welcome, auto-replies, and music player.
Railway.app compatible deployment.
"""

import asyncio
import logging
import os
from pyrogram import idle
from bot import ArabBot
from database import db_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
# Reduce noise from libraries
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pytgcalls").setLevel(logging.WARNING)
logging.getLogger("motor").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Ensure music temp dir exists (Railway uses ephemeral filesystem)
os.makedirs(os.environ.get("DOWNLOAD_DIR", "/tmp/arabbot_music"), exist_ok=True)


async def main():
    logger.info("🤖 ArabBot is starting...")

    await db_client.connect()

    async with ArabBot() as bot:
        logger.info("✅ Bot is online and ready.")
        await idle()

    await db_client.disconnect()
    logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
