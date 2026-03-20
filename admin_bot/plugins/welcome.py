"""
admin_bot/plugins/welcome.py
نظام الترحيب بالأعضاء الجدد
"""

import re
from pyrogram import Client, filters
from admin_bot.helpers import is_admin
from admin_bot.database import get_group_settings


def register(app: Client):

    @app.on_message(filters.new_chat_members & filters.group)
    async def welcome_handler(client, message):
        settings = get_group_settings(message.chat.id)
        if not settings.get("welcome_enabled", True):
            return
        me = await client.get_me()
        for member in message.new_chat_members:
            if member.id == me.id:
                continue
            text = settings["welcome_message"].format(
                user=member.first_name,
                group=message.chat.title,
                username=f"@{member.username}" if member.username else "",
                id=member.id,
            )
            try:
                await message.reply(text)
            except Exception:
                pass

    @app.on_message(filters.regex(r"^تفعيل الترحيب$") & filters.group)
    async def enable_welcome(client, message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply("⚠️ يجب أن تكون مشرفاً!")
        get_group_settings(message.chat.id)["welcome_enabled"] = True
        await message.reply("✅ تم تفعيل الترحيب")

    @app.on_message(filters.regex(r"^تعطيل الترحيب$") & filters.group)
    async def disable_welcome(client, message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply("⚠️ يجب أن تكون مشرفاً!")
        get_group_settings(message.chat.id)["welcome_enabled"] = False
        await message.reply("✅ تم تعطيل الترحيب")

    @app.on_message(filters.regex(r"^تعيين رسالة الترحيب\s+(.+)", re.DOTALL) & filters.group)
    async def set_welcome(client, message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply("⚠️ يجب أن تكون مشرفاً!")
        match = re.match(r"^تعيين رسالة الترحيب\s+(.+)", message.text, re.DOTALL)
        if not match:
            return await message.reply("⚠️ الصيغة:\nتعيين رسالة الترحيب [النص]")
        welcome_msg = match.group(1).strip()
        get_group_settings(message.chat.id)["welcome_message"] = welcome_msg
        await message.reply(f"✅ تم تعيين رسالة الترحيب:\n\n{welcome_msg}")
