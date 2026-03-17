"""
config.py - Bot configuration loaded from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Telegram credentials ──────────────────────────────────────────────────
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")
    API_ID: int = int(os.environ.get("API_ID", 0))
    API_HASH: str = os.environ.get("API_HASH", "")

    # ── Owner / Sudo users ────────────────────────────────────────────────────
    OWNER_ID: int = int(os.environ.get("OWNER_ID", 0))
    SUDO_USERS: list[int] = [
        int(x) for x in os.environ.get("SUDO_USERS", "").split() if x
    ]

    # ── MongoDB ───────────────────────────────────────────────────────────────
    # Railway MongoDB plugin injects MONGO_URL automatically
    MONGO_URI: str = os.environ.get("MONGO_URL") or os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME: str = os.environ.get("DB_NAME", "arabbot")

    # ── Music / Streaming ─────────────────────────────────────────────────────
    MAX_QUEUE_SIZE: int = int(os.environ.get("MAX_QUEUE_SIZE", 50))
    DOWNLOAD_DIR: str = os.environ.get("DOWNLOAD_DIR", "/tmp/arabbot_music")

    # ── Moderation ────────────────────────────────────────────────────────────
    MAX_WARNINGS: int = int(os.environ.get("MAX_WARNINGS", 3))
    WARN_ACTION: str = os.environ.get("WARN_ACTION", "mute")  # "mute" or "ban"

    # ── Misc ──────────────────────────────────────────────────────────────────
    LOG_CHANNEL: int = int(os.environ.get("LOG_CHANNEL", 0))

    @property
    def all_admins(self) -> list[int]:
        return [self.OWNER_ID] + self.SUDO_USERS


config = Config()
