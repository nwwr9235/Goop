"""
admin_bot/plugins/music_commands.py

أوامر الموسيقى في بوت الإدارة.
لا يشغّل الصوت مباشرة — يرسل الطلب إلى بوت الموسيقى عبر MusicBridge.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
مثال تدفق أمر /تشغيل:

  المستخدم  ──► [Admin Bot]
                    │
                    │  POST /play
                    │  { chat_id, user_id, query }
                    ▼
              [Music Bot API]
                    │
                    ▼
             تشغيل الصوت في Voice Chat
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import re
from pyrogram import Client, filters
from shared.music_bridge import MusicBridge


def register(app: Client):

    # ─── تشغيل ──────────────────────────────────────────────────
    @app.on_message(filters.regex(r"^تشغيل\s+(.+)$", re.DOTALL) & filters.group)
    async def play_handler(client, message):
        match = re.match(r"^تشغيل\s+(.+)$", message.text.strip(), re.DOTALL)
        query = match.group(1).strip()
        msg = await message.reply("🔍 جاري البحث...")

        result = await MusicBridge.play(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            query=query,
        )

        if result.get("ok"):
            title = result.get("title", query)
            pos   = result.get("position", 1)
            if pos == 1:
                await msg.edit(f"🎵 جاري تشغيل: **{title}**")
            else:
                await msg.edit(f"✅ أُضيفت إلى القائمة (#{pos}): **{title}**")
        else:
            err = result.get("error", "خطأ غير معروف")
            await msg.edit(f"❌ فشل التشغيل: {err}")

    # ─── إيقاف ──────────────────────────────────────────────────
    @app.on_message(filters.regex(r"^ايقاف$") & filters.group)
    async def stop_handler(client, message):
        result = await MusicBridge.stop(message.chat.id, message.from_user.id)
        if result.get("ok"):
            await message.reply("⏹️ تم إيقاف التشغيل ومسح القائمة.")
        else:
            await message.reply(f"❌ {result.get('error', 'فشل الإيقاف')}")

    # ─── تخطي ───────────────────────────────────────────────────
    @app.on_message(filters.regex(r"^تخطي$") & filters.group)
    async def skip_handler(client, message):
        result = await MusicBridge.skip(message.chat.id, message.from_user.id)
        if result.get("ok"):
            nxt = result.get("next_title")
            if nxt:
                await message.reply(f"⏭️ تم التخطي — الآن يُشغَّل: **{nxt}**")
            else:
                await message.reply("⏭️ تم التخطي — القائمة فارغة الآن.")
        else:
            await message.reply(f"❌ {result.get('error', 'فشل التخطي')}")

    # ─── إيقاف مؤقت ─────────────────────────────────────────────
    @app.on_message(filters.regex(r"^ايقاف مؤقت$") & filters.group)
    async def pause_handler(client, message):
        result = await MusicBridge.pause(message.chat.id, message.from_user.id)
        if result.get("ok"):
            await message.reply("⏸️ تم الإيقاف المؤقت.")
        else:
            await message.reply(f"❌ {result.get('error', 'فشل')}")

    # ─── استئناف ────────────────────────────────────────────────
    @app.on_message(filters.regex(r"^استئناف$") & filters.group)
    async def resume_handler(client, message):
        result = await MusicBridge.resume(message.chat.id, message.from_user.id)
        if result.get("ok"):
            await message.reply("▶️ تم استئناف التشغيل.")
        else:
            await message.reply(f"❌ {result.get('error', 'فشل')}")

    # ─── القائمة ────────────────────────────────────────────────
    @app.on_message(filters.regex(r"^القائمة$") & filters.group)
    async def queue_handler(client, message):
        result = await MusicBridge.queue(message.chat.id)
        if not result.get("ok"):
            return await message.reply(f"❌ {result.get('error', 'فشل')}")
        items = result.get("queue", [])
        if not items:
            return await message.reply("📭 القائمة فارغة حالياً.")
        text = "🎵 **قائمة الانتظار:**\n\n"
        for i, item in enumerate(items, 1):
            marker = "▶️ " if i == 1 else f"{i}. "
            text += f"{marker}**{item['title']}**\n"
        await message.reply(text)
