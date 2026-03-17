"""
utils/__init__.py
Shared utilities: permission checks, user parsing, formatting.
"""

from pyrogram import Client
from pyrogram.types import Message, ChatMember
from pyrogram.enums import ChatMemberStatus, ChatType
from config import config
import logging
import re
import time

logger = logging.getLogger(__name__)


# ── Permission helpers ────────────────────────────────────────────────────────

async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    """Check if user is admin or creator."""
    if user_id in [config.OWNER_ID] + config.SUDO_USERS:
        return True
    try:
        member: ChatMember = await client.get_chat_member(chat_id, user_id)
        return member.status in (
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        )
    except Exception:
        return False


async def is_owner(user_id: int) -> bool:
    return user_id == config.OWNER_ID


async def get_admin_permissions(client: Client, chat_id: int, user_id: int) -> ChatMember | None:
    try:
        return await client.get_chat_member(chat_id, user_id)
    except Exception:
        return None


async def bot_is_admin(client: Client, chat_id: int) -> bool:
    me = await client.get_me()
    return await is_admin(client, chat_id, me.id)


# ── User parsing ──────────────────────────────────────────────────────────────

async def extract_user(client: Client, message: Message, text: str = None) -> tuple[int | None, str | None]:
    """
    Returns (user_id, first_name) from:
    - replied message
    - @username in text
    - user_id integer in text
    """
    user_id = None
    first_name = None

    # From reply
    if message.reply_to_message and message.reply_to_message.from_user:
        user = message.reply_to_message.from_user
        return user.id, user.first_name

    # From text
    if text:
        # @username
        match = re.search(r"@(\w+)", text)
        if match:
            try:
                user = await client.get_users(match.group(1))
                return user.id, user.first_name
            except Exception:
                return None, None

        # Numeric ID
        match = re.search(r"\b(\d{5,})\b", text)
        if match:
            try:
                user = await client.get_users(int(match.group(1)))
                return user.id, user.first_name
            except Exception:
                return int(match.group(1)), "Unknown"

    return None, None


# ── Formatting helpers ────────────────────────────────────────────────────────

def mention(user_id: int, name: str) -> str:
    return f"[{name}](tg://user?id={user_id})"


def time_to_seconds(time_str: str) -> int | None:
    """Convert time strings like 1h30m, 10m, 300 to seconds."""
    match = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s?)?", time_str.strip())
    if not match:
        return None
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = int(match.group(3) or 0)
    total = h * 3600 + m * 60 + s
    return total if total > 0 else None


def format_duration(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


# ── Command parsing ───────────────────────────────────────────────────────────

def extract_command_args(text: str, command: str) -> str:
    """Remove the command word from the start of the text and return the rest."""
    if text.lower().startswith(command.lower()):
        return text[len(command):].strip()
    return text.strip()


# ── Group type check ──────────────────────────────────────────────────────────

def is_group(message: Message) -> bool:
    return message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)


# ── Anti-flood simple tracker ─────────────────────────────────────────────────

_flood_tracker: dict[tuple, list[float]] = {}

def check_flood(chat_id: int, user_id: int, limit: int = 5, window: int = 5) -> bool:
    """Returns True if user is flooding (exceeded limit messages in window seconds)."""
    key = (chat_id, user_id)
    now = time.monotonic()
    timestamps = _flood_tracker.get(key, [])
    timestamps = [t for t in timestamps if now - t < window]
    timestamps.append(now)
    _flood_tracker[key] = timestamps
    return len(timestamps) > limit
