"""
admin_bot/plugins/protection.py
نظام الحماية: قفل/فتح أنواع المحتوى
"""

import re
from pyrogram import Client, filters
from admin_bot.helpers import is_admin
from admin_bot.database import get_group_settings

LOCK_TYPES = {
    "الروابط":   "links",
    "التكرار":   "flood",
    "السبام":    "spam",
    "البوتات":   "bots",
    "الصور":     "photos",
    "الفيديو":   "videos",
    "الملفات":   "files",
    "الملصقات":  "stickers",
    "الصوتيات":  "voices",
}


def register(app: Client):

    # ─── قفل ────────────────────────────────────────────────────
    @app.on_message(filters.regex(r"^قفل\s+(.+)$") & filters.group)
    async def lock_handler(client, message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply("⚠️ يجب أن تكون مشرفاً!")
        match = re.match(r"^قفل\s+(.+)$", message.text)
        lock_type = match.group(1).strip()
        if lock_type not in LOCK_TYPES:
            types_list = "\n".join(f"• {k}" for k in LOCK_TYPES)
            return await message.reply(f"❌ الأنواع المتاحة:\n{types_list}")
        get_group_settings(message.chat.id)["locks"][LOCK_TYPES[lock_type]] = True
        await message.reply(f"🔒 تم قفل {lock_type}")

    # ─── فتح ────────────────────────────────────────────────────
    @app.on_message(filters.regex(r"^فتح\s+(.+)$") & filters.group)
    async def unlock_handler(client, message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply("⚠️ يجب أن تكون مشرفاً!")
        match = re.match(r"^فتح\s+(.+)$", message.text)
        lock_type = match.group(1).strip()
        if lock_type not in LOCK_TYPES:
            types_list = "\n".join(f"• {k}" for k in LOCK_TYPES)
            return await message.reply(f"❌ الأنواع المتاحة:\n{types_list}")
        get_group_settings(message.chat.id)["locks"][LOCK_TYPES[lock_type]] = False
        await message.reply(f"🔓 تم فتح {lock_type}")

    # ─── تطبيق الحماية على كل رسالة ────────────────────────────
    @app.on_message(filters.all & filters.group, group=2)
    async def protection_handler(client, message):
        if not message.from_user:
            return
        try:
            member = await client.get_chat_member(message.chat.id, message.from_user.id)
            if member.status in ["administrator", "creator"]:
                return
        except Exception:
            return

        locks = get_group_settings(message.chat.id).get("locks", {})

        checks = [
            ("links",    message.text and (
                "http" in message.text or "www" in message.text or "t.me" in message.text
            ), "الروابط"),
            ("photos",   bool(message.photo),    "الصور"),
            ("videos",   bool(message.video),    "الفيديو"),
            ("files",    bool(message.document), "الملفات"),
            ("stickers", bool(message.sticker),  "الملصقات"),
            ("voices",   bool(message.voice or message.audio), "الصوتيات"),
        ]

        for key, condition, label in checks:
            if locks.get(key) and condition:
                try:
                    await message.delete()
                    await message.reply(
                        f"⚠️ {message.from_user.first_name}، {label} ممنوعة!"
                    )
                except Exception:
                    pass
                return
