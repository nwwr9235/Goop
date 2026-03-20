"""
admin_bot/plugins/auto_replies.py
نظام الردود التلقائية
"""

import re
from pyrogram import Client, filters
from admin_bot.helpers import is_admin
from admin_bot.database import get_replies, add_reply, delete_reply

# الأوامر التي لا يُراد الرد عليها تلقائياً
_SKIP_PREFIXES = [
    "رفع مشرف", "تنزيل مشرف", "حظر", "الغاء حظر",
    "كتم", "الغاء كتم", "طرد", "انذار",
    "عرض انذارات", "مسح انذارات",
    "اضافة رد", "حذف رد", "عرض الردود",
    "تفعيل الترحيب", "تعطيل الترحيب", "تعيين رسالة الترحيب",
    "قفل", "فتح", "ا", "اا", "افتاره",
    "تشغيل", "ايقاف", "تخطي", "ايقاف مؤقت", "استئناف", "القائمة",
    "مساعدة", "الاوامر",
]


def register(app: Client):

    @app.on_message(filters.regex(r"^اضافة رد\s+(.+?)\s*=\s*(.+)", re.DOTALL) & filters.group)
    async def add_reply_handler(client, message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply("⚠️ يجب أن تكون مشرفاً!")
        match = re.match(r"^اضافة رد\s+(.+?)\s*=\s*(.+)", message.text, re.DOTALL)
        if not match:
            return await message.reply("⚠️ الصيغة:\nاضافة رد كلمة = الرد")
        trigger, response = match.group(1).strip(), match.group(2).strip()
        if not trigger or not response:
            return await message.reply("⚠️ الكلمة والرد لا يمكن أن يكونا فارغين!")
        add_reply(message.chat.id, trigger, response)
        await message.reply(f"✅ تم إضافة الرد:\n🔹 الكلمة: `{trigger}`\n🔸 الرد: {response}")

    @app.on_message(filters.regex(r"^حذف رد\s+(.+)") & filters.group)
    async def delete_reply_handler(client, message):
        if not await is_admin(client, message.chat.id, message.from_user.id):
            return await message.reply("⚠️ يجب أن تكون مشرفاً!")
        match = re.match(r"^حذف رد\s+(.+)", message.text)
        trigger = match.group(1).strip()
        if delete_reply(message.chat.id, trigger):
            await message.reply(f"✅ تم حذف رد: `{trigger}`")
        else:
            await message.reply(f"❌ الرد `{trigger}` غير موجود")

    @app.on_message(filters.regex(r"^عرض الردود$") & filters.group)
    async def show_replies_handler(client, message):
        replies = get_replies(message.chat.id)
        if not replies:
            return await message.reply("📭 لا توجد ردود مسجلة في هذه المجموعة")
        text = "📋 قائمة الردود:\n\n"
        for t, r in replies.items():
            text += f"🔹 `{t}` ← {r}\n"
        await message.reply(text)

    @app.on_message(filters.text & filters.group, group=1)
    async def auto_reply_trigger(client, message):
        if not message.text or not message.from_user or message.from_user.is_bot:
            return
        lower = message.text.strip().lower()
        for prefix in _SKIP_PREFIXES:
            if lower.startswith(prefix.lower()):
                return
        replies = get_replies(message.chat.id)
        for trigger, response in replies.items():
            if trigger in lower:
                try:
                    await message.reply(response)
                except Exception:
                    pass
                return
