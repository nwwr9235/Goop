import logging
from pyrogram import Client
from py_tgcalls import PyTgCalls
from config import config

logger = logging.getLogger(name)

class ArabBot(Client):
def    init(self):
super().init(
name="arabbot",
api_id=config.API_ID,
api_hash=config.API_HASH,
bot_token=config.BOT_TOKEN,
plugins={"root": "bot/plugins"},
sleep_threshold=30,
workers=64,
)

    self.call_py = PyTgCalls(self)

async def start(self):
    await super().start()
    await self.call_py.start()

    me = await self.get_me()
    logger.info(f"Bot running as @{me.username}")

async def stop(self, *args):
    try:
        await self.call_py.stop()
    except Exception:
        pass

    await super().stop()
