"""
music_bot/player.py
محرك التشغيل الصوتي — مع حلول شاملة لجميع المشاكل
"""

import asyncio
import logging
import os
import traceback
import random
import time
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, AudioQuality, StreamEnded

try:
    import yt_dlp
    YTDLP_AVAILABLE = True
except ImportError:
    YTDLP_AVAILABLE = False
    logging.warning("yt-dlp not available")

try:
    from pytube import YouTube
    PYTUBE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"pytube not available: {e}")
    PYTUBE_AVAILABLE = False

# ✅ محاولة استيراد youtube-search بدون بروكسي
try:
    from youtubesearchpython import VideosSearch
    YTSEARCH_AVAILABLE = True
except ImportError as e:
    logging.warning(f"youtube-search not available: {e}")
    YTSEARCH_AVAILABLE = False

logger = logging.getLogger(__name__)


class MusicPlayer:

    def __init__(self, tgcalls: PyTgCalls, assistant_client=None):
        # ✅ تصحيح: طباعة معلومات الكوكيز
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        cookies_path = os.path.join(current_file_dir, "cookies.txt")
        
        print("=" * 60)
        print(f"🔍 DEBUG: File: {os.path.abspath(__file__)}")
        print(f"🔍 DEBUG: Cookies: {cookies_path}")
        print(f"🔍 DEBUG: Exists: {os.path.exists(cookies_path)}")
        print("=" * 60)
        
        self.calls = tgcalls
        self.assistant = assistant_client
        self._register_callbacks()
        
        # ✅ إعدادات yt-dlp المُحسَّنة جداً
        self.ydl_opts_base = {
            # ✅ تنسيق بسيط جداً - أي تنسيق يعمل
            "format": "best/bestaudio/worst",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "socket_timeout": 30,
            "source_address": "0.0.0.0",
            
            # ✅ محاكاة متصفح حقيقي
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "referer": "https://www.youtube.com/",
            "headers": {
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
            },
            
            # ✅ إعدادات YouTube محسّنة
            "extractor_args": {
                "youtube": {
                    "player_client": "android_vr",
                    "player_skip": "configs,webpage",
                }
            },
            
            # ✅ تأخيرات
            "sleep_requests": 1,
            "sleep_interval": 2,
        }
        
        # ✅ إعداد الكوكيز
        self._setup_cookies(cookies_path)
        
        logger.info(f"✅ MusicPlayer initialized")

    def _setup_cookies(self, primary_path):
        """إعداد الكوكيز"""
        
        if os.path.exists(primary_path):
            self.ydl_opts_base["cookiefile"] = primary_path
            logger.info(f"✅ Cookies: {primary_path}")
            
            # ✅ التحقق من صلاحية الكوكيز (قراءة أول سطر)
            try:
                with open(primary_path, 'r') as f:
                    content = f.read()
                    lines = [l for l in content.split('\n') if l.strip() and not l.startswith('#')]
                    logger.info(f"✅ Cookies file: {len(lines)} valid lines")
                    
                    # ✅ تحذير إذا كان الملف قديماً
                    if "youtube.com" not in content:
                        logger.warning("⚠️ Cookies may be invalid (no youtube.com found)")
                        
            except Exception as e:
                logger.warning(f"⚠️ Cannot read cookies: {e}")
        else:
            logger.error(f"❌ Cookies NOT found: {primary_path}")

    async def play(self, chat_id: int, query: str, user_id: int, invited_by: int = None) -> dict:
        logger.info(f"🎵 PLAY: chat_id={chat_id}, query='{query}'")
        
        # التحقق من البوت
        if self.assistant:
            try:
                member = await self.assistant.get_chat_member(chat_id, "me")
                logger.info(f"✅ Bot status: {member.status}")
            except Exception as e:
                return {"ok": False, "error": f"البوت ليس في المجموعة: {str(e)}"}

        # ✅ جلب الرابط
        try:
            title, stream_url = await self._get_stream_url_with_retry(query)
            logger.info(f"✅ Found: {title[:50]}...")
        except Exception as e:
            logger.error(f"❌ SEARCH ERROR: {e}")
            return {"ok": False, "error": f"فشل جلب الأغنية: {str(e)}"}

        # إضافة للقائمة
        track = Track(title=title, url=stream_url, query=query, user_id=user_id)
        gq = queue_manager.get(chat_id)
        pos = gq.add(track)

        if not gq.is_playing:
            result = await self._start_playback(chat_id)
            if not result["ok"]:
                return result

        return {"ok": True, "title": title, "position": pos}

    async def _get_stream_url_with_retry(self, query: str, max_retries: int = 3) -> tuple[str, str]:
        """محاولة متعددة مع استراتيجيات مختلفة"""
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 Attempt {attempt + 1}/{max_retries}")
                
                # ✅ تغيير الاستراتيجية في كل محاولة
                result = await self._get_stream_url(query, attempt)
                
                if result and result[0] and result[1]:
                    return result
                    
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Attempt {attempt + 1} failed: {str(e)[:100]}")
                
                if attempt < max_retries - 1:
                    delay = random.uniform(2, 5)
                    logger.info(f"⏳ Waiting {delay:.1f}s...")
                    await asyncio.sleep(delay)
        
        raise Exception(f"فشل بعد {max_retries} محاولات: {last_error}")

    async def _get_stream_url(self, query: str, attempt: int = 0) -> tuple[str, str]:
        """استراتيجيات متعددة — يوتيوب أولاً ثم SoundCloud"""
        
        loop = asyncio.get_event_loop()
        
        # ✅ استراتيجية 1: yt-dlp YouTube
        if YTDLP_AVAILABLE:
            try:
                opts = self._get_ytdlp_opts_for_attempt(attempt)
                return await loop.run_in_executor(None, self._get_ytdlp_url, query, opts)
            except Exception as e:
                logger.warning(f"⚠️ yt-dlp YouTube failed: {str(e)[:80]}")
        
        # ✅ استراتيجية 2: SoundCloud عبر yt-dlp
        if YTDLP_AVAILABLE:
            try:
                logger.info(f"🎵 Trying SoundCloud for: {query}")
                return await loop.run_in_executor(None, self._get_soundcloud_url, query)
            except Exception as e:
                logger.warning(f"⚠️ SoundCloud failed: {str(e)[:80]}")

        # ✅ استراتيجية 3: pytube مباشر
        if PYTUBE_AVAILABLE and query.startswith("http"):
            try:
                return await loop.run_in_executor(None, self._get_pytube_direct, query)
            except Exception as e:
                logger.warning(f"⚠️ pytube direct failed: {e}")
        
        # ✅ استراتيجية 4: yt-dlp بدون كوكيز
        if attempt >= 2 and YTDLP_AVAILABLE:
            try:
                opts = self.ydl_opts_base.copy()
                if "cookiefile" in opts:
                    del opts["cookiefile"]
                opts["extractor_args"]["youtube"]["player_client"] = "web_embedded"
                return await loop.run_in_executor(None, self._get_ytdlp_url, query, opts)
            except Exception as e:
                logger.warning(f"⚠️ yt-dlp no-cookies failed: {e}")
        
        raise Exception("جميع المصادر فشلت — يوتيوب و SoundCloud")

    def _get_ytdlp_opts_for_attempt(self, attempt: int) -> dict:
        """تغيير الإعدادات حسب المحاولة"""
        
        opts = self.ydl_opts_base.copy()
        
        # ✅ تغيير التنسيق
        formats = ["best", "bestaudio", "worst", "18"]  # 18 = 360p MP4
        if attempt < len(formats):
            opts["format"] = formats[attempt]
            logger.info(f"🔄 Format: {formats[attempt]}")
        
        # ✅ تغيير العميل
        clients = ["android_vr", "web_safari", "web_embedded"]
        if attempt < len(clients):
            opts["extractor_args"]["youtube"]["player_client"] = clients[attempt]
            logger.info(f"🔄 Client: {clients[attempt]}")
        
        # ✅ المحاولة الأخيرة: بدون كوكيز
        if attempt == 2 and "cookiefile" in opts:
            del opts["cookiefile"]
            logger.info("🔄 No cookies")
        
        return opts

    def _get_ytdlp_url(self, query: str, opts: dict) -> tuple[str, str]:
        """yt-dlp مع معالجة أخطاء محسّنة"""
        
        search = query if query.startswith("http") else f"ytsearch1:{query}"
        
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                logger.info(f"🔍 yt-dlp: {search[:40]}...")
                
                info = ydl.extract_info(search, download=False)
                
                if not info:
                    raise Exception("No info returned")
                
                if "entries" in info:
                    entries = info["entries"]
                    if not entries:
                        raise Exception("No results")
                    info = entries[0]
                
                title = info.get('title', 'Unknown')
                
                # ✅ البحث عن الرابط بأي طريقة
                url = None
                
                # 1. من التنسيقات
                formats = info.get('formats', [])
                if formats:
                    # أي تنسيق يعمل
                    for f in formats:
                        url = f.get('url')
                        if url and url.startswith('http'):
                            logger.info(f"✅ Format: {f.get('format_id', 'unknown')}")
                            break
                
                # 2. الرابط المباشر
                if not url:
                    url = info.get('url')
                
                if not url or not url.startswith('http'):
                    raise Exception("No valid URL found")
                
                logger.info(f"✅ yt-dlp success: {title[:40]}")
                return title, url
                
        except Exception as e:
            error = str(e)
            
            # ✅ تحليل الخطأ
            if "format is not available" in error:
                raise Exception("Format not available - try different video")
            elif "Sign in" in error:
                raise Exception("Sign in required - cookies invalid")
            elif "bot" in error.lower():
                raise Exception("Bot detected by YouTube")
            else:
                raise Exception(f"yt-dlp: {error[:80]}")


    def _get_soundcloud_url(self, query: str) -> tuple[str, str]:
        """البحث في SoundCloud عبر yt-dlp"""
        
        sc_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "socket_timeout": 30,
        }
        
        # البحث في SoundCloud
        search = f"scsearch1:{query}"
        logger.info(f"🔍 SoundCloud search: {query}")
        
        with yt_dlp.YoutubeDL(sc_opts) as ydl:
            info = ydl.extract_info(search, download=False)
            
            if not info:
                raise Exception("No SoundCloud results")
            
            if "entries" in info:
                entries = [e for e in info["entries"] if e]
                if not entries:
                    raise Exception("No SoundCloud entries")
                info = entries[0]
            
            title = info.get("title", query)
            
            # استخراج الرابط المباشر
            formats = info.get("formats", [])
            url = None
            
            for f in formats:
                u = f.get("url", "")
                if u and u.startswith("http"):
                    url = u
                    break
            
            if not url:
                url = info.get("url", "")
            
            if not url:
                raise Exception("No SoundCloud URL found")
            
            logger.info(f"✅ SoundCloud found: {title[:50]}")
            return title, url

    def _get_pytube_direct(self, url: str) -> tuple[str, str]:
        """pytube مباشر بدون بحث"""
        
        try:
            yt = YouTube(url)
            title = yt.title
            
            # ✅ محاولة جميع الطرق
            stream = None
            
            methods = [
                lambda: yt.streams.filter(only_audio=True).first(),
                lambda: yt.streams.get_audio_only(),
                lambda: yt.streams.first(),
            ]
            
            for method in methods:
                try:
                    stream = method()
                    if stream:
                        break
                except Exception:
                    continue
            
            if not stream:
                raise Exception("No stream found")
            
            return title, stream.url
            
        except Exception as e:
            raise Exception(f"pytube: {e}")

    async def _start_playback(self, chat_id: int) -> dict:
        """بدء التشغيل"""
        gq = queue_manager.get(chat_id)
        track = gq.current()
        
        if not track:
            return {"ok": False, "error": "لا يوجد أغنية"}

        gq.is_playing = True

        try:
            stream = MediaStream(
                track.url,
                audio_parameters=AudioQuality.HIGH,
            )
            
            await self.calls.play(chat_id, stream)
            logger.info(f"✅ Playing: {track.title[:40]}")
            return {"ok": True}

        except Exception as e:
            logger.error(f"❌ Playback: {e}")
            gq.is_playing = False
            return {"ok": False, "error": f"فشل التشغيل: {str(e)}"}

    def _register_callbacks(self):
        @self.calls.on_update()
        async def on_stream_ended(_, update):
            if isinstance(update, StreamEnded):
                chat_id = update.chat_id
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
        # ✅ ضبط الـ index عند إضافة أول أغنية
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

