# plugins/admin/admin.py
import re
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions
from database.models import User
from utils.decorators import is_admin

# Command patterns
PROMOTE_PATTERN = re.compile(r'رفع\s+@(\w+)')
DEMOTE_PATTERN = re.compile(r'تنزيل\s+@(\w+)')
BAN_PATTERN = re.compile(r'حظر\s+@(\w+)')
UNBAN_PATTERN = re.compile(r'الغاء\s+الحظر\s+@(\w+)')
MUTE_PATTERN = re.compile(r'كتم\s+@(\w+)')
UNMUTE_PATTERN = re.compile(r'الغاء\s+الكتم\s+@(\w+)')
KICK_PATTERN = re.compile(r'طرد\s+@(\w+)')

@app.on_message(filters.regex(r'^رفع\s+@(\w+)') & filters.group)
@is_admin
async def promote_handler(client, message):
    # Extract username from message
    username = message.matches[0].group(1)
    
    # Get user info
    user = await client.get_chat_member(message.chat.id, username)
    
    if user:
        # Promote user
        await client.promote_chat_member(
            chat_id=message.chat.id,
            user_id=user.user.id,
            privileges=ChatPermissions(
                can_change_info=True,
                can_delete_messages=True,
                can_restrict_members=True,
                can_pin_messages=True,
                can_promote_members=True,
                can_manage_chat=True,
                can_invite_users=True,
                can_post_messages=True,
                can_edit_messages=True
            )
        )
        
        await message.reply(f"✅ تم رفع @{username} إلى رتبة أعلى بنجاح!")
    else:
        await message.reply("⚠️ لم يتم العثور على المستخدم!")

@app.on_message(filters.regex(r'^تنزيل\s+@(\w+)') & filters.group)
@is_admin
async def demote_handler(client, message):
    # Similar logic for demote
    username = message.matches[0].group(1)
    
    user = await client.get_chat_member(message.chat.id, username)
    
    if user:
        # Demote user
        await client.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=user.user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False
            )
        )
        
        await message.reply(f"✅ تم تنزيل @{username} من رتبته بنجاح!")

@app.on_message(filters.regex(r'^حظر\s+@(\w+)') & filters.group)
@is_admin
async def ban_handler(client, message):
    username = message.matches[0].group(1)
    
    user = await client.get_chat_member(message.chat.id, username)
    
    if user:
        await client.ban_chat_member(message.chat.id, user.user.id)
        await message.reply(f"✅ تم حظر @{username} بنجاح!")

@app.on_message(filters.regex(r'^الغاء\s+الحظر\s+@(\w+)') & filters.group)
@is_admin
async def unban_handler(client, message):
    username = message.matches[0].group(1)
    
    user = await client.get_chat_member(message.chat.id, username)
    
    if user:
        await client.unban_chat_member(message.chat.id, user.user.id)
        await message.reply(f"✅ تم إلغاء حظر @{username} بنجاح!")

@app.on_message(filters.regex(r'^كتم\s+@(\w+)') & filters.group)
@is_admin
async def mute_handler(client, message):
    username = message.matches[0].group(1)
    
    user = await client.get_chat_member(message.chat.id, username)
    
    if user:
        await client.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=user.user.id,
            permissions=ChatPermissions(
                can_send_messages=False
            )
        )
        await message.reply(f"✅ تم كتم @{username} بنجاح!")

@app.on_message(filters.regex(r'^الغاء\s+الكتم\s+@(\w+)') & filters.group)
@is_admin
async def unmute_handler(client, message):
    username = message.matches[0].group(1)
    
    user = await client.get_chat_member(message.chat.id, username)
    
    if user:
        await client.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=user.user.id,
            permissions=ChatPermissions(
                can_send_messages=True
            )
        )
        await message.reply(f"✅ تم إلغاء كتم @{username} بنجاح!")

@app.on_message(filters.regex(r'^طرد\s+@(\w+)') & filters.group)
@is_admin
async def kick_handler(client, message):
    username = message.matches[0].group(1)
    
    user = await client.get_chat_member(message.chat.id, username)
    
    if user:
        await client.ban_chat_member(message.chat.id, user.user.id)
        await message.reply(f"✅ تم طرد @{username} بنجاح!")
        
        # Unban after kick (so they can rejoin)
        await client.unban_chat_member(message.chat.id, user.user.id)
