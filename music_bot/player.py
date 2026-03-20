"""
music_bot/player.py
محرك التشغيل الصوتي — يتحكم في PyTgCalls
"""

import asyncio
import logging
import os
import yt_dlp
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
from music_bot.queue_manager import queue_manager, Track

logger = logging.getLogger(__name__)

# ─── إعداد yt-dlp ────────────────────────────────────────────────
YDL_OPTS = {
    "format":            "bestaudio/best",
    "noplaylist":        True,
    "quiet":             True,
    "no_warnings":       True,
    "extract_flat":      False,
    "postprocessors": [{
        "key":            "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }],
    "outtmpl": "/tmp/music/%(id)s.%(ext)s",
}

os.makedirs("/tmp/music", exist_ok=True)


class MusicPlayer:
    """
    يتولى التحكم الكامل في Voice Chat:
    - تنزيل الأغاني عبر yt-dlp
    - تشغيلها عبر PyTgCalls
    - الانتقال التلقائي للأغنية التالية
    """

    def __init__(self, tgcalls: PyTgCalls):
        self.calls = tgcalls
        self._register_callbacks()

    # ---------------------------------------------------------------- #
    # واجهة عامة
    # ---------------------------------------------------------------- #

    async def play(self, chat_id: int, query: str, user_id: int) -> dict:
        """
        إضافة أغنية للقائمة وبدء التشغيل إن لم يكن هناك شيء يُشغَّل.
        يُرجع: {"ok": True, "title": ..., "position": ...}
        """
        try:
            title, file_path = await self._fetch(query)
        except Exception as e:
            logger.error(f"yt-dlp error: {e}")
            return {"ok": False, "error": f"فشل التنزيل: {e}"}

        track = Track(title=title, url=file_path, query=query, user_id=user_id)
        gq    = queue_manager.get(chat_id)
        pos   = gq.add(track)

        if not gq.is_playing:
            await self._start_playback(chat_id)

        return {"ok": True, "title": title, "position": pos}

    async def stop(self, chat_id: int) -> dict:
        gq = queue_manager.get(chat_id)
        gq.clear()
        try:
            await self.calls.leave_call(chat_id)
        except Exception:
            pass
        return {"ok": True}

    async def skip(self, chat_id: int) -> dict:
        gq   = queue_manager.get(chat_id)
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

    # ---------------------------------------------------------------- #
    # دوال داخلية
    # ---------------------------------------------------------------- #

    async def _start_playback(self, chat_id: int):
        gq    = queue_manager.get(chat_id)
        track = gq.current()
        if not track:
            gq.is_playing = False
            return
        gq.is_playing = True
        gq.is_paused  = False
        try:
            await self.calls.play(
                chat_id,
                MediaStream(track.url),
            )
            logger.info(f"▶️ تشغيل في {chat_id}: {track.title}")
        except Exception as e:
            logger.error(f"خطأ في التشغيل: {e}")
            gq.is_playing = False

    def _register_callbacks(self):
        """الانتقال التلقائي عند انتهاء الأغنية"""
        @self.calls.on_stream_end()
        async def on_stream_end(_, update):
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
                logger.info(f"✅ انتهت القائمة في {chat_id}")

    @staticmethod
    async def _fetch(query: str) -> tuple[str, str]:
        """
        تنزيل الأغنية وإرجاع (title, file_path).
        يدعم: اسم الأغنية، رابط YouTube.
        """
        search = query if query.startswith("http") else f"ytsearch1:{query}"
        loop = asyncio.get_event_loop()

        def _download():
            with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                info = ydl.extract_info(search, download=True)
                if "entries" in info:
                    info = info["entries"][0]
                title     = info.get("title", query)
                file_path = ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3")
                return title, file_path

        return await loop.run_in_executor(None, _download)
