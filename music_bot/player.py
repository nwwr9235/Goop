"""
music_bot/player.py
محرك التشغيل الصوتي — متوافق مع py-tgcalls v2.2.11 + pyrofork 2.3.38
"""

import asyncio
import logging
import os
import yt_dlp
from pytgcalls import PyTgCalls
# ✅ استيراد صحيح لـ py-tgcalls 2.2.11
from pytgcalls.types.input_stream import AudioPiped, AudioParameters
from pytgcalls.types.stream import StreamEnded

logger = logging.getLogger(__name__)

YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "outtmpl": "/tmp/music/%(id)s.%(ext)s",
    # ✅ تحويل تلقائي إلى MP3 للتأكد من التوافق
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }],
}

os.makedirs("/tmp/music", exist_ok=True)


class MusicPlayer:

    def __init__(self, tgcalls: PyTgCalls):
        self.calls = tgcalls
        self._register_callbacks()

    async def play(self, chat_id: int, query: str, user_id: int) -> dict:
        try:
            title, file_path = await self._fetch(query)
        except Exception as e:
            logger.error(f"yt-dlp error: {e}")
            return {"ok": False, "error": f"فشل التنزيل: {e}"}

        # ✅ التحقق من وجود الملف
        if not os.path.exists(file_path):
            logger.error(f"الملف غير موجود: {file_path}")
            return {"ok": False, "error": "الملف غير موجود بعد التنزيل"}

        track = Track(title=title, url=file_path, query=query, user_id=user_id)
        gq = queue_manager.get(chat_id)
        pos = gq.add(track)

        if not gq.is_playing:
            await self._start_playback(chat_id)

        return {"ok": True, "title": title, "position": pos}

    async def stop(self, chat_id: int) -> dict:
        queue_manager.get(chat_id).clear()
        try:
            await self.calls.leave_call(chat_id)
        except Exception as e:
            logger.warning(f"خطأ عند المغادرة: {e}")
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

    async def _start_playback(self, chat_id: int):
        gq = queue_manager.get(chat_id)
        track = gq.current()
        if not track:
            gq.is_playing = False
            return

        gq.is_playing = True
        gq.is_paused = False

        try:
            # ✅ استخدام AudioPiped مع AudioParameters (الطريقة الصحيحة في 2.2.11)
            audio = AudioPiped(
                track.url,
                AudioParameters(
                    bitrate=48000,
                    channels=2,
                ),
            )

            await self.calls.play(
                chat_id,
                audio,
            )
            logger.info(f"▶️ تشغيل في {chat_id}: {track.title}")

        except Exception as e:
            logger.error(f"❌ خطأ في التشغيل: {e}")
            logger.exception(e)
            gq.is_playing = False
            # محاولة التخطي للأغنية التالية
            await self.skip(chat_id)

    def _register_callbacks(self):
        @self.calls.on_update()
        async def on_stream_ended(_, update):
            if isinstance(update, StreamEnded):
                chat_id = update.chat_id
                logger.info(f"🔴 انتهى البث في {chat_id}")

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
        search = query if query.startswith("http") else f"ytsearch1:{query}"
        loop = asyncio.get_event_loop()

        def _download():
            with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
                info = ydl.extract_info(search, download=True)
                if "entries" in info:
                    info = info["entries"][0]
                title = info.get("title", query)
                file_path = ydl.prepare_filename(info)
                
                # ✅ التأكد من امتداد الملف الصحيح بعد التحويل
                if file_path.endswith(('.webm', '.m4a', '.mp4', '.weba')):
                    file_path = file_path.rsplit('.', 1)[0] + '.mp3'
                
                return title, file_path

        return await loop.run_in_executor(None, _download)
