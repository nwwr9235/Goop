"""
bot/plugins/owner/owner.py
Owner-only commands: اعادة تشغيل, حالة البوت, سرعة البوت, اذاعة
"""

import os
import sys
import time
import asyncio
import platform
import psutil
from pyrogram import Client, filters
from pyrogram.types import Message
from config import config
from utils.arabic_commands import (
    CMD_RESTART, CMD_BOT_STATUS, CMD_BOT_SPEED, CMD_BROADCAST
)
import logging

logger = logging.getLogger(__name__)

_START_TIME = time.time()


def arabic_cmd(cmd: str):
    async def func(flt, client, message: Message):
        if not message.text:
            return False
        return message.text.strip().startswith(cmd)
    return filters.create(func)


def owner_only():
    async def func(flt, client, message: Message):
        return message.from_user and message.from_user.id in [config.OWNER_ID] + config.SUDO_USERS
    return filters.create(func)


def format_uptime(seconds: float) -> str:
    seconds = int(seconds)
    d, r = divmod(seconds, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    parts = []
    if d: parts.append(f"{d}د")
    if h: parts.append(f"{h}س")
    if m: parts.append(f"{m}ق")
    parts.append(f"{s}ث")
    return " ".join(parts)


# ── اعادة تشغيل ───────────────────────────────────────────────────────────────

@Client.on_message(arabic_cmd(CMD_RESTART) & owner_only())
async def cmd_restart(client: Client, message: Message):
    await message.reply("🔄 جاري إعادة التشغيل...")
    logger.info("Restart requested by owner.")
    await asyncio.sleep(1)
    os.execl(sys.executable, sys.executable, *sys.argv)


# ── حالة البوت ────────────────────────────────────────────────────────────────

@Client.on_message(arabic_cmd(CMD_BOT_STATUS) & owner_only())
async def cmd_bot_status(client: Client, message: Message):
    uptime = time.time() - _START_TIME
    me = await client.get_me()

    try:
        proc = psutil.Process()
        ram_mb = proc.memory_info().rss / 1024 / 1024
        cpu_pct = psutil.cpu_percent(interval=0.5)
        ram_total = psutil.virtual_memory().total / 1024 / 1024 / 1024
        ram_used = psutil.virtual_memory().used / 1024 / 1024 / 1024
    except Exception:
        ram_mb = cpu_pct = ram_total = ram_used = 0

    text = (
        f"📊 **حالة البوت:**\n\n"
        f"🤖 **الاسم:** {me.first_name}\n"
        f"🔢 **ID:** `{me.id}`\n"
        f"⏱ **وقت التشغيل:** {format_uptime(uptime)}\n\n"
        f"💻 **النظام:** {platform.system()} {platform.release()}\n"
        f"🐍 **Python:** {platform.python_version()}\n\n"
        f"🧠 **RAM البوت:** {ram_mb:.1f} MB\n"
        f"💾 **RAM الكلي:** {ram_used:.2f} / {ram_total:.2f} GB\n"
        f"⚡ **CPU:** {cpu_pct:.1f}%"
    )

    await message.reply(text, parse_mode="markdown")


# ── سرعة البوت ────────────────────────────────────────────────────────────────

@Client.on_message(arabic_cmd(CMD_BOT_SPEED) & owner_only())
async def cmd_bot_speed(client: Client, message: Message):
    start = time.monotonic()
    msg = await message.reply("⚡ جاري قياس السرعة...")
    latency = (time.monotonic() - start) * 1000
    await msg.edit(
        f"⚡ **سرعة البوت:**\n\n"
        f"📡 **Ping:** `{latency:.2f}` ms",
        parse_mode="markdown"
    )


# ── اذاعة ─────────────────────────────────────────────────────────────────────

@Client.on_message(arabic_cmd(CMD_BROADCAST) & owner_only())
async def cmd_broadcast(client: Client, message: Message):
    text = message.text.strip()[len(CMD_BROADCAST):].strip()

    if not text:
        return await message.reply(
            "❗ يرجى كتابة رسالة الإذاعة.\nمثال: `اذاعة مرحباً بالجميع!`",
            parse_mode="markdown"
        )

    status_msg = await message.reply("📡 جاري إرسال الإذاعة...")

    sent = failed = 0

    async for dialog in client.get_dialogs():
        from pyrogram.enums import ChatType
        if dialog.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
            try:
                await client.send_message(dialog.chat.id, text)
                sent += 1
                await asyncio.sleep(0.3)  # Rate limit protection
            except Exception as e:
                logger.debug(f"Broadcast failed to {dialog.chat.id}: {e}")
                failed += 1

    await status_msg.edit(
        f"✅ **تمت الإذاعة:**\n\n"
        f"✔️ تم الإرسال: {sent} مجموعة\n"
        f"❌ فشل: {failed} مجموعة",
        parse_mode="markdown"
    )
