"""
admin_bot/plugins/warnings.py
نظام الإنذارات الثلاثية
"""

from pyrogram import Client, filters
from admin_bot.helpers import is_admin, get_target_from_reply
from admin_bot.database import get_warnings, add_warning, reset_warnings


def register(app: Client):

    @app.on_message(filters.regex(r"^انذار$") & filters.group)
    async def warn_handler(client, message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply("⚠️ يجب أن تكون مشرفاً!")
        target = await get_target_from_reply(message)
        if not target:
            return await message.reply("⚠️ عليك الرد على رسالة المستخدم!")

        chat_id, user_id = message.chat.id, target.id
        count = add_warning(chat_id, user_id)

        if count >= 3:
            try:
                await client.ban_chat_member(chat_id, user_id)
                reset_warnings(chat_id, user_id)
                await message.reply(
                    f"🚫 تم حظر [{target.first_name}](tg://user?id={user_id}) بعد 3 إنذارات!"
                )
            except Exception as e:
                await message.reply(f"⚠️ 3 إنذارات ولكن فشل الحظر: {e}")
        else:
            await message.reply(
                f"⚠️ إنذار {count}/3 للمستخدم [{target.first_name}](tg://user?id={user_id})"
            )

    @app.on_message(filters.regex(r"^عرض انذارات$") & filters.group)
    async def show_warnings_handler(client, message):
        target = await get_target_from_reply(message) or message.from_user
        count = get_warnings(message.chat.id, target.id)
        await message.reply(
            f"📋 إنذارات [{target.first_name}](tg://user?id={target.id}): {count}/3"
        )

    @app.on_message(filters.regex(r"^مسح انذارات$") & filters.group)
    async def clear_warnings_handler(client, message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply("⚠️ يجب أن تكون مشرفاً!")
        target = await get_target_from_reply(message)
        if not target:
            return await message.reply("⚠️ عليك الرد على رسالة المستخدم!")
        reset_warnings(message.chat.id, target.id)
        await message.reply(
            f"✅ تم مسح إنذارات [{target.first_name}](tg://user?id={target.id})"
        )
