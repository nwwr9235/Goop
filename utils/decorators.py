# utils/decorators.py
from functools import wraps
from pyrogram.types import ChatPermissions
from typing import Callable, Optional

def is_admin(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        # Check if user is admin
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        # Get chat member info
        chat_member = await client.get_chat_member(chat_id, user_id)
        
        if chat_member.status in ["administrator", "creator"] or user_id in [123456789]:  # Replace with actual admin check
            return await func(client, message, *args, **kwargs)
        else:
            await message.reply("⚠️ يجب أن تكون مسؤولاً لاستخدام هذا الأمر!")
    
    return wrapper

def is_sudo(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        # Check if user is sudo
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        # Replace with actual sudo check
        sudo_users = [123456789]  # Replace with actual sudo check
        
        if user_id in sudo_users:
            return await func(client, message, *args, **kwargs)
        else:
            await message.reply("⚠️ هذا الأمر متاح فقط للمطور!")
    
    return wrapper

def check_flood(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        # Check flood
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        # Implement flood check logic here
        # This is a placeholder
        return await func(client, message, *args, **kwargs)
    
    return wrapper

