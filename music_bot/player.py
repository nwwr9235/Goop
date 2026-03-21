"""
music_bot/player.py
محرك التشغيل الصوتي — مع تسجيل مفصل للأخطاء
"""

import asyncio
import logging
import os
import traceback
import yt_dlp
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, AudioQuality, StreamEnded

logger = logging.getLogger(__name__)

YDL_OPTS = {
    # ✅ bestaudio* يختار أي صيغة صوتية متاحة بدون قيود
    "format": "bestaudio*/best",
    "no_check_formats": True,
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,

    "cookiefile": "/app/cookies.txt",

    "extractor_args": {
        "youtube": {
            "player_client": ["android", "web"]
        }
    },

    "nocheckcertificate": True,
    "ignoreerrors": False,

    "outtmpl": "/tmp/music/%(id)s.%(ext)s",

    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }],
}
os.makedirs("/tmp/music", exist_ok=True)


class MusicPlayer:

    def __init__(self, tgcalls: PyTgCalls, assistant_client: Client = None):
        self.calls = tgcalls
        self.assistant = assistant_client
        self._register_callbacks()
        logger.info("✅ MusicPlayer initialized")

    async def play(self, chat_id: int, query: str, user_id: int, invited_by: int = None) -> dict:
        logger.info(f"="*50)
        logger.info(f"🎵 PLAY REQUEST: chat_id={chat_id}, query='{query}', user_id={user_id}")
        
        # ✅ 1. التحقق من البوت في المجموعة
        if self.assistant:
            try:
                me = await self.assistant.get_me()
                logger.info(f"🤖 Assistant ID: {me.id}, Username: @{me.username}")
                
                try:
                    member = await self.assistant.get_chat_member(chat_id, "me")
                    logger.info(f"✅ Bot is in group, status: {member.status}")
                except Exception as e:
                    logger.error(f"❌ Bot NOT in group {chat_id}: {e}")
                    return {
                        "ok": False, 
                        "error": "البوت المساعد ليس في المجموعة. أضفه أولاً!"
                    }
                    
            except Exception as e:
                logger.error(f"❌ Error checking bot status: {e}")
                return {"ok": False, "error": f"خطأ في التحقق: {str(e)}"}

        # ✅ 2. تنزيل الأغنية
        try:
            logger.info(f"⬇️ Starting download: {query}")
            title, file_path = await self._fetch(query)
            logger.info(f"✅ Download complete: {title} -> {file_path}")
        except Exception as e:
            logger.error(f"❌ DOWNLOAD ERROR: {e}")
            logger.error(traceback.format_exc())
            return {"ok": False, "error": f"فشل التنزيل: {str(e)}"}

        # ✅ 3. التحقق من الملف
        if not os.path.exists(file_path):
            logger.error(f"❌ File not found: {file_path}")
            return {"ok": False, "error": "الملف غير موجود بعد التنزيل"}
        
        file_size = os.path.getsize(file_path)
        logger.info(f"📁 File exists: {file_path}, Size: {file_size} bytes")
        
        if file_size == 0:
            logger.error(f"❌ File is empty!")
            return {"ok": False, "error": "الملف فارغ"}

        # ✅ 4. إضافة للقائمة
        track = Track(title=title, url=file_path, query=query, user_id=user_id)
        gq = queue_manager.get(chat_id)
        pos = gq.add(track)
        logger.info(f"📋 Added to queue at position: {pos}")

        # ✅ 5. بدء التشغيل
        if not gq.is_playing:
            logger.info(f"▶️ No active playback, starting now...")
            result = await self._start_playback(chat_id)
            logger.info(f"🎬 Playback result: {result}")
            if not result["ok"]:
                return result
        else:
            logger.info(f"⏸️ Already playing, added to queue")

        logger.info(f"="*50)
        return {"ok": True, "title": title, "position": pos}

    async def _start_playback(self, chat_id: int) -> dict:
        gq = queue_manager.get(chat_id)
        track = gq.current()
        
        if not track:
            logger.warning(f"⚠️ No track in queue for {chat_id}")
            gq.is_playing = False
            return {"ok": False, "error": "لا يوجد أغنية في القائمة"}

        gq.is_playing = True
        gq.is_paused = False

        try:
            logger.info(f"▶️ STARTING PLAYBACK: {track.title}")
            logger.info(f"📂 File path: {track.url}")
            logger.info(f"📂 File exists: {os.path.exists(track.url)}")
            logger.info(f"📂 File size: {os.path.getsize(track.url)} bytes")
            
            logger.info(f"🔧 Creating MediaStream...")
            stream = MediaStream(
                track.url,
                audio_parameters=AudioQuality.HIGH,
            )
            logger.info(f"✅ MediaStream created")
            
            logger.info(f"🎵 Calling self.calls.play({chat_id}, stream)...")
            await self.calls.play(chat_id, stream)
            logger.info(f"✅ PLAYBACK STARTED: {track.title}")
            return {"ok": True}

        except Exception as e:
            logger.error(f"❌❌❌ PLAYBACK ERROR: {e}")
            logger.error(f"❌ Error type: {type(e).__name__}")
            logger.error(f"❌ Full traceback:\n{traceback.format_exc()}")
            gq.is_playing = False
            return {"ok": False, "error": f"فشل التشغيل: {str(e)}"}

    async def stop(self, chat_id: int) -> dict:
        queue_manager.get(chat_id).clear()
        try:
            await self.calls.leave_call(chat_id)
            logger.info(f"🛑 Stopped and left {chat_id}")
        except Exception as e:
            logger.warning(f"⚠️ Leave error: {e}")
        return {"ok": True}

    async def skip(self, chat_id: int) -> dict:
        gq = queue_manager.get(chat_id)
        next_track = gq.skip()
        if next_track:
            await self._start_playback(chat_id)
            return {"ok": True, "next_title": next_track.title}
        else:
            try:
                await self.calls.leave_call(chat_id)
            except Exception:
                pass
            gq.is_playing = False
            return {"ok": True, "next_title": None}

    async def pause(self, chat_id: int) -> dict:
        try:
            await self.calls.pause_stream(chat_id)
            queue_manager.get(chat_id).is_paused = True
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def resume(self, chat_id: int) -> dict:
        try:
            await self.calls.resume_stream(chat_id)
            queue_manager.get(chat_id).is_paused = False
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_queue(self, chat_id: int) -> dict:
        return {"ok": True, "queue": queue_manager.get(chat_id).to_list()}

    def _register_callbacks(self):
        @self.calls.on_update()
        async def on_stream_ended(_, update):
            if isinstance(update, StreamEnded):
                chat_id = update.chat_id
                logger.info(f"🔴 Stream ended: {chat_id}")
                
                gq = queue_manager.get(chat_id)
                next_track = gq.skip()
                
                if next_track:
                    await self._start_playback(chat_id)
                else:
                    gq.is_playing = False
                    try:
                        await self.calls.leave_call(chat_id)
                    except Exception:
                        pass

    @staticmethod
    async def _fetch(query: str) -> tuple[str, str]:
        is_url = query.startswith("http")
        # ✅ nبحث عن 3 نتائج بدل 1 حتى نتجاوز الفيديوهات المحمية
        search = query if is_url else f"ytsearch3:{query}"
        loop = asyncio.get_event_loop()

        def _try_download(video_url: str, title_hint: str) -> tuple[str, str]:
            """محاولة تحميل فيديو واحد"""
            opts = {**YDL_OPTS, "noplaylist": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                if info is None:
                    raise Exception("فشل التحميل")
                title = info.get("title", title_hint)
                file_path = ydl.prepare_filename(info)
                if file_path.endswith(('.webm', '.m4a', '.mp4', '.weba')):
                    file_path = file_path.rsplit('.', 1)[0] + '.mp3'
                if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                    raise Exception("الملف فارغ أو غير موجود")
                return title, file_path

        def _download():
            logger.info(f"🔍 yt-dlp searching: {search}")

            # الخطوة 1: جلب قائمة النتائج بدون تحميل
            info_opts = {
                "quiet": True,
                "no_warnings": True,
                "cookiefile": "/app/cookies.txt",
                "nocheckcertificate": True,
                "skip_download": True,
                "extract_flat": True,
            }
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                results = ydl.extract_info(search, download=False)

            if results is None:
                raise Exception("لا توجد نتائج للبحث")

            # استخراج قائمة الفيديوهات
            if is_url:
                entries = [results]
            else:
                entries = results.get("entries", [])
                entries = [e for e in entries if e is not None]

            if not entries:
                raise Exception("لا توجد نتائج صالحة")

            logger.info(f"📋 وجدت {len(entries)} نتيجة، أجرّب كل واحدة...")

            # الخطوة 2: جرّب كل نتيجة حتى تنجح واحدة
            last_error = None
            for i, entry in enumerate(entries):
                video_id = entry.get("id", "")
                video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id and not video_id.startswith("http") else entry.get("url", video_id)
                title_hint = entry.get("title", query)
                logger.info(f"⬇️ محاولة [{i+1}/{len(entries)}]: {title_hint}")
                try:
                    title, file_path = _try_download(video_url, title_hint)
                    logger.info(f"✅ نجحت: {title} -> {file_path}")
                    return title, file_path
                except Exception as e:
                    logger.warning(f"⚠️ فشلت [{i+1}]: {e} — أجرّب التالية...")
                    last_error = e
                    continue

            raise Exception(f"فشلت جميع النتائج. آخر خطأ: {last_error}")

        return await loop.run_in_executor(None, _download)


# الكلاسات المساعدة
class Track:
    def __init__(self, title: str, url: str, query: str, user_id: int):
        self.title = title
        self.url = url
        self.query = query
        self.user_id = user_id

class QueueManager:
    def __init__(self):
        self._queues = {}
    
    def get(self, chat_id: int):
        if chat_id not in self._queues:
            self._queues[chat_id] = GroupQueue()
        return self._queues[chat_id]

queue_manager = QueueManager()

class GroupQueue:
    def __init__(self):
        self.tracks = []
        self.is_playing = False
        self.is_paused = False
        self.current_index = -1
    
    def add(self, track: Track) -> int:
        self.tracks.append(track)
        # ✅ إصلاح #3: عند إضافة أول أغنية، اضبط الـ index على 0
        if self.current_index == -1:
            self.current_index = 0
        return len(self.tracks)
    
    def current(self) -> Track | None:
        if 0 <= self.current_index < len(self.tracks):
            return self.tracks[self.current_index]
        return None
    
    def skip(self) -> Track | None:
        self.current_index += 1
        return self.current()
    
    def clear(self):
        self.tracks = []
        self.current_index = -1
        self.is_playing = False
    
    def to_list(self):
        return [{"title": t.title, "user_id": t.user_id} for t in self.tracks]
