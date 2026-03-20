"""
admin_bot/plugins/info.py
أوامر عرض المعلومات والصور
"""

from pyrogram import Client, filters
from admin_bot.helpers import get_target_from_reply


def register(app: Client):

    # ─── ا : معلوماتك + صورتك ───────────────────────────────────
    @app.on_message(filters.regex(r"^ا$") & filters.group)
    async def id_handler(client, message):
        target = message.from_user
        chat   = message.chat
        try:
            member = await client.get_chat_member(chat.id, target.id)
            status  = member.status
            joined  = member.joined_date.strftime("%Y-%m-%d") if member.joined_date else "غير معروف"
        except Exception:
            status = joined = "غير معروف"

        members_count = "N/A"
        try:
            members_count = await client.get_chat_members_count(chat.id)
        except Exception:
            pass

        info = (
            "┏━ 𝙐𝙎𝙀𝙍 𝙄𝙉𝙁𝙊 ━┓\n\n"
            f"🆔 **ايدي:** `{target.id}`\n"
            f"👤 **الاسم:** {target.first_name}\n"
            f"📧 **المعرف:** @{target.username or 'لا يوجد'}\n"
            f"📊 **الحالة:** {status}\n"
            f"📅 **الانضمام:** {joined}\n"
            f"🤖 **النوع:** {'بوت 🤖' if target.is_bot else 'عضو 👤'}\n\n"
            "┏━ 𝙂𝙍𝙊𝙐𝙋 𝙄𝙉𝙁𝙊 ━┓\n\n"
            f"🆔 **ايدي:** `{chat.id}`\n"
            f"📛 **الاسم:** {chat.title}\n"
            f"👥 **الأعضاء:** {members_count}"
        )
        await _send_with_photo(client, message, target.id, info)

    # ─── اا : صورتك فقط ─────────────────────────────────────────
    @app.on_message(filters.regex(r"^اا$") & filters.group)
    async def my_photo_handler(client, message):
        target = message.from_user
        await _send_photo_only(client, message, target.id, target.first_name)

    # ─── افتاره : صورة الآخر ────────────────────────────────────
    @app.on_message(filters.regex(r"^افتاره$") & filters.group)
    async def his_photo_handler(client, message):
        target = await get_target_from_reply(message)
        if not target:
            return await message.reply("⚠️ عليك الرد على رسالة الشخص لعرض صورته!")
        await _send_photo_only(client, message, target.id, target.first_name)

    # ─── المساعدة ───────────────────────────────────────────────
    @app.on_message(
        (filters.regex(r"^مساعدة$|^الاوامر$") | filters.command(["start", "help"]))
    )
    async def help_handler(client, message):
        await message.reply(
            "🤖 **أوامر البوت:**\n\n"
            "**👮‍♂️ الإدارة (بالرد):**\n"
            "`رفع مشرف` `تنزيل مشرف` `حظر` `الغاء حظر`\n"
            "`كتم` `الغاء كتم` `طرد`\n\n"
            "**⚠️ الإنذارات:**\n"
            "`انذار` `عرض انذارات` `مسح انذارات`\n\n"
            "**🔒 الحماية:**\n"
            "`قفل الروابط` `فتح الروابط`  "`قفل الصور` `فتح الصور`\n"
            "`قفل الفيديو` `فتح الفيديو`  `قفل الملفات` `فتح الملفات`\n"
            "`قفل الملصقات` `فتح الملصقات` `قفل الصوتيات` `فتح الصوتيات`\n\n"
            "**🎵 الموسيقى:**\n"
            "`تشغيل [اسم الأغنية]` `ايقاف` `تخطي`\n"
            "`ايقاف مؤقت` `استئناف` `القائمة`\n\n"
            "**💬 الردود التلقائية:**\n"
            "`اضافة رد كلمة = الرد` `حذف رد كلمة` `عرض الردود`\n\n"
            "**👋 الترحيب:**\n"
            "`تفعيل الترحيب` `تعطيل الترحيب`\n"
            "`تعيين رسالة الترحيب [نص]`\n\n"
            "**📋 المعلومات:**\n"
            "`ا` معلوماتك + صورتك | `اا` صورتك | `افتاره` صورة الآخر (رد)\n\n"
            "_جميع الأوامر تعمل داخل المجموعات فقط._"
        )


# ─── دوال مساعدة خاصة ────────────────────────────────────────────

async def _send_with_photo(client, message, user_id: int, caption: str):
    try:
        photos = [p async for p in client.get_chat_photos(user_id, limit=1)]
        if photos:
            await message.reply_photo(photos[0].file_id, caption=caption)
        else:
            await message.reply(caption + "\n\n📷 لا توجد صورة")
    except Exception:
        await message.reply(caption)


async def _send_photo_only(client, message, user_id: int, name: str):
    try:
        photos = [p async for p in client.get_chat_photos(user_id, limit=1)]
        if photos:
            await message.reply_photo(photos[0].file_id)
        else:
            await message.reply(f"📷 **{name} ليس لديه صورة ملف شخصي**")
    except Exception:
        await message.reply("❌ تعذر عرض الصورة")
