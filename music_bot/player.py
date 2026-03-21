"""
music_bot/player.py
محرك التشغيل الصوتي — يستخدم MediaStream (الموجود في py-tgcalls 2.2.11)
"""

import asyncio
import logging
import os
import traceback
import yt_dlp
from pyrogram import Client
from pytgcalls import PyTgCalls

# ✅ استخدام MediaStream (الموجود) بدلاً من AudioPiped (غير موجود)
from pytgcalls.types import MediaStream, AudioQuality, StreamEnded

logger = logging.getLogger(__name__)

YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
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
        logger.info(f"🎵 Play request: chat={chat_id}, query={query}")
        
        # التحقق من البوت في المجموعة
        if self.assistant:
            try:
                me = await self.assistant.get_me()
                member = await self.assistant.get_chat_member(chat_id, "me")
                logger.info(f"✅ Bot status: {member.status}")
            except Exception as e:
                logger.error(f"❌ Bot not in group: {e}")
                return {"ok": False, "error": f"البوت ليس في المجموعة: {str(e)}"}

        # تنزيل الأغنية
        try:
            logger.info(f"⬇️ Downloading: {query}")
            title, file_path = await self._fetch(query)
            logger.info(f"✅ Downloaded: {title}")
        except Exception as e:
            logger.error(f"❌ Download error: {e}")
            return {"ok": False, "error": f"فشل التنزيل: {str(e)}"}

        if not os.path.exists(file_path):
            return {"ok": False, "error": "الملف غير موجود بعد التنزيل"}
        
        file_size = os.path.getsize(file_path)
        logger.info(f"📁 File size: {file_size} bytes")
        if file_size == 0:
            return {"ok": False, "error": "الملف فارغ"}

        # إضافة للقائمة
        track = Track(title=title, url=file_path, query=query, user_id=user_id)
        gq = queue_manager.get(chat_id)
        pos = gq.add(track)

        if not gq.is_playing:
            result = await self._start_playback(chat_id)
            if not result["ok"]:
                return result

        return {"ok": True, "title": title, "position": pos}

    async def _start_playback(self, chat_id: int) -> dict:
        gq = queue_manager.get(chat_id)
        track = gq.current()
        
        if not track:
            gq.is_playing = False
            return {"ok": False, "error": "لا يوجد أغنية في القائمة"}

        gq.is_playing = True
        gq.is_paused = False

        try:
            logger.info(f"▶️ Starting: {track.title}")
            
            # ✅ استخدام MediaStream (الموجود في py-tgcalls 2.2.11)
            stream = MediaStream(
                track.url,
                audio_parameters=AudioQuality.HIGH,  # ✅ AudioQuality موجود
            )
            
            await self.calls.play(chat_id, stream)
            logger.info(f"✅ Playing: {track.title}")
            return {"ok": True}

        except Exception as e:
            logger.error(f"❌ Playback error: {e}")
            logger.error(traceback.format_exc())
            gq.is_playing = False
            return {"ok": False, "error": f"فشل التشغيل: {str(e)}"}

    async def stop(self, chat_id: int) -> dict:
        queue_manager.get(chat_id).clear()
        try:
            await self.calls.leave_call(chat_id)
        except Exception as e:
            logger.warning(f"Leave error: {e}")
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
        search = query if query.startswith("http") else f"ytsearch1:{query}"
        loop = asyncio.get_event_loop()

        def _download():
            with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                info = ydl.extract_info(search, download=True)
                if "entries" in info:
                    info = info["entries"][0]
                title = info.get("title", query)
                file_path = ydl.prepare_filename(info)
                
                if file_path.endswith(('.webm', '.m4a', '.mp4', '.weba')):
                    file_path = file_path.rsplit('.', 1)[0] + '.mp3'
                
                return title, file_path

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
