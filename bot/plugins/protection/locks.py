"""
bot/plugins/protection/locks.py
Group protection via content locks.
Enforces: links, usernames, bots, photos, videos, stickers, files, flood, spam.
"""

import re
import time
from pyrogram import Client, filters
from pyrogram.types import Message, ChatPermissions
from pyrogram.enums import MessageEntityType, ChatType
from database import db_client
from utils import is_admin, mention
from utils.arabic_commands import LOCK_MAP, LOCK_NAMES_AR
import logging

logger = logging.getLogger(__name__)

# ── In-memory flood tracker ───────────────────────────────────────────────────
_flood: dict[tuple, list[float]] = {}


def arabic_lock_cmd():
    """Match any lock/unlock command."""
    async def func(flt, client, message: Message):
        if not message.text:
            return False
        txt = message.text.strip()
        return any(txt.startswith(cmd) for cmd in LOCK_MAP.keys())
    return filters.create(func)


@Client.on_message(arabic_lock_cmd() & filters.group)
async def handle_lock(client: Client, message: Message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("❌ هذا الأمر للمشرفين فقط.")

    txt = message.text.strip()
    for cmd, (lock_name, state) in LOCK_MAP.items():
        if txt.startswith(cmd):
            await db_client.set_lock(message.chat.id, lock_name, state)
            status = "🔒 مغلق" if state else "🔓 مفتوح"
            ar_name = LOCK_NAMES_AR.get(lock_name, lock_name)
            await message.reply(f"{status} — **{ar_name}**", parse_mode="markdown")
            return


# ── Message enforcement handler ───────────────────────────────────────────────

@Client.on_message(filters.group & ~filters.service, group=1)
async def enforce_locks(client: Client, message: Message):
    """Check every group message against active locks."""
    if not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    # Admins bypass locks
    if await is_admin(client, chat_id, user_id):
        return

    locks = await db_client.get_locks(chat_id)
    if not locks:
        return

    reason = None

    # ── Links ─────────────────────────────────────────────────────────────────
    if locks.get("links") and message.text:
        url_pattern = re.compile(
            r"(https?://|t\.me/|@[\w]+|www\.)", re.IGNORECASE
        )
        if url_pattern.search(message.text):
            reason = "الروابط"

    # ── Usernames ──────────────────────────────────────────────────────────────
    if not reason and locks.get("usernames") and message.text:
        if re.search(r"@[\w]{4,}", message.text):
            reason = "المعرفات"

    # ── Bots ─────────────────────────────────────────────────────────────────
    if not reason and locks.get("bots") and message.entities:
        for ent in message.entities:
            if ent.type == MessageEntityType.MENTION:
                text_mention = message.text[ent.offset: ent.offset + ent.length]
                try:
                    u = await client.get_users(text_mention)
                    if u.is_bot:
                        reason = "البوتات"
                        break
                except Exception:
                    pass

    # ── Photos ────────────────────────────────────────────────────────────────
    if not reason and locks.get("photos") and message.photo:
        reason = "الصور"

    # ── Videos ───────────────────────────────────────────────────────────────
    if not reason and locks.get("videos") and (message.video or message.video_note):
        reason = "الفيديو"

    # ── Stickers / Animated ───────────────────────────────────────────────────
    if not reason and locks.get("stickers") and message.sticker:
        reason = "الملصقات المتحركة"

    # ── Files ─────────────────────────────────────────────────────────────────
    if not reason and locks.get("files") and message.document:
        reason = "الملفات"

    # ── Flood ─────────────────────────────────────────────────────────────────
    if not reason and locks.get("flood"):
        now = time.monotonic()
        key = (chat_id, user_id)
        times = _flood.get(key, [])
        times = [t for t in times if now - t < 5]
        times.append(now)
        _flood[key] = times
        if len(times) > 5:
            reason = "الإرسال المتكرر"

    # ── Spam (forwarded messages) ─────────────────────────────────────────────
    if not reason and locks.get("spam") and message.forward_date:
        reason = "رسائل المُعاد توجيهها"

    if reason:
        try:
            await message.delete()
            warn_msg = await message.reply(
                f"⚠️ {mention(user_id, message.from_user.first_name)} — "
                f"محظور إرسال **{reason}** في هذه المجموعة.",
                parse_mode="markdown"
            )
            # Auto-delete warning after 5s
            import asyncio
            await asyncio.sleep(5)
            try:
                await warn_msg.delete()
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"Lock enforcement error: {e}")
