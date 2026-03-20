"""
admin_bot/plugins/moderation.py
أوامر الإدارة: حظر، كتم، طرد، رفع/تنزيل مشرف
"""

import asyncio
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions, ChatPrivileges
from admin_bot.helpers import is_admin, get_target_from_reply


def register(app: Client):

    # ─── رفع مشرف ───────────────────────────────────────────────
    @app.on_message(filters.regex(r"^رفع مشرف$") & filters.group)
    async def promote_handler(client, message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply("⚠️ يجب أن تكون مشرفاً!")
        target = await get_target_from_reply(message)
        if not target:
            return await message.reply("⚠️ عليك الرد على رسالة المستخدم!")
        if target.is_bot:
            return await message.reply("❌ لا يمكن رفع البوتات!")
        try:
            await client.promote_chat_member(
                message.chat.id, target.id,
                privileges=ChatPrivileges(
                    can_manage_chat=True, can_delete_messages=True,
                    can_manage_video_chats=True, can_restrict_members=True,
                    can_promote_members=False, can_change_info=True,
                    can_invite_users=True, can_pin_messages=True,
                    is_anonymous=False,
                ),
            )
            await message.reply(
                f"✅ تم رفع [{target.first_name}](tg://user?id={target.id}) إلى مشرف!"
            )
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    # ─── تنزيل مشرف ─────────────────────────────────────────────
    @app.on_message(filters.regex(r"^تنزيل مشرف$") & filters.group)
    async def demote_handler(client, message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply("⚠️ يجب أن تكون مشرفاً!")
        target = await get_target_from_reply(message)
        if not target:
            return await message.reply("⚠️ عليك الرد على رسالة المستخدم!")
        try:
            await client.promote_chat_member(
                message.chat.id, target.id,
                privileges=ChatPrivileges(
                    can_manage_chat=False, can_delete_messages=False,
                    can_manage_video_chats=False, can_restrict_members=False,
                    can_promote_members=False, can_change_info=False,
                    can_invite_users=False, can_pin_messages=False,
                    is_anonymous=False,
                ),
            )
            await message.reply(
                f"✅ تم تنزيل [{target.first_name}](tg://user?id={target.id})!"
            )
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    # ─── حظر ────────────────────────────────────────────────────
    @app.on_message(filters.regex(r"^حظر$") & filters.group)
    async def ban_handler(client, message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply("⚠️ يجب أن تكون مشرفاً!")
        target = await get_target_from_reply(message)
        if not target:
            return await message.reply("⚠️ عليك الرد على رسالة المستخدم!")
        try:
            await client.ban_chat_member(message.chat.id, target.id)
            await message.reply(
                f"🚫 تم حظر [{target.first_name}](tg://user?id={target.id})!"
            )
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    # ─── إلغاء حظر ──────────────────────────────────────────────
    @app.on_message(filters.regex(r"^الغاء حظر$") & filters.group)
    async def unban_handler(client, message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply("⚠️ يجب أن تكون مشرفاً!")
        target = await get_target_from_reply(message)
        if not target:
            return await message.reply("⚠️ عليك الرد على رسالة المستخدم!")
        try:
            await client.unban_chat_member(message.chat.id, target.id)
            await message.reply(
                f"✅ تم إلغاء حظر [{target.first_name}](tg://user?id={target.id})!"
            )
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    # ─── كتم ────────────────────────────────────────────────────
    @app.on_message(filters.regex(r"^كتم$") & filters.group)
    async def mute_handler(client, message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply("⚠️ يجب أن تكون مشرفاً!")
        target = await get_target_from_reply(message)
        if not target:
            return await message.reply("⚠️ عليك الرد على رسالة المستخدم!")
        try:
            await client.restrict_chat_member(
                message.chat.id, target.id,
                permissions=ChatPermissions(can_send_messages=False),
            )
            await message.reply(
                f"🔇 تم كتم [{target.first_name}](tg://user?id={target.id})!"
            )
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    # ─── إلغاء كتم ──────────────────────────────────────────────
    @app.on_message(filters.regex(r"^الغاء كتم$") & filters.group)
    async def unmute_handler(client, message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply("⚠️ يجب أن تكون مشرفاً!")
        target = await get_target_from_reply(message)
        if not target:
            return await message.reply("⚠️ عليك الرد على رسالة المستخدم!")
        try:
            await client.restrict_chat_member(
                message.chat.id, target.id,
                permissions=ChatPermissions(can_send_messages=True),
            )
            await message.reply(
                f"🔊 تم إلغاء كتم [{target.first_name}](tg://user?id={target.id})!"
            )
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    # ─── طرد ────────────────────────────────────────────────────
    @app.on_message(filters.regex(r"^طرد$") & filters.group)
    async def kick_handler(client, message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply("⚠️ يجب أن تكون مشرفاً!")
        target = await get_target_from_reply(message)
        if not target:
            return await message.reply("⚠️ عليك الرد على رسالة المستخدم!")
        try:
            await client.ban_chat_member(message.chat.id, target.id)
            await asyncio.sleep(0.5)
            await client.unban_chat_member(message.chat.id, target.id)
            await message.reply(
                f"👢 تم طرد [{target.first_name}](tg://user?id={target.id})!"
            )
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")
