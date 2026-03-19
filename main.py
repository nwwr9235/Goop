# main.py - النسخة المعدلة مع صورة البروفايل

import logging
import os
import re
import asyncio
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions, ChatPrivileges
from pyrogram.errors import UserAdminInvalid, ChatAdminRequired, UserNotParticipant
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Client(
    "bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# قاعدة بيانات مؤقتة
group_settings = {}
auto_replies = {}
warnings_db = {}

def get_group_settings(chat_id):
    if chat_id not in group_settings:
        group_settings[chat_id] = {
            'welcome_enabled': True,
            'welcome_message': 'مرحباً بك {user} في المجموعة {group}!',
            'locks': {}
        }
    return group_settings[chat_id]

async def is_admin(client, chat_id, user_id):
    try:
        if user_id in Config.SUDO_USERS:
            return True
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except:
        return False

async def get_target_from_reply(message):
    """استخراج المستخدم من الرد على الرسالة فقط"""
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
        logger.info(f"Target from reply: {target.id} - {target.first_name}")
        return target
    
    logger.warning("No reply found")
    return None

# ============================================================
# رفع مشرف - يعمل بالرد فقط
# ============================================================

@app.on_message(filters.regex(r'^رفع مشرف$') & filters.group)
async def promote_handler(client, message):
    logger.info(f"Promote command from {message.from_user.id}")
    
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    target = await get_target_from_reply(message)
    
    if not target:
        return await message.reply("⚠️ عليك الرد على رسالة المستخدم الذي تريد رفعه!")
    
    if target.is_bot:
        return await message.reply("❌ لا يمكن رفع البوتات!")
    
    try:
        await client.promote_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            privileges=ChatPrivileges(
                can_manage_chat=True,
                can_delete_messages=True,
                can_manage_video_chats=True,
                can_restrict_members=True,
                can_promote_members=False,
                can_change_info=True,
                can_invite_users=True,
                can_pin_messages=True,
                is_anonymous=False
            )
        )
        
        await message.reply(
            f"✅ تم رفع [{target.first_name}](tg://user?id={target.id}) إلى مشرف بنجاح!",
            disable_web_page_preview=True
        )
        logger.info(f"Successfully promoted {target.id}")
        
    except ChatAdminRequired:
        await message.reply("❌ البوت يحتاج صلاحية رفع المشرفين!")
    except UserAdminInvalid:
        await message.reply("❌ لا يمكن رفع هذا المستخدم!")
    except Exception as e:
        logger.error(f"Promote error: {e}")
        await message.reply(f"❌ فشل الرفع: {str(e)}")

# ============================================================
# تنزيل مشرف - يعمل بالرد فقط
# ============================================================

@app.on_message(filters.regex(r'^تنزيل مشرف$') & filters.group)
async def demote_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    target = await get_target_from_reply(message)
    if not target:
        return await message.reply("⚠️ عليك الرد على رسالة المستخدم الذي تريد تنزيله!")
    
    try:
        await client.promote_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            privileges=ChatPrivileges(
                can_manage_chat=False,
                can_delete_messages=False,
                can_manage_video_chats=False,
                can_restrict_members=False,
                can_promote_members=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False,
                is_anonymous=False
            )
        )
        await message.reply(f"✅ تم تنزيل [{target.first_name}](tg://user?id={target.id}) من المشرفين!")
    except Exception as e:
        await message.reply(f"❌ فشل التنزيل: {str(e)}")

# ============================================================
# حظر - يعمل بالرد فقط
# ============================================================

@app.on_message(filters.regex(r'^حظر$') & filters.group)
async def ban_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    target = await get_target_from_reply(message)
    if not target:
        return await message.reply("⚠️ عليك الرد على رسالة المستخدم الذي تريد حظره!")
    
    try:
        await client.ban_chat_member(message.chat.id, target.id)
        await message.reply(f"✅ تم حظر [{target.first_name}](tg://user?id={target.id})!")
    except Exception as e:
        await message.reply(f"❌ فشل الحظر: {str(e)}")

# ============================================================
# إلغاء حظر - يعمل بالرد فقط
# ============================================================

@app.on_message(filters.regex(r'^الغاء حظر$') & filters.group)
async def unban_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    target = await get_target_from_reply(message)
    if not target:
        return await message.reply("⚠️ عليك الرد على رسالة المستخدم الذي تريد إلغاء حظره!")
    
    try:
        await client.unban_chat_member(message.chat.id, target.id)
        await message.reply(f"✅ تم إلغاء حظر [{target.first_name}](tg://user?id={target.id})!")
    except Exception as e:
        await message.reply(f"❌ فشل إلغاء الحظر: {str(e)}")

# ============================================================
# كتم - يعمل بالرد فقط
# ============================================================

@app.on_message(filters.regex(r'^كتم$') & filters.group)
async def mute_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    target = await get_target_from_reply(message)
    if not target:
        return await message.reply("⚠️ عليك الرد على رسالة المستخدم الذي تريد كتمه!")
    
    try:
        await client.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False
            )
        )
        await message.reply(f"✅ تم كتم [{target.first_name}](tg://user?id={target.id})!")
    except Exception as e:
        await message.reply(f"❌ فشل الكتم: {str(e)}")

# ============================================================
# إلغاء كتم - يعمل بالرد فقط
# ============================================================

@app.on_message(filters.regex(r'^الغاء كتم$') & filters.group)
async def unmute_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    target = await get_target_from_reply(message)
    if not target:
        return await message.reply("⚠️ عليك الرد على رسالة المستخدم الذي تريد إلغاء كتمه!")
    
    try:
        await client.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
                can_change_info=True,
                can_invite_users=True,
                can_pin_messages=True
            )
        )
        await message.reply(f"✅ تم إلغاء كتم [{target.first_name}](tg://user?id={target.id})!")
    except Exception as e:
        await message.reply(f"❌ فشل إلغاء الكتم: {str(e)}")

# ============================================================
# طرد - يعمل بالرد فقط
# ============================================================

@app.on_message(filters.regex(r'^طرد$') & filters.group)
async def kick_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    target = await get_target_from_reply(message)
    if not target:
        return await message.reply("⚠️ عليك الرد على رسالة المستخدم الذي تريد طرده!")
    
    try:
        await client.ban_chat_member(message.chat.id, target.id)
        await asyncio.sleep(0.5)
        await client.unban_chat_member(message.chat.id, target.id)
        await message.reply(f"✅ تم طرد [{target.first_name}](tg://user?id={target.id})!")
    except Exception as e:
        await message.reply(f"❌ فشل الطرد: {str(e)}")

# ============================================================
# نظام الإنذارات - يعمل بالرد فقط
# ============================================================

@app.on_message(filters.regex(r'^انذار$') & filters.group)
async def warn_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    target = await get_target_from_reply(message)
    if not target:
        return await message.reply("⚠️ عليك الرد على رسالة المستخدم الذي تريد إنذاره!")
    
    chat_id = message.chat.id
    user_id = target.id
    
    if chat_id not in warnings_db:
        warnings_db[chat_id] = {}
    
    if user_id not in warnings_db[chat_id]:
        warnings_db[chat_id][user_id] = 0
    
    warnings_db[chat_id][user_id] += 1
    count = warnings_db[chat_id][user_id]
    
    if count >= 3:
        try:
            await client.ban_chat_member(chat_id, user_id)
            await message.reply(f"🚫 تم حظر [{target.first_name}](tg://user?id={user_id}) بعد 3 إنذارات!")
            warnings_db[chat_id][user_id] = 0
        except:
            await message.reply(f"⚠️ تم الوصول لـ 3 إنذارات لكن فشل الحظر")
    else:
        await message.reply(f"⚠️ إنذار {count}/3 للمستخدم [{target.first_name}](tg://user?id={user_id})")

@app.on_message(filters.regex(r'^عرض انذارات$') & filters.group)
async def show_warnings_handler(client, message):
    target = await get_target_from_reply(message)
    if not target:
        target = message.from_user
    
    chat_id = message.chat.id
    user_id = target.id
    
    count = warnings_db.get(chat_id, {}).get(user_id, 0)
    await message.reply(f"📋 إنذارات [{target.first_name}](tg://user?id={user_id}): {count}/3")

@app.on_message(filters.regex(r'^مسح انذارات$') & filters.group)
async def clear_warnings_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    target = await get_target_from_reply(message)
    if not target:
        return await message.reply("⚠️ عليك الرد على رسالة المستخدم الذي تريد مسح إنذاراته!")
    
    chat_id = message.chat.id
    user_id = target.id
    
    if chat_id in warnings_db and user_id in warnings_db[chat_id]:
        warnings_db[chat_id][user_id] = 0
    
    await message.reply(f"✅ تم مسح إنذارات [{target.first_name}](tg://user?id={user_id})")

# ============================================================
# نظام الردود التلقائية
# ============================================================

@app.on_message(filters.regex(r'^اضافة رد\s+(.+?)\s*=\s*(.+)') & filters.group)
async def add_reply_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    match = re.match(r'اضافة رد\s+(.+?)\s*=\s*(.+)', message.text, re.DOTALL)
    if not match:
        return await message.reply("⚠️ الصيغة: اضافة رد كلمة = الرد")
    
    trigger = match.group(1).strip().lower()
    response = match.group(2).strip()
    
    chat_id = message.chat.id
    if chat_id not in auto_replies:
        auto_replies[chat_id] = {}
    
    auto_replies[chat_id][trigger] = response
    
    await message.reply(f"✅ تم إضافة رد:\nكلمة: `{trigger}`\nرد: {response}")

@app.on_message(filters.regex(r'^حذف رد\s+(.+)') & filters.group)
async def delete_reply_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    match = re.match(r'حذف رد\s+(.+)', message.text)
    trigger = match.group(1).strip().lower()
    
    chat_id = message.chat.id
    if chat_id in auto_replies and trigger in auto_replies[chat_id]:
        del auto_replies[chat_id][trigger]
        await message.reply(f"✅ تم حذف رد: `{trigger}`")
    else:
        await message.reply(f"❌ الرد `{trigger}` غير موجود")

@app.on_message(filters.regex(r'^عرض الردود') & filters.group)
async def show_replies_handler(client, message):
    chat_id = message.chat.id
    
    if chat_id not in auto_replies or not auto_replies[chat_id]:
        return await message.reply("📭 لا توجد ردود مسجلة")
    
    text = "📋 قائمة الردود:\n\n"
    for trigger, response in auto_replies[chat_id].items():
        text += f"• `{trigger}` → {response}\n"
    
    await message.reply(text)

@app.on_message(filters.text & filters.group)
async def auto_reply_handler(client, message):
    """معالج الردود التلقائية"""
    if not message.text:
        return
    
    admin_commands = [
        'رفع مشرف', 'تنزيل مشرف', 'حظر', 'الغاء حظر', 
        'كتم', 'الغاء كتم', 'طرد',
        'انذار', 'عرض انذارات', 'مسح انذارات',
        'اضافة رد', 'حذف رد', 'عرض الردود',
        'تفعيل الترحيب', 'تعطيل الترحيب', 'تعيين رسالة الترحيب',
        'قفل', 'فتح', 'ايدي', 'معلوماتي', 'معلومات المجموعة'
    ]
    
    for cmd in admin_commands:
        if message.text.startswith(cmd):
            return
    
    chat_id = message.chat.id
    if chat_id not in auto_replies:
        return
    
    text = message.text.lower()
    for trigger, response in auto_replies[chat_id].items():
        if trigger in text:
            await message.reply(response)
            return

# ============================================================
# أمر ايدي المعدل - مع صورة البروفايل
# ============================================================

@app.on_message(filters.regex(r'^ايدي$') | filters.command("id"))
async def id_handler(client, message):
    # تحديد المستخدم (الشخص نفسه أو من الرد)
    target = message.from_user
    
    # إذا كان هناك رد، أظهر معلومات الشخص المردود عليه
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
    
    chat = message.chat
    
    # الحصول على صورة البروفايل
    photos = []
    try:
        photos = await client.get_chat_photos(target.id, limit=1)
    except Exception as e:
        logger.error(f"Error getting profile photos: {e}")
    
    # بناء نص المعلومات
    text = f"""
👤 **معلومات المستخدم:**

🆔 **الايدي:** `{target.id}`
📛 **الاسم:** {target.first_name}
🔖 **المعرف:** @{target.username if target.username else 'لا يوجد'}
📅 **تاريخ الانضمام:** {target.join_date if hasattr(target, 'join_date') else 'غير متوفر'}
🤖 **نوع الحساب:** {'بوت' if target.is_bot else 'مستخدم'}
💬 **الحالة:** {target.status if hasattr(target, 'status') else 'غير معروف'}

📊 **معلومات المجموعة:**
🆔 **ايدي المجموعة:** `{chat.id}`
📛 **اسم المجموعة:** {chat.title}
👥 **عدد الأعضاء:** {await client.get_chat_members_count(chat.id) if chat.type != 'private' else 'N/A'}
    """
    
    # إرسال الصورة مع النص إذا وجدت
    if photos:
        async for photo in photos:
            await message.reply_photo(
                photo=photo.file_id,
                caption=text,
                quote=True
            )
            return
    
    # إذا لم توجد صورة، إرسال النص فقط
    await message.reply(text, quote=True)

# ============================================================
# أمر معلوماتي المعدل - مع صورة البروفايل
# ============================================================

@app.on_message(filters.regex(r'^معلوماتي$'))
async def my_info_handler(client, message):
    user = message.from_user
    
    # الحصول على صورة البروفايل
    photos = []
    try:
        photos = await client.get_chat_photos(user.id, limit=1)
    except Exception as e:
        logger.error(f"Error getting profile photos: {e}")
    
    try:
        member = await client.get_chat_member(message.chat.id, user.id)
        status = member.status
    except:
        status = "غير معروف"
    
    text = f"""
👤 **معلوماتك الشخصية:**

🆔 **الايدي:** `{user.id}`
📛 **الاسم:** {user.first_name}
📧 **المعرف:** @{user.username if user.username else 'لا يوجد'}
📊 **الحالة في المجموعة:** {status}
🤖 **نوع الحساب:** {'بوت' if user.is_bot else 'مستخدم'}
    """
    
    # إرسال الصورة مع النص إذا وجدت
    if photos:
        async for photo in photos:
            await message.reply_photo(
                photo=photo.file_id,
                caption=text,
                quote=True
            )
            return
    
    await message.reply(text, quote=True)

# ============================================================
# أمر معلومات المجموعة المعدل
# ============================================================

@app.on_message(filters.regex(r'^معلومات المجموعة$') | filters.regex(r'^معلومات المجموعه$'))
async def group_info_handler(client, message):
    chat = message.chat
    
    try:
        count = await client.get_chat_members_count(chat.id)
    except:
        count = "غير معروف"
    
    # الحصول على صورة المجموعة إذا وجدت
    chat_photo = None
    if chat.photo:
        try:
            chat_photo = chat.photo.big_file_id
        except:
            pass
    
    text = f"""
📊 **معلومات المجموعة:**

🆔 **الايدي:** `{chat.id}`
📛 **الاسم:** {chat.title}
👥 **عدد الأعضاء:** {count}
📋 **الوصف:** {chat.description if chat.description else 'لا يوجد وصف'}
🔗 **الرابط:** {chat.invite_link if chat.invite_link else 'غير متوفر'}
🔒 **نوع المجموعة:** {chat.type}
    """
    
    # إرسال الصورة مع النص إذا وجدت
    if chat_photo:
        await message.reply_photo(
            photo=chat_photo,
            caption=text,
            quote=True
        )
    else:
        await message.reply(text, quote=True)

# ============================================================
# نظام الترحيب
# ============================================================

@app.on_message(filters.new_chat_members & filters.group)
async def welcome_handler(client, message):
    settings = get_group_settings(message.chat.id)
    
    if not settings['welcome_enabled']:
        return
    
    me = await client.get_me()
    
    for new_member in message.new_chat_members:
        if new_member.id == me.id:
            continue
        
        welcome_text = settings['welcome_message'].format(
            user=new_member.first_name,
            group=message.chat.title,
            username=new_member.username or "",
            id=new_member.id
        )
        
        await message.reply(welcome_text)

@app.on_message(filters.regex(r'^تفعيل الترحيب$') & filters.group)
async def enable_welcome_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    settings = get_group_settings(message.chat.id)
    settings['welcome_enabled'] = True
    
    await message.reply("✅ تم تفعيل الترحيب")

@app.on_message(filters.regex(r'^تعطيل الترحيب$') & filters.group)
async def disable_welcome_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    settings = get_group_settings(message.chat.id)
    settings['welcome_enabled'] = False
    
    await message.reply("✅ تم تعطيل الترحيب")

@app.on_message(filters.regex(r'^تعيين رسالة الترحيب\s+(.+)') & filters.group)
async def set_welcome_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    match = re.match(r'تعيين رسالة الترحيب\s+(.+)', message.text, re.DOTALL)
    welcome_msg = match.group(1).strip()
    
    settings = get_group_settings(message.chat.id)
    settings['welcome_message'] = welcome_msg
    
    await message.reply(f"✅ تم تعيين رسالة الترحيب:\n{welcome_msg}")

# ============================================================
# نظام الحماية
# ============================================================

LOCK_TYPES = {
    'الروابط': 'links',
    'التكرار': 'flood',
    'السبام': 'spam',
    'البوتات': 'bots',
    'الصور': 'photos',
    'الفيديو': 'videos',
    'الملفات': 'files',
    'الملصقات': 'stickers',
    'الصوتيات': 'voices'
}

@app.on_message(filters.regex(r'^قفل\s+(\w+)') & filters.group)
async def lock_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    match = re.match(r'^قفل\s+(\w+)', message.text)
    lock_type = match.group(1)
    
    if lock_type not in LOCK_TYPES:
        return await message.reply(f"❌ الأنواع المتاحة: {', '.join(LOCK_TYPES.keys())}")
    
    settings = get_group_settings(message.chat.id)
    settings['locks'][LOCK_TYPES[lock_type]] = True
    
    await message.reply(f"🔒 تم قفل {lock_type}")

@app.on_message(filters.regex(r'^فتح\s+(\w+)') & filters.group)
async def unlock_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    match = re.match(r'^فتح\s+(\w+)', message.text)
    lock_type = match.group(1)
    
    if lock_type not in LOCK_TYPES:
        return await message.reply(f"❌ نوع القفل غير معروف")
    
    settings = get_group_settings(message.chat.id)
    settings['locks'][LOCK_TYPES[lock_type]] = False
    
    await message.reply(f"🔓 تم فتح {lock_type}")

# ============================================================
# المساعدة المعدلة
# ============================================================

@app.on_message(filters.regex(r'^مساعدة$') | filters.regex(r'^الاوامر$') | filters.command(["start", "help"]))
async def help_handler(client, message):
    help_text = """
🤖 **أوامر البوت:**

**👮‍♂️ الإدارة (بالرد على رسالة المستخدم):**
`رفع مشرف` - رفع المستخدم إلى مشرف
`تنزيل مشرف` - تنزيل المستخدم من المشرفين
`حظر` - حظر المستخدم
`الغاء حظر` - إلغاء حظر المستخدم
`كتم` - كتم المستخدم
`الغاء كتم` - إلغاء كتم المستخدم
`طرد` - طرد المستخدم

**⚠️ الإنذارات (بالرد):**
`انذار` - إنذار المستخدم (3 = حظر تلقائي)
`عرض انذارات` - عرض إنذارات المستخدم
`مسح انذارات` - مسح إنذارات المستخدم

**🔒 الحماية:**
`قفل الروابط` - منع إرسال الروابط
`فتح الروابط` - السماح بالروابط
`قفل التكرار` - منع التكرار
`فتح التكرار` - السماح بالتكرار

**💬 الردود التلقائية:**
`اضافة رد كلمة = الرد` - إضافة رد تلقائي
`حذف رد كلمة` - حذف رد تلقائي
`عرض الردود` - عرض جميع الردود

**👋 الترحيب:**
`تفعيل الترحيب` - تفعيل رسالة الترحيب
`تعطيل الترحيب` - تعطيل رسالة الترحيب
`تعيين رسالة الترحيب [نص]` - تعيين رسالة الترحيب

**📋 المعلومات:**
`ايدي` - معلوماتك + صورة البروفايل
`ايدي` (بالرد) - معلومات الشخص + صورته
`معلوماتي` - تفاصيلك + صورة البروفايل
`معلومات المجموعة` - معلومات المجموعة + صورتها

**ملاحظة:** جميع أوامر الإدارة تعمل بالرد على رسالة المستخدم فقط!
    """
    
    await message.reply(help_text, disable_web_page_preview=True)

# ============================================================
# تشغيل البوت
# ============================================================

if __name__ == "__main__":
    logger.info("🚀 جاري تشغيل البوت...")
    app.run()
