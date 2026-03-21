"""
shared/config.py
إعدادات مشتركة بين البوتين
"""

import os
from dotenv import load_dotenv

load_dotenv()


class AdminConfig:
    """إعدادات بوت الإدارة"""
    API_ID       = int(os.getenv("API_ID", 0))
    API_HASH     = os.getenv("API_HASH", "")
    BOT_TOKEN    = os.getenv("ADMIN_BOT_TOKEN", "")
    MONGO_URL    = os.getenv("MONGO_URL", "")

    sudo_str     = os.getenv("SUDO_USERS", "")
    SUDO_USERS   = [int(x.strip()) for x in sudo_str.split(",") if x.strip()]

    # عنوان API الخاص ببوت الموسيقى
    MUSIC_API_URL    = os.getenv("MUSIC_API_URL", "http://localhost:8000")
    # مفتاح سري مشترك بين البوتين (يجب أن يكون نفس القيمة في البوتين)
    INTERNAL_SECRET  = os.getenv("INTERNAL_SECRET", "change_this_secret_key")


class MusicConfig:
    """إعدادات بوت الموسيقى"""
    API_ID      = int(os.getenv("API_ID", 0))
    API_HASH    = os.getenv("API_HASH", "")
    
    # ✅ توكن البوت المساعد (للمكالمات الصوتية)
    # يمكن استخدام MUSIC_BOT_TOKEN كـ fallback
    ASSISTANT_BOT_TOKEN = os.getenv("ASSISTANT_BOT_TOKEN") or os.getenv("MUSIC_BOT_TOKEN", "")
    
    # ✅ توكن بوت الموسيقى (للتوافق مع الكود القديم)
    BOT_TOKEN   = os.getenv("MUSIC_BOT_TOKEN", "")
    
    MONGO_URL   = os.getenv("MONGO_URL", "")

    # ✅ المنفذ (Railway يستخدم PORT، نستخدمه كأولوية)
    API_PORT    = int(os.getenv("PORT") or os.getenv("MUSIC_API_PORT", 8000))
    
    INTERNAL_SECRET  = os.getenv("INTERNAL_SECRET", "change_this_secret_key")
