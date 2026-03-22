"""
music_bot/player.py
محرك التشغيل الصوتي — يستخدم pytube + youtube-search
"""

import asyncio
import logging
import os
import traceback
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, AudioQuality, StreamEnded

# ✅ استيراد pytube و youtube-search
try:
    from pytube import YouTube
    from youtubesearchpython import VideosSearch
    PYTUBE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"pytube not available: {e}")
    PYTUBE_AVAILABLE = False

# ✅ yt-dlp كـ fallback
try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False

logger = logging.getLogger(__name__)


class MusicPlayer:

    def __init__(self, tgcalls: PyTgCalls, assistant_client=None):
        self.calls = tgcalls
        self.assistant = assistant_client
        self._register_callbacks()
        logger.info(f"✅ MusicPlayer initialized (pytube: {PYTUBE_AVAILABLE}, yt-dlp: {YTDLP_AVAILABLE})")

    async def play(self, chat_id: int, query: str, user_id: int, invited_by: int = None) -> dict:
        logger.info(f"="*50)
        logger.info(f"🎵 PLAY REQUEST: chat_id={chat_id}, query='{query}', user_id={user_id}")
        
        # التحقق من البوت في المجموعة
        if self.assistant:
            try:
                me = await self.assistant.get_me()
                member = await self.assistant.get_chat_member(chat_id, "me")
                logger.info(f"✅ Bot status: {member.status}")
            except Exception as e:
                logger.error(f"❌ Bot not in group: {e}")
                return {"ok": False, "error": f"البوت ليس في المجموعة: {str(e)}"}

        # ✅ جلب رابط الأغنية
        try:
            logger.info(f"🔍 Searching for: {query}")
            title, stream_url = await self._get_stream_url(query)
            logger.info(f"✅ Found: {title} -> {stream_url[:50]}...")
        except Exception as e:
            logger.error(f"❌ SEARCH ERROR: {e}")
            logger.error(traceback.format_exc())
            return {"ok": False, "error": f"فشل جلب الأغنية: {str(e)}"}

        # إضافة للقائمة والتشغيل
        track = Track(title=title, url=stream_url, query=query, user_id=user_id)
        gq = queue_manager.get(chat_id)
        pos = gq.add(track)

        if not gq.is_playing:
            result = await self._start_playback(chat_id)
            if not result["ok"]:
                return result

        return {"ok": True, "title": title, "position": pos}

    async def _get_stream_url(self, query: str) -> tuple[str, str]:
        """الحصول على رابط مباشر باستخدام pytube أولاً"""
        
        loop = asyncio.get_event_loop()
        
        # ✅ المحاولة 1: pytube (الأسرع)
        if PYTUBE_AVAILABLE:
            try:
                return await loop.run_in_executor(None, self._get_pytube_url, query)
            except Exception as e:
                logger.warning(f"⚠️ pytube failed: {e}")
        
        # ✅ المحاولة 2: yt-dlp (fallback)
        if YTDLP_AVAILABLE:
            try:
                return await loop.run_in_executor(None, self._get_ytdlp_url, query)
            except Exception as e:
                logger.warning(f"⚠️ yt-dlp failed: {e}")
        
        raise Exception("جميع المصادر فشلت")

    def _get_pytube_url(self, query: str) -> tuple[str, str]:
        """استخدام pytube للحصول على رابط مباشر"""
        
        # إذا كان الرابط مباشر
        if query.startswith("http"):
            video_url = query
        else:
            # ✅ البحث باستخدام youtube-search-python
            logger.info(f"🔍 youtube-search: {query}")
            search = VideosSearch(query, limit=3)  # 3 نتائج للتأكد
            
            results = search.result()
            if not results or not results.get('result'):
                raise Exception("لا توجد نتائج بحث")
            
            # تجربة النتائج حتى نجد واحدة تعمل
            for video in results['result']:
                try:
                    video_url = video['link']
                    title = video['title']
                    logger.info(f"🎬 Trying: {title}")
                    
                    # ✅ التحقق من pytube
                    yt = YouTube(video_url)
                    
                    # الحصول على أول تدفق صوتي
                    audio_stream = yt.streams.filter(only_audio=True).first()
                    if not audio_stream:
                        audio_stream = yt.streams.get_audio_only()
                    
                    if audio_stream:
                        direct_url = audio_stream.url
                        logger.info(f"✅ pytube success: {title}")
                        return title, direct_url
                        
                except Exception as e:
                    logger.warning(f"⚠️ فشلت {video.get('title', 'unknown')}: {e}")
                    continue
            
            raise Exception("جميع نتائج pytube فشلت")
        
        # إذا كان رابط مباشر
        yt = YouTube(video_url)
        title = yt.title
        audio_stream = yt.streams.filter(only_audio=True).first()
        
        if not audio_stream:
            raise Exception("لا يوجد تدفق صوتي")
        
        return title, audio_stream.url

    def _get_ytdlp_url(self, query: str) -> tuple[str, str]:
        """fallback باستخدام yt-dlp"""
        
        search = query if query.startswith("http") else f"ytsearch1:{query}"
        
        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search, download=False)
            if "entries" in info:
                info = info["entries"][0]
            
            title = info.get('title', query)
            url = info.get('url')
            
            if not url:
                formats = info.get('formats', [])
                if formats:
                    url = formats[0].get('url')
            
            if not url:
                raise Exception("لا يوجد رابط مباشر")
            
            return title, url

    async def _start_playback(self, chat_id: int) -> dict:
        """بدء التشغيل"""
        gq = queue_manager.get(chat_id)
        track = gq.current()
        
        if not track:
            gq.is_playing = False
            return {"ok": False, "error": "لا يوجد أغنية في القائمة"}

        gq.is_playing = True
        gq.is_paused = False

        try:
            logger.info(f"▶️ Starting playback: {track.title}")
            
            stream = MediaStream(
                track.url,
                audio_parameters=AudioQuality.HIGH,
            )
            
            await self.calls.play(chat_id, stream)
            logger.info(f"✅ Playing: {track.title}")
            return {"ok": True}

        except Exception as e:
            logger.error(f"❌ Playback error: {e}")
            logger.error(traceback.format_exc())
            gq.is_playing = False
            return {"ok": False, "error": f"فشل التشغيل: {str(e)}"}

    # ... بقية الدوال (stop, skip, pause, resume, get_queue) كما هي ...

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


# ✅ الكلاسات المساعدة
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
