"""
music_bot/player.py
محرك التشغيل الصوتي — Streaming مباشر بدون تحميل
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

# ✅ إعدادات Streaming — بدون تحميل
YDL_OPTS = {
    "format": "bestaudio*/best",
    "no_check_formats": True,
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "cookiefile": "/app/cookies.txt",
    "extractor_args": {
        "youtube": {
            "player_client": ["tv_embedded", "mweb"]
        }
    },
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "skip_download": True,
    # ✅ البروكسي لتجاوز حجب يوتيوب على السيرفرات السحابية
    "proxy": os.environ.get("PROXY_URL", ""),
}


class MusicPlayer:

    def __init__(self, tgcalls: PyTgCalls, assistant_client: Client = None):
        self.calls = tgcalls
        self.assistant = assistant_client
        self._register_callbacks()
        logger.info("✅ MusicPlayer initialized")

    async def play(self, chat_id: int, query: str, user_id: int, invited_by: int = None) -> dict:
        logger.info("=" * 50)
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
                    return {"ok": False, "error": "البوت المساعد ليس في المجموعة. أضفه أولاً!"}
            except Exception as e:
                logger.error(f"❌ Error checking bot status: {e}")
                return {"ok": False, "error": f"خطأ في التحقق: {str(e)}"}

        # ✅ 2. جلب رابط الـ Stream
        try:
            logger.info(f"🔗 Getting stream URL: {query}")
            title, stream_url = await self._get_stream_url(query)
            logger.info(f"✅ Got stream URL: {title}")
        except Exception as e:
            logger.error(f"❌ STREAM ERROR: {e}")
            logger.error(traceback.format_exc())
            return {"ok": False, "error": f"فشل جلب الأغنية: {str(e)}"}

        # ✅ 3. إضافة للقائمة
        track = Track(title=title, url=stream_url, query=query, user_id=user_id)
        gq = queue_manager.get(chat_id)
        pos = gq.add(track)
        logger.info(f"📋 Added to queue at position: {pos}")

        # ✅ 4. بدء التشغيل
        if not gq.is_playing:
            logger.info("▶️ No active playback, starting now...")
            result = await self._start_playback(chat_id)
            logger.info(f"🎬 Playback result: {result}")
            if not result["ok"]:
                return result
        else:
            logger.info("⏸️ Already playing, added to queue")

        logger.info("=" * 50)
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
            logger.info(f"▶️ STARTING STREAM: {track.title}")
            logger.info(f"🔗 Stream URL: {track.url[:80]}...")

            # ✅ Streaming مباشر من الرابط
            stream = MediaStream(
                track.url,
                audio_parameters=AudioQuality.HIGH,
            )
            logger.info("✅ MediaStream created")

            await self.calls.play(chat_id, stream)
            logger.info(f"✅ STREAMING STARTED: {track.title}")
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
    async def _get_stream_url(query: str) -> tuple[str, str]:
        """جلب رابط الـ Stream مباشرة بدون تحميل"""
        is_url = query.startswith("http")
        search = query if is_url else f"ytsearch3:{query}"
        loop = asyncio.get_event_loop()

        def _fetch():
            logger.info(f"🔍 yt-dlp searching: {search}")

            # الخطوة 1: جلب قائمة النتائج
            info_opts = {
                "quiet": True,
                "no_warnings": True,
                "cookiefile": "/app/cookies.txt",
                "nocheckcertificate": True,
                "extract_flat": True,
                "skip_download": True,
                "proxy": os.environ.get("PROXY_URL", ""),
            }
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                results = ydl.extract_info(search, download=False)

            if results is None:
                raise Exception("لا توجد نتائج للبحث")

            if is_url:
                entries = [results]
            else:
                entries = results.get("entries", [])
                entries = [e for e in entries if e is not None]

            if not entries:
                raise Exception("لا توجد نتائج صالحة")

            logger.info(f"📋 وجدت {len(entries)} نتيجة، أجرّب كل واحدة...")

            # الخطوة 2: جرّب كل نتيجة حتى تنجح
            last_error = None
            for i, entry in enumerate(entries):
                video_id = entry.get("id", "")
                video_url = (
                    f"https://www.youtube.com/watch?v={video_id}"
                    if video_id and not video_id.startswith("http")
                    else entry.get("url", video_id)
                )
                title_hint = entry.get("title", query)
                logger.info(f"🔗 محاولة [{i+1}/{len(entries)}]: {title_hint}")

                try:
                    # ✅ جلب الرابط المباشر بدون تحميل
                    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                        info = ydl.extract_info(video_url, download=False)

                    if info is None:
                        raise Exception("فشل جلب معلومات الفيديو")

                    # ✅ استخراج أفضل رابط صوتي مباشر
                    formats = info.get("formats", [])

                    # أولاً: صوت فقط بدون فيديو
                    audio_formats = [
                        f for f in formats
                        if f.get("acodec") != "none"
                        and f.get("vcodec") == "none"
                        and f.get("url")
                    ]

                    # إذا لم يجد صوت فقط، خذ أي format فيه صوت
                    if not audio_formats:
                        audio_formats = [
                            f for f in formats
                            if f.get("url") and f.get("acodec") != "none"
                        ]

                    if not audio_formats:
                        raise Exception("لا يوجد رابط صوتي متاح")

                    # اختر أفضل جودة
                    best = sorted(
                        audio_formats,
                        key=lambda f: f.get("abr") or f.get("tbr") or 0,
                        reverse=True
                    )[0]

                    stream_url = best["url"]
                    title = info.get("title", title_hint)

                    logger.info(f"✅ نجحت: {title}")
                    return title, stream_url

                except Exception as e:
                    logger.warning(f"⚠️ فشلت [{i+1}]: {e} — أجرّب التالية...")
                    last_error = e
                    continue

            raise Exception(f"فشلت جميع النتائج. آخر خطأ: {last_error}")

        return await loop.run_in_executor(None, _fetch)


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
