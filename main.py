# main.py - النسخة المصححة (بدون StreamType)

import logging
import os
import re
import asyncio
import yt_dlp
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions, ChatPrivileges
from pyrogram.errors import UserAdminInvalid, ChatAdminRequired, UserNotParticipant
from pytgcalls import PyTgCalls
from pytgcalls.types import Update
from pytgcalls.types.input_stream import InputAudioStream, InputStream
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# تهيئة البوت
app = Client(
    "bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# تهيئة PyTgCalls للمكالمات الصوتية
pytgcalls = PyTgCalls(app)

# ============================================================
# قواعد البيانات
# ============================================================

group_settings = {}
auto_replies = {}
warnings_db = {}

# قاعدة بيانات الموسيقى
music_queues = {}  # {chat_id: [song_dict, ...]}
current_song = {}  # {chat_id: song_dict}
is_playing = {}    # {chat_id: bool}

def get_group_settings(chat_id):
    if chat_id not in group_settings:
        group_settings[chat_id] = {
            'welcome_enabled': True,
            'welcome_message': 'مرحباً بك {user} في المجموعة {group}!',
            'locks': {
                'links': False,
                'flood': False,
                'spam': False,
                'bots': False,
                'photos': False,
                'videos': False,
                'files': False,
                'stickers': False,
                'voices': False
            }
        }
    return group_settings[chat_id]

async def is_admin(client, chat_id, user_id):
    try:
        if user_id in Config.SUDO_USERS:
            return True
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking admin: {e}")
        return False

async def get_target_from_reply(message):
    """استخراج المستخدم من الرد على الرسالة"""
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
        logger.info(f"Target from reply: {target.id} - {target.first_name}")
        return target
    return None

# ============================================================
# نظام الموسيقى - دوال مساعدة
# ============================================================

async def download_song(query):
    """تحميل الأغنية من YouTube"""
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # البحث في YouTube
            info = ydl.extract_info(f"ytsearch:{query}", download=False)
            if 'entries' in info:
                info = info['entries'][0]
            
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            url = info.get('webpage_url', '')
            thumbnail = info.get('thumbnail', '')
            
            # تحميل الملف
            file_path = ydl.prepare_filename(info)
            ydl.download([url])
            
            # إرجاع معلومات الأغنية
            return {
                'title': title,
                'file_path': file_path.replace('.webm', '.mp3').replace('.m4a', '.mp3'),
                'duration': duration,
                'url': url,
                'thumbnail': thumbnail
            }
    except Exception as e:
        logger.error(f"Error downloading song: {e}")
        return None

async def play_next_song(client, chat_id):
    """تشغيل الأغنية التالية في القائمة"""
    global music_queues, current_song, is_playing
    
    if chat_id not in music_queues or not music_queues[chat_id]:
        is_playing[chat_id] = False
        current_song[chat_id] = None
        return
    
    # الحصول على الأغنية التالية
    song = music_queues[chat_id].pop(0)
    current_song[chat_id] = song
    is_playing[chat_id] = True
    
    try:
        # الانضمام إلى المكالمة إذا لم نكن فيها
        try:
            await pytgcalls.join_group_call(
                chat_id,
                InputStream(
                    InputAudioStream(
                        song['file_path'],
                    ),
                ),
            )
        except Exception as e:
            logger.error(f"Error joining call: {e}")
            # ربما نحن بالفعل في المكالمة، نحاول التشغيل مباشرة
            await pytgcalls.change_stream(
                chat_id,
                InputStream(
                    InputAudioStream(
                        song['file_path'],
                    ),
                ),
            )
        
        # إرسال رسالة التشغيل
        await client.send_message(
            chat_id,
            f"🎵 **يتم تشغيل:**\n{song['title']}\n⏱ المدة: {song['duration']//60}:{song['duration']%60:02d}"
        )
        
    except Exception as e:
        logger.error(f"Error playing song: {e}")
        is_playing[chat_id] = False
        await client.send_message(chat_id, f"❌ فشل تشغيل: {str(e)}")

# ============================================================
# أوامر الموسيقى
# ============================================================

@app.on_message(filters.regex(r'^تشغيل\s+(.+)') & filters.group)
async def play_handler(client, message):
    """أمر تشغيل: تشغيل <اسم الأغنية أو الرابط>"""
    chat_id = message.chat.id
    
    # استخراج اسم الأغنية
    match = re.match(r'^تشغيل\s+(.+)', message.text)
    if not match:
        return await message.reply("⚠️ الصيغة: تشغيل <اسم الأغنية>")
    
    query = match.group(1).strip()
    
    # إرسال رسالة البحث
    status_msg = await message.reply("🔍 **جاري البحث...**")
    
    # تحميل الأغنية
    song = await download_song(query)
    
    if not song:
        return await status_msg.edit("❌ **لم يتم العثور على الأغنية**")
    
    # إضافة إلى القائمة
    if chat_id not in music_queues:
        music_queues[chat_id] = []
    
    music_queues[chat_id].append(song)
    
    await status_msg.edit(f"✅ **تم إضافة إلى القائمة:**\n🎵 {song['title']}")
    
    # إذا لم يكن هناك تشغيل حالي، ابدأ التشغيل
    if not is_playing.get(chat_id, False):
        await play_next_song(client, chat_id)

@app.on_message(filters.regex(r'^تخطي$') & filters.group)
async def skip_handler(client, message):
    """أمر تخطي: تخطي الأغنية الحالية"""
    chat_id = message.chat.id
    
    if not is_playing.get(chat_id, False):
        return await message.reply("⚠️ **لا يوجد تشغيل حالي**")
    
    try:
        await pytgcalls.leave_group_call(chat_id)
        await message.reply("⏭ **تم تخطي الأغنية**")
        
        # تشغيل التالية
        await asyncio.sleep(1)
        await play_next_song(client, chat_id)
    except Exception as e:
        logger.error(f"Error skipping: {e}")
        await message.reply(f"❌ فشل التخطي: {str(e)}")

@app.on_message(filters.regex(r'^ايقاف$') & filters.group)
async def stop_handler(client, message):
    """أمر إيقاف: إيقاف التشغيل"""
    chat_id = message.chat.id
    
    if not is_playing.get(chat_id, False):
        return await message.reply("⚠️ **لا يوجد تشغيل حالي**")
    
    try:
        await pytgcalls.leave_group_call(chat_id)
        music_queues[chat_id] = []
        is_playing[chat_id] = False
        current_song[chat_id] = None
        await message.reply("⏹ **تم إيقاف التشغيل**")
    except Exception as e:
        logger.error(f"Error stopping: {e}")
        await message.reply(f"❌ فشل الإيقاف: {str(e)}")

@app.on_message(filters.regex(r'^ايقاف مؤقت$') & filters.group)
async def pause_handler(client, message):
    """أمر إيقاف مؤقت"""
    chat_id = message.chat.id
    
    if not is_playing.get(chat_id, False):
        return await message.reply("⚠️ **لا يوجد تشغيل حالي**")
    
    try:
        await pytgcalls.pause_stream(chat_id)
        await message.reply("⏸ **تم إيقاف مؤقت**")
    except Exception as e:
        logger.error(f"Error pausing: {e}")
        await message.reply(f"❌ فشل: {str(e)}")

@app.on_message(filters.regex(r'^استئناف$') & filters.group)
async def resume_handler(client, message):
    """أمر استئناف"""
    chat_id = message.chat.id
    
    if not is_playing.get(chat_id, False):
        return await message.reply("⚠️ **لا يوجد تشغيل متوقف**")
    
    try:
        await pytgcalls.resume_stream(chat_id)
        await message.reply("▶️ **تم الاستئناف**")
    except Exception as e:
        logger.error(f"Error resuming: {e}")
        await message.reply(f"❌ فشل: {str(e)}")

@app.on_message(filters.regex(r'^قائمة التشغيل$') & filters.group)
async def queue_handler(client, message):
    """أمر قائمة التشغيل"""
    chat_id = message.chat.id
    
    if chat_id not in music_queues or not music_queues[chat_id]:
        if not current_song.get(chat_id):
            return await message.reply("📭 **قائمة التشغيل فارغة**")
    
    text = "📋 **قائمة التشغيل:**\n\n"
    
    # الأغنية الحالية
    if current_song.get(chat_id):
        text += f"▶️ **الحالية:** {current_song[chat_id]['title']}\n\n"
    
    # الأغاني في الانتظار
    if chat_id in music_queues:
        for i, song in enumerate(music_queues[chat_id], 1):
            text += f"{i}. {song['title']}\n"
    
    await message.reply(text)

@app.on_message(filters.regex(r'^مغادرة$') & filters.group)
async def leave_handler(client, message):
    """أمر مغادرة: مغادرة المكالمة الصوتية"""
    chat_id = message.chat.id
    
    try:
        await pytgcalls.leave_group_call(chat_id)
        music_queues[chat_id] = []
        is_playing[chat_id] = False
        current_song[chat_id] = None
        await message.reply("👋 **تم مغادرة المكالمة**")
    except Exception as e:
        logger.error(f"Error leaving: {e}")
        await message.reply(f"❌ فشل المغادرة: {str(e)}")

# ============================================================
# الأوامر الإدارية (تعمل بالرد فقط)
# ============================================================

@app.on_message(filters.regex(r'^رفع مشرف$') & filters.group)
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
        await message.reply(f"✅ تم رفع [{target.first_name}](tg://user?id={target.id}) إلى مشرف!")
    except Exception as e:
        await message.reply(f"❌ فشل: {str(e)}")

@app.on_message(filters.regex(r'^تنزيل مشرف$') & filters.group)
async def demote_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    target = await get_target_from_reply(message)
    if not target:
        return await message.reply("⚠️ عليك الرد على رسالة المستخدم!")
    
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
        await message.reply(f"✅ تم تنزيل [{target.first_name}](tg://user?id={target.id})!")
    except Exception as e:
        await message.reply(f"❌ فشل: {str(e)}")

@app.on_message(filters.regex(r'^حظر$') & filters.group)
async def ban_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    target = await get_target_from_reply(message)
    if not target:
        return await message.reply("⚠️ عليك الرد على رسالة المستخدم!")
    
    try:
        await client.ban_chat_member(message.chat.id, target.id)
        await message.reply(f"✅ تم حظر [{target.first_name}.first_name}](tg://user?id={target.id})!")
    except Exception as e:
        await message.reply(f"❌ فشل: {str(e)}")

@app.on_message(filters.regex(r'^الغاء حظر$') & filters.group)
async def unban_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    target = await get_target_from_reply(message)
    if not target:
        return await message.reply("⚠️ عليك الرد على رسالة المستخدم!")
    
    try:
        await client.unban_chat_member(message.chat.id, target.id)
        await message.reply(f"✅ تم إلغاء حظر [{target.first_name}](tg://user?id={target.id})!")
    except Exception as e:
        await message.reply(f"❌ فشل: {str(e)}")

@app.on_message(filters.regex(r'^كتم$') & filters.group)
async def mute_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    target = await get_target_from_reply(message)
    if not target:
        return await message.reply("⚠️ عليك الرد على رسالة المستخدم!")
    
    try:
        await client.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            permissions=ChatPermissions(can_send_messages=False)
        )
        await message.reply(f"✅ تم كتم [{target.first_name}](tg://user?id={target.id})!")
    except Exception as e:
        await message.reply(f"❌ فشل: {str(e)}")

@app.on_message(filters.regex(r'^الغاء كتم$') & filters.group)
async def unmute_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    target = await get_target_from_reply(message)
    if not target:
        return await message.reply("⚠️ عليك الرد على رسالة المستخدم!")
    
    try:
        await client.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target.id,
            permissions=ChatPermissions(can_send_messages=True)
        )
        await message.reply(f"✅ تم إلغاء كتم [{target.first_name}](tg://user?id={target.id})!")
    except Exception as e:
        await message.reply(f"❌ فشل: {str(e)}")

@app.on_message(filters.regex(r'^طرد$') & filters.group)
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
        await message.reply(f"✅ تم طرد [{target.first_name}](tg://user?id={target.id})!")
    except Exception as e:
        await message.reply(f"❌ فشل: {str(e)}")

# ============================================================
# نظام الإنذارات
# ============================================================

@app.on_message(filters.regex(r'^انذار$') & filters.group)
async def warn_handler(client, message):
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    target = await get_target_from_reply(message)
    if not target:
        return await message.reply("⚠️ عليك الرد على رسالة المستخدم!")
    
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
            await message.reply(f"⚠️ 3 إنذارات لكن فشل الحظر")
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
        return await message.reply("⚠️ عليك الرد على رسالة المستخدم!")
    
    chat_id = message.chat.id
    user_id = target.id
    
    if chat_id in warnings_db and user_id in warnings_db[chat_id]:
        warnings_db[chat_id][user_id] = 0
    
    await message.reply(f"✅ تم مسح إنذارات [{target.first_name}](tg://user?id={user_id})")

# ============================================================
# نظام الردود التلقائية
# ============================================================

@app.on_message(filters.regex(r'^اضافة رد\s+(.+?)\s*=\s*(.+)', re.DOTALL) & filters.group)
async def add_reply_handler(client, message):
    logger.info(f"Add reply command: {message.text}")
    
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    match = re.match(r'^اضافة رد\s+(.+?)\s*=\s*(.+)', message.text, re.DOTALL)
    if not match:
        return await message.reply("⚠️ الصيغة:\nاضافة رد كلمة = الرد")
    
    trigger = match.group(1).strip().lower()
    response = match.group(2).strip()
    
    if not trigger or not response:
        return await message.reply("⚠️ الكلمة والرد لا يمكن أن يكونا فارغين!")
    
    chat_id = message.chat.id
    if chat_id not in auto_replies:
        auto_replies[chat_id] = {}
    
    auto_replies[chat_id][trigger] = response
    
    await message.reply(f"✅ تم إضافة الرد:\n🔹 الكلمة: `{trigger}`\n🔸 الرد: {response}")

@app.on_message(filters.regex(r'^حذف رد\s+(.+)') & filters.group)
async def delete_reply_handler(client, message):
    logger.info(f"Delete reply command: {message.text}")
    
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    match = re.match(r'^حذف رد\s+(.+)', message.text)
    if not match:
        return await message.reply("⚠️ الصيغة: حذف رد كلمة")
    
    trigger = match.group(1).strip().lower()
    
    chat_id = message.chat.id
    if chat_id in auto_replies and trigger in auto_replies[chat_id]:
        del auto_replies[chat_id][trigger]
        await message.reply(f"✅ تم حذف رد: `{trigger}`")
    else:
        await message.reply(f"❌ الرد `{trigger}` غير موجود")

@app.on_message(filters.regex(r'^عرض الردود$') & filters.group)
async def show_replies_handler(client, message):
    logger.info(f"Show replies command in chat {message.chat.id}")
    
    chat_id = message.chat.id
    
    if chat_id not in auto_replies or not auto_replies[chat_id]:
        return await message.reply("📭 لا توجد ردود مسجلة في هذه المجموعة")
    
    text = "📋 قائمة الردود:\n\n"
    for trigger, response in auto_replies[chat_id].items():
        text += f"🔹 `{trigger}` → {response}\n"
    
    await message.reply(text)

# ============================================================
# معالج الردود التلقائية
# ============================================================

@app.on_message(filters.text & filters.group, group=1)
async def auto_reply_handler(client, message):
    """معالج الردود التلقائية"""
    
    if not message.text or message.from_user.is_bot:
        return
    
    text = message.text.strip()
    lower_text = text.lower()
    
    # قائمة الأوامر التي لا يجب الرد عليها
    admin_commands = [
        'رفع مشرف', 'تنزيل مشرف', 'حظر', 'الغاء حظر',
        'كتم', 'الغاء كتم', 'طرد', 'انذار',
        'عرض انذارات', 'مسح انذارات',
        'اضافة رد', 'حذف رد', 'عرض الردود',
        'تفعيل الترحيب', 'تعطيل الترحيب', 'تعيين رسالة الترحيب',
        'قفل', 'فتح', 'ا', 'افتاره', 'مساعدة', 'الاوامر',
        'تشغيل', 'تخطي', 'ايقاف', 'ايقاف مؤقت', 'استئناف',
        'قائمة التشغيل', 'مغادرة'
    ]
    
    for cmd in admin_commands:
        if lower_text.startswith(cmd.lower()):
            return
    
    chat_id = message.chat.id
    if chat_id not in auto_replies:
        return
    
    for trigger, response in auto_replies[chat_id].items():
        if trigger in lower_text:
            try:
                await message.reply(response)
                logger.info(f"Auto reply sent: {trigger} -> {response}")
                return
            except Exception as e:
                logger.error(f"Error sending auto reply: {e}")

# ============================================================
# نظام الحماية (القفل)
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

@app.on_message(filters.regex(r'^قفل\s+(.+)$') & filters.group)
async def lock_handler(client, message):
    logger.info(f"Lock command: {message.text}")
    
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    match = re.match(r'^قفل\s+(.+)$', message.text)
    if not match:
        return await message.reply("⚠️ الصيغة: قفل [النوع]")
    
    lock_type = match.group(1).strip()
    
    if lock_type not in LOCK_TYPES:
        types_list = '\n'.join([f"• {k}" for k in LOCK_TYPES.keys()])
        return await message.reply(f"❌ الأنواع المتاحة:\n{types_list}")
    
    settings = get_group_settings(message.chat.id)
    settings['locks'][LOCK_TYPES[lock_type]] = True
    
    await message.reply(f"🔒 تم قفل {lock_type}")

@app.on_message(filters.regex(r'^فتح\s+(.+)$') & filters.group)
async def unlock_handler(client, message):
    logger.info(f"Unlock command: {message.text}")
    
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    match = re.match(r'^فتح\s+(.+)$', message.text)
    if not match:
        return await message.reply("⚠️ الصيغة: فتح [النوع]")
    
    lock_type = match.group(1).strip()
    
    if lock_type not in LOCK_TYPES:
        types_list = '\n'.join([f"• {k}" for k in LOCK_TYPES.keys()])
        return await message.reply(f"❌ الأنواع المتاحة:\n{types_list}")
    
    settings = get_group_settings(message.chat.id)
    settings['locks'][LOCK_TYPES[lock_type]] = False
    
    await message.reply(f"🔓 تم فتح {lock_type}")

# ============================================================
# تطبيق الحماية على الرسائل
# ============================================================

@app.on_message(filters.all & filters.group, group=2)
async def protection_handler(client, message):
    """تطبيق قواعد الحماية"""
    
    if not message.from_user:
        return
    
    try:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status in ["administrator", "creator"]:
            return
    except:
        return
    
    chat_id = message.chat.id
    settings = get_group_settings(chat_id)
    locks = settings.get('locks', {})
    
    # قفل الروابط
    if locks.get('links', False):
        if message.text and ('http' in message.text or 'www' in message.text or 't.me' in message.text):
            try:
                await message.delete()
                await message.reply(f"⚠️ {message.from_user.first_name}، الروابط ممنوعة!")
                return
            except:
                pass
    
    # قفل الصور
    if locks.get('photos', False):
        if message.photo:
            try:
                await message.delete()
                await message.reply(f"⚠️ {message.from_user.first_name}، الصور ممنوعة!")
                return
            except:
                pass
    
    # قفل الفيديو
    if locks.get('videos', False):
        if message.video:
            try:
                await message.delete()
                await message.reply(f"⚠️ {message.from_user.first_name}، الفيديوهات ممنوعة!")
                return
            except:
                pass
    
    # قفل الملفات
    if locks.get('files', False):
        if message.document:
            try:
                await message.delete()
                await message.reply(f"⚠️ {message.from_user.first_name}، الملفات ممنوعة!")
                return
            except:
                pass
    
    # قفل الملصقات
    if locks.get('stickers', False):
        if message.sticker:
            try:
                await message.delete()
                await message.reply(f"⚠️ {message.from_user.first_name}، الملصقات ممنوعة!")
                return
            except:
                pass
    
    # قفل الصوتيات
    if locks.get('voices', False):
        if message.voice or message.audio:
            try:
                await message.delete()
                await message.reply(f"⚠️ {message.from_user.first_name}، الصوتيات ممنوعة!")
                return
            except:
                pass

# ============================================================
# نظام الترحيب
# ============================================================

@app.on_message(filters.new_chat_members & filters.group)
async def welcome_handler(client, message):
    logger.info(f"New member joined: {message.new_chat_members}")
    
    settings = get_group_settings(message.chat.id)
    
    if not settings.get('welcome_enabled', True):
        return
    
    me = await client.get_me()
    
    for new_member in message.new_chat_members:
        if new_member.id == me.id:
            continue
        
        welcome_text = settings['welcome_message'].format(
            user=new_member.first_name,
            group=message.chat.title,
            username=f"@{new_member.username}" if new_member.username else "",
            id=new_member.id
        )
        
        try:
            await message.reply(welcome_text)
            logger.info(f"Welcome sent to {new_member.first_name}")
        except Exception as e:
            logger.error(f"Error sending welcome: {e}")

@app.on_message(filters.regex(r'^تفعيل الترحيب$') & filters.group)
async def enable_welcome_handler(client, message):
    logger.info(f"Enable welcome command")
    
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    settings = get_group_settings(message.chat.id)
    settings['welcome_enabled'] = True
    
    await message.reply("✅ تم تفعيل الترحيب")

@app.on_message(filters.regex(r'^تعطيل الترحيب$') & filters.group)
async def disable_welcome_handler(client, message):
    logger.info(f"Disable welcome command")
    
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    settings = get_group_settings(message.chat.id)
    settings['welcome_enabled'] = False
    
    await message.reply("✅ تم تعطيل الترحيب")

@app.on_message(filters.regex(r'^تعيين رسالة الترحيب\s+(.+)', re.DOTALL) & filters.group)
async def set_welcome_handler(client, message):
    logger.info(f"Set welcome command")
    
    if not await is_admin(client, message.chat.id, message.from_user.id):
        return await message.reply("⚠️ يجب أن تكون مشرفاً!")
    
    match = re.match(r'^تعيين رسالة الترحيب\s+(.+)', message.text, re.DOTALL)
    if not match:
        return await message.reply("⚠️ الصيغة:\nتعيين رسالة الترحيب [نص الترحيب]")
    
    welcome_msg = match.group(1).strip()
    
    settings = get_group_settings(message.chat.id)
    settings['welcome_message'] = welcome_msg
    
    await message.reply(f"✅ تم تعيين رسالة الترحيب:\n\n{welcome_msg}")

# ============================================================
# أمر ا - معلوماتك + صورتك
# ============================================================

@app.on_message(filters.regex(r'^ا$') & filters.group)
async def id_short_handler(client, message):
    """أمر مختصر: ا - يظهر معلوماتك وصورتك فقط"""
    
    target = message.from_user
    chat = message.chat
    
    try:
        member = await client.get_chat_member(chat.id, target.id)
        user_status = member.status
        user_joined_date = member.joined_date.strftime("%Y-%m-%d") if member.joined_date else "غير معروف"
    except:
        user_status = "غير معروف"
        user_joined_date = "غير معروف"
    
    info_text = f"""
┏━ 𝙐𝙎𝙀𝙍 𝙄𝙉𝙁𝙊 ━┓

🆔 **ايدي:** `{target.id}`
👤 **الاسم:** {target.first_name}
📧 **المعرف:** @{target.username if target.username else 'لا يوجد'}
📊 **الحالة:** {user_status}
📅 **الانضمام:** {user_joined_date}
🤖 **النوع:** {'بوت 🤖' if target.is_bot else 'عضو 👤'}

┏━ 𝙂𝙍𝙊𝙐𝙋 𝙄𝙉𝙁𝙊 ━┓

🆔 **ايدي:** `{chat.id}`
📛 **الاسم:** {chat.title}
👥 **الأعضاء:** {await client.get_chat_members_count(chat.id) if chat.type != 'private' else 'N/A'}
    """
    
    try:
        photos = []
        async for photo in client.get_chat_photos(target.id, limit=1):
            photos.append(photo)
        
        if photos:
            await message.reply_photo(
                photo=photos[0].file_id,
                caption=info_text,
                reply_to_message_id=message.id
            )
        else:
            await message.reply(
                info_text + "\n\n📷 **لا توجد صورة**",
                reply_to_message_id=message.id
            )
            
    except Exception as e:
        logger.error(f"Error in id_short: {e}")
        await message.reply(info_text, reply_to_message_id=message.id)

# ============================================================
# أمر اا - صورتك فقط
# ============================================================

@app.on_message(filters.regex(r'^اا$') & filters.group)
async def my_photo_only_handler(client, message):
    """أمر مختصر: اا - يظهر صورة ملفك الشخصي فقط"""
    
    target = message.from_user
    
    try:
        photos = []
        async for photo in client.get_chat_photos(target.id, limit=1):
            photos.append(photo)
        
        if photos:
            await message.reply_photo(
                photo=photos[0].file_id,
                reply_to_message_id=message.id
            )
        else:
            await message.reply(
                "📷 **لا يوجد صورة ملف شخصي**",
                reply_to_message_id=message.id
            )
            
    except Exception as e:
        logger.error(f"Error in my_photo_only: {e}")
        await message.reply(
            "❌ تعذر عرض الصورة",
            reply_to_message_id=message.id
        )

# ============================================================
# أمر افتاره - صورته فقط (يجب الرد)
# ============================================================

@app.on_message(filters.regex(r'^افتاره$') & filters.group)
async def his_photo_handler(client, message):
    """أمر: افتاره - يظهر صورة المستخدم المردود عليه فقط"""
    
    target = await get_target_from_reply(message)
    
    if not target:
        return await message.reply("⚠️ عليك الرد على رسالة الشخص لعرض صورته!")
    
    try:
        photos = []
        async for photo in client.get_chat_photos(target.id, limit=1):
            photos.append(photo)
        
        if photos:
            await message.reply_photo(
                photo=photos[0].file_id,
                reply_to_message_id=message.id
            )
        else:
            await message.reply(
                f"📷 **{target.first_name} ليس لديه صورة ملف شخصي**",
                reply_to_message_id=message.id
            )
            
    except Exception as e:
        logger.error(f"Error in his_photo: {e}")
        await message.reply(
            "❌ تعذر عرض الصورة",
            reply_to_message_id=message.id
        )

# ============================================================
# المساعدة المعدلة
# ============================================================

@app.on_message(filters.regex(r'^مساعدة$|^الاوامر$') | filters.command(["start", "help"]))
async def help_handler(client, message):
    help_text = """
🤖 **أوامر البوت:**

**🎵 الموسيقى (المكالمات الصوتية):**
`تشغيل <اسم الأغنية>` - تشغيل من YouTube
`تخطي` - تخطي الأغنية الحالية
`ايقاف` - إيقاف التشغيل
`ايقاف مؤقت` - إيقاف مؤقت
`استئناف` - استئناف التشغيل
`قائمة التشغيل` - عرض الأغاني في الانتظار
`مغادرة` - مغادرة المكالمة

**👮‍♂️ الإدارة (بالرد):**
`رفع مشرف` `تنزيل مشرف` `حظر` `الغاء حظر`
`كتم` `الغاء كتم` `طرد`

**⚠️ الإنذارات (بالرد):**
`انذار` `عرض انذارات` `مسح انذارات`

**🔒 الحماية:**
`قفل الروابط` `فتح الروابط`
`قفل الصور` `فتح الصور`
`قفل الفيديو` `فتح الفيديو`
`قفل الملفات` `فتح الملفات`
`قفل الملصقات` `فتح الملصقات`
`قفل الصوتيات` `فتح الصوتيات`

**💬 الردود التلقائية:**
`اضافة رد كلمة = الرد`
`حذف رد كلمة`
`عرض الردود`

**👋 الترحيب:**
`تفعيل الترحيب`
`تعطيل الترحيب`
`تعيين رسالة الترحيب [نص]`

**📋 المعلومات:**
`ا` - معلوماتك + صورتك
`اا` - صورتك فقط
`افتاره` (رد) - صورته فقط

**ملاحظة:** جميع الأوامر تعمل في المجموعات فقط!
    """
    
    await message.reply(help_text)

# ============================================================
# تشغيل البوت
# ============================================================

if __name__ == "__main__":
    logger.info("🚀 جاري تشغيل البوت...")
    
    # بدء PyTgCalls
    pytgcalls.start()
    
    # تشغيل البوت
    app.run()
