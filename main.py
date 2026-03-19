# main.py
import logging
import asyncio
from pyrogram import Client, filters, types
from pyrogram.handlers import MessageHandler
from motor.motor_asyncio import AsyncIOMotorClient
import os
from config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB client
mongo_client = None
db = None

async def get_db():
    global mongo_client, db
    if mongo_client is None:
        mongo_client = AsyncIOMotorClient(Config.MONGO_URL)
        db = mongo_client.telegram_bot
    return db

# Initialize bot
app = Client(
    "bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# Import handlers after bot initialization
from plugins.admin import admin
from plugins.protection import locks
from plugins.music import player
from plugins.replies import auto_reply
from plugins.welcome import welcome
from plugins.group_info import info

# Register modules
app.add_handler(MessageHandler(admin.handle_admin))
app.add_handler(MessageHandler(locks.handle_locks))
app.add_handler(MessageHandler(player.handle_music))
app.add_handler(MessageHandler(auto_reply.handle_reply))
app.add_handler(MessageHandler(welcome.handle_welcome))
app.add_handler(MessageHandler(info.handle_info))

@app.on_message(filters.command(["start", "help"]) | filters.regex("^مساعدة$"))
async def help_handler(client, message):
    await message.reply_text("""
🤖 **أوامر البوت:**

**الإدارة:**
رفع @user - رفع المستخدم لرتبة أعلى
تنزيل @user - تنزيل المستخدم من رتبته
حظر @user - حظر المستخدم من المجموعة
الغاء الحظر @user - إلغاء حظر المستخدم
كتم @user - كتم المستخدم
الغاء الكتم @user - إلغاء كتم المستخدم
طرد @user - طرد المستخدم من المجموعة

**الحماية:**
قفل الروابط / فتح الروابط - قفل/فتح إرسال الروابط
قفل التكرار / فتح التكرار - قفل/فتح التكرار في المجموعة
قفل السبام / فتح السبام - قفل/فتح إرسال الرسائل السريعة

**الموسيقى:**
تشغيل <الاسم أو الرابط> - تشغيل الموسيقى في الدردشة الصوتية
تخطي - تخطي الأغنية الحالية
ايقاف - إيقاف تشغيل الموسيقى
ايقاف مؤقت - إيقاف مؤقت
استئناف - استئناف التشغيل
قائمة التشغيل - عرض قائمة الانتظار
مغادرة - مغادرة الدردشة الصوتية

**المعلومات:**
ايدي - عرض معلومات المستخدم
معلوماتي - عرض معلوماتي
معلومات المجموعة - عرض معلومات المجموعة

**الترحيب:**
تفعيل الترحيب - تفعيل الترحيب
تعطيل الترحيب - تعطيل الترحيب
تعيين رسالة الترحيب - تعيين رسالة الترحيب
    """)

if __name__ == "__main__":
    app.run()
