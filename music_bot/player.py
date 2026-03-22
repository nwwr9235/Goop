"""
music_bot/player.py
محرك التشغيل الصوتي — يستخدم yt-dlp مع دعم كامل للكوكيز
"""

import asyncio
import logging
import os
import traceback
import random
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, AudioQuality, StreamEnded

# ✅ استيراد yt-dlp كأساسي
try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False
    logging.warning("yt-dlp not available")

# ✅ pytube كاحتياطي فقط
try:
    from pytube import YouTube
    from youtubesearchpython import VideosSearch
    PYTUBE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"pytube not available: {e}")
    PYTUBE_AVAILABLE = False

logger = logging.getLogger(__name__)


class MusicPlayer:

    def __init__(self, tgcalls: PyTgCalls, assistant_client=None):
        # ✅ التحقق السريع من موقع الكوكيز (للتصحيح فقط)
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        cookies_path = os.path.join(current_file_dir, "cookies.txt")
        
        print("=" * 60)
        print(f"🔍 DEBUG: This file is at: {os.path.abspath(__file__)}")
        print(f"🔍 DEBUG: Looking for cookies at: {cookies_path}")
        print(f"🔍 DEBUG: File exists: {os.path.exists(cookies_path)}")
        print(f"🔍 DEBUG: Directory contents: {os.listdir(current_file_dir)}")
        print("=" * 60)
        
        self.calls = tgcalls
        self.assistant = assistant_client
        self._register_callbacks()
        
        # ✅ إعدادات yt-dlp المُحسَّنة
        self.ydl_opts_base = {
            "format": "bestaudio*/best*/worstaudio*/worst*",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "socket_timeout": 30,
            "source_address": "0.0.0.0",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "referer": "https://www.youtube.com/",
            "headers": {
                "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            "extractor_args": {
                "youtube": {
                    "player_client": "android_vr",
                    "player_skip": "configs",
                }
            },
            "sleep_requests": 0.5,
            "sleep_interval": 1,
            "max_sleep_interval": 3,
        }
        
        # ✅ إعداد الكوكيز من مجلد music_bot
        self._setup_cookies()
        
        logger.info(f"✅ MusicPlayer initialized (yt-dlp: {YTDLP_AVAILABLE}, pytube: {PYTUBE_AVAILABLE})")

    def _setup_cookies(self):
        """إعداد الكوكيز من مجلد music_bot"""
        
        # ✅ المسار الصحيح: مجلد هذا الملف (music_bot)
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        cookies_path = os.path.join(current_file_dir, "cookies.txt")
        
        if os.path.exists(cookies_path):
            self.ydl_opts_base["cookiefile"] = cookies_path
            logger.info(f"✅ Cookies loaded from: {cookies_path}")
            
            # ✅ التحقق من صحة الملف
            try:
                with open(cookies_path, 'r') as f:
                    lines = f.readlines()
                    logger.info(f"✅ Cookies file has {len(lines)} lines")
            except Exception as e:
                logger.warning(f"⚠️ Cannot read cookies: {e}")
        else:
            logger.error(f"❌ Cookies NOT FOUND at: {cookies_path}")
            # ✅ محاولة المواقع البديلة
            alt_paths = [
                "cookies.txt",
                "/app/cookies.txt",
                "/app/music_bot/cookies.txt",
            ]
            for alt in alt_paths:
                if os.path.exists(alt):
                    self.ydl_opts_base["cookiefile"] = alt
                    logger.info(f"✅ Found cookies at alternative: {alt}")
                    break

    async def play(self, chat_id: int, query: str, user_id: int, invited_by: int = None) -> dict:
        logger.info(f"{'='*50}")
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
            title, stream_url = await self._get_stream_url_with_retry(query)
            logger.info(f"✅ Found: {title}")
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

    async def _get_stream_url_with_retry(self, query: str, max_retries: int = 3) -> tuple[str, str]:
        """الحصول على الرابط مع إعادة المحاولة"""
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Attempt {attempt + 1}/{max_retries}")
                result = await self._get_stream_url(query, attempt)
                
                if result and result[0] and result[1]:
                    return result
                    
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    delay = random.uniform(1, 3)
                    logger.info(f"⏳ Waiting {delay:.1f}s before retry...")
                    await asyncio.sleep(delay)
        
        raise Exception(f"فشل بعد {max_retries} محاولات: {last_error}")

    async def _get_stream_url(self, query: str, attempt: int = 0) -> tuple[str, str]:
        """الحصول على رابط مباشر"""
        
        loop = asyncio.get_event_loop()
        
        # ✅ المحاولة 1: yt-dlp
        if YTDLP_AVAILABLE:
            try:
                opts = self._get_ytdlp_opts_for_attempt(attempt)
                return await loop.run_in_executor(None, self._get_ytdlp_url, query, opts)
            except Exception as e:
                logger.warning(f"⚠️ yt-dlp failed (attempt {attempt}): {e}")
        
        # ✅ المحاولة 2: pytube
        if PYTUBE_AVAILABLE:
            try:
                return await loop.run_in_executor(None, self._get_pytube_url, query)
            except Exception as e:
                logger.warning(f"⚠️ pytube failed: {e}")
        
        raise Exception("جميع المصادر فشلت")

    def _get_ytdlp_opts_for_attempt(self, attempt: int) -> dict:
        """تعديل الإعدادات حسب المحاولة"""
        
        opts = self.ydl_opts_base.copy()
        
        formats = [
            "bestaudio*/best*/worstaudio*/worst*",
            "best*/bestaudio*",
            "worst*",
        ]
        
        if attempt < len(formats):
            opts["format"] = formats[attempt]
            logger.info(f"🔄 Using format: {formats[attempt]}")
        
        if attempt == 2:
            opts["extractor_args"]["youtube"]["player_client"] = "web_embedded"
            logger.info("🔄 Using fallback client: web_embedded")
        
        return opts

    def _get_ytdlp_url(self, query: str, opts: dict = None) -> tuple[str, str]:
        """استخدام yt-dlp"""
        
        if opts is None:
            opts = self.ydl_opts_base
        
        search = query if query.startswith("http") else f"ytsearch1:{query}"
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                logger.info(f"🔍 Extracting: {search[:50]}...")
                
                info = ydl.extract_info(search, download=False)
                
                if info is None:
                    raise Exception("لم يتم استلام معلومات")
                
                if "entries" in info:
                    entries = info["entries"]
                    if not entries or len(entries) == 0:
                        raise Exception("لا توجد نتائج")
                    info = entries[0]
                
                title = info.get('title', query)
                
                # ✅ البحث عن أي رابط متاح
                url = None
                formats = info.get('formats', [])
                
                if formats:
                    audio_only = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
                    video_audio = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') != 'none']
                    any_format = [f for f in formats if f.get('url')]
                    
                    for fmt_list in [audio_only, video_audio, any_format]:
                        if fmt_list:
                            url = fmt_list[0].get('url')
                            if url:
                                logger.info(f"✅ Selected: {fmt_list[0].get('format_id', 'unknown')}")
                                break
                
                if not url:
                    url = info.get('url')
                
                if not url:
                    raise Exception("لا يوجد رابط مباشر")
                
                if not url.startswith('http'):
                    raise Exception(f"رابط غير صالح: {url[:50]}")
                
                logger.info(f"✅ yt-dlp success: {title}")
                return title, url
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ yt-dlp error: {error_msg}")
            
            if "Requested format is not available" in error_msg:
                raise Exception("التنسيق غير متاح")
            elif "Sign in to confirm" in error_msg:
                raise Exception("YouTube يتطلب تسجيل الدخول - تحقق من الكوكيز")
            elif "bot" in error_msg.lower():
                raise Exception("تم كشف البوت")
            else:
                raise

    def _get_pytube_url(self, query: str) -> tuple[str, str]:
        """استخدام pytube - بدون بروكسي"""
        
        if query.startswith("http"):
            try:
                yt = YouTube(query)
                title = yt.title
                
                audio_stream = None
                try:
                    audio_stream = yt.streams.filter(only_audio=True).first()
                except Exception:
                    pass
                
                if not audio_stream:
                    try:
                        audio_stream = yt.streams.get_audio_only()
                    except Exception:
                        pass
                
                if not audio_stream:
                    try:
                        audio_stream = yt.streams.first()
                    except Exception:
                        pass
                
                if not audio_stream:
                    raise Exception("لا يوجد تدفق")
                
                return title, audio_stream.url
                
            except Exception as e:
                raise Exception(f"pytube failed: {e}")
        
        # ✅ البحث
        logger.info(f"🔍 youtube-search: {query}")
        
        try:
            search = VideosSearch(query, limit=5)
            results = search.result()
        except Exception as e:
            raise Exception(f"فشل البحث: {e}")
        
        if not results or not results.get('result'):
            raise Exception("لا توجد نتائج")
        
        for i, video in enumerate(results['result']):
            try:
                video_url = video.get('link')
                if not video_url:
                    continue
                    
                title = video.get('title', 'unknown')
                logger.info(f"🎬 Trying [{i+1}]: {title}")
                
                yt = YouTube(video_url)
                real_title = yt.title
                
                audio_stream = None
                try:
                    audio_stream = yt.streams.filter(only_audio=True).first()
                except Exception:
                    pass
                
                if not audio_stream:
                    try:
                        audio_stream = yt.streams.get_audio_only()
                    except Exception:
                        pass
                
                if not audio_stream:
                    try:
                        audio_stream = yt.streams.first()
                    except Exception:
                        pass
                
                if audio_stream:
                    return real_title, audio_stream.url
                    
            except Exception as e:
                logger.warning(f"⚠️ فشلت {i+1}: {e}")
                continue
        
        raise Exception("جميع نتائج pytube فشلت")

    async def _start_playback(self, chat_id: int) -> dict:
        """بدء التشغيل"""
        gq = queue_manager.get(chat_id)
        track = gq.current()
        
        if not track:
            gq.is_playing = False
            return {"ok": False, "error": "لا يوجد أغنية"}

        gq.is_playing = True
        gq.is_paused = False

        try:
            logger.info(f"▶️ Starting: {track.title}")
            
            stream = MediaStream(
                track.url,
                audio_parameters=AudioQuality.HIGH,
            )
            
            await self.calls.play(chat_id, stream)
            logger.info(f"✅ Playing: {track.title}")
            return {"ok": True}

        except Exception as e:
            logger.error(f"❌ Playback error: {e}")
            gq.is_playing = False
            return {"ok": False, "error": f"فشل التشغيل: {str(e)}"}

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

