Create a production-ready Telegram Supergroup Management + Music Bot similar to Rose Telegram Bot and VCPlayer Telegram Bot.

The bot must support:

 Group moderation
 Advanced protection system
 Auto replies
 Welcome system
 Voice chat music player

IMPORTANT:
The bot must support Arabic commands without "/" and work fully inside group messages.

---

TECH STACK

Language: Python

Libraries:

- Pyrogram
- PyTgCalls
- TgCrypto

Database:

- MongoDB (use async Motor)

Streaming:

- yt-dlp
- ffmpeg

Architecture:

- Async / await
- Modular plugin system

---

DEPLOYMENT (VERY IMPORTANT)

The bot must be fully ready to deploy on Railway.app

Requirements:

1. Create a Procfile
   Example:
   worker: python main.py

2. Create requirements.txt

3. Use environment variables instead of hardcoding:

- API_ID
- API_HASH
- BOT_TOKEN
- MONGO_URL
- SUDO_USERS

4. Add support for Railway environment

5. Auto start on deploy

6. Handle restart safely

7. Logging for Railway console

---

ADMIN FEATURES (Arabic without slash)

رفع @user
تنزيل @user

حظر @user
الغاء الحظر @user

كتم @user
الغاء الكتم @user

طرد @user

قائمة الادمنية

---

WARNING SYSTEM

انذار @user
عرض الانذارات @user
مسح الانذارات @user

Auto punishment after 3 warnings:

- mute or ban

---

PROTECTION SYSTEM

Implement advanced locks:

قفل الروابط / فتح الروابط
قفل التكرار / فتح التكرار
قفل السبام / فتح السبام
قفل البوتات / فتح البوتات
قفل الصور / فتح الصور
قفل الفيديو / فتح الفيديو
قفل الملفات / فتح الملفات

Add:

- anti flood
- anti spam
- anti links
- blacklist words

---

WELCOME SYSTEM

Commands:

تفعيل الترحيب
تعطيل الترحيب
تعيين رسالة الترحيب

Support variables:
{user}
{group}

---

AUTO REPLIES

اضافة رد مرحبا = اهلا بك
حذف رد مرحبا
عرض الردود

---

MUSIC SYSTEM (VOICE CHAT)

Commands:

تشغيل <name or link>
تخطي
ايقاف
ايقاف مؤقت
استئناف
قائمة التشغيل
مغادرة

Features:

- auto join voice chat
- queue system
- YouTube search
- fast streaming
- stable playback

---

GROUP INFO

ايدي
معلوماتي
معلومات @user
معلومات المجموعة

---

UTILITY

مساعدة
الاوامر
حالة البوت
سرعة البوت

---

OWNER COMMANDS

اعادة تشغيل
اذاعة
تحديث

---

DATABASE

Store in MongoDB:

- settings
- locks
- warnings
- replies
- welcome
- music queue

---

PROJECT STRUCTURE

bot/
plugins/
plugins/admin/
plugins/music/
plugins/protection/
plugins/replies/
plugins/welcome/

database/
utils/
config/

---

FILES

main.py
config.py
requirements.txt
Procfile
.env

---

EXTRA (IMPORTANT FOR RAILWAY)

- The bot must not crash if connection drops
- Auto reconnect to MongoDB
- Handle Pyrogram session restart
- Use logging module
- Use try/except in all handlers

---

GOAL

Build a high-performance Telegram bot that:

• runs on Railway smoothly
• supports Arabic commands without slash
• manages large groups (100k+ members)
• plays music in voice chat
• has strong protection system
• stable and production-ready
