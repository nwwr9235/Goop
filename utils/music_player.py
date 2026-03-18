"""
utils/music_player.py
مشغل الموسيقى — متوافق مع pytgcalls==2.1.0

API ثابتة ومعروفة في 2.1.0:
  from pytgcalls import PyTgCalls
  from pytgcalls.types.input_stream import AudioPiped
  from pytgcalls.types.input_stream.quality import HighQualityAudio
  pytgcalls.on_stream_end() → callback(client, update)
  update.chat_id
"""

import asyncio
import logging

from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped
from pytgcalls.types.input_stream.quality import HighQualityAudio

from database import db_client
from utils.music_downloader import download_audio, cleanup_file

logger = logging.getLogger(__name__)


class MusicPlayer:
    def __init__(self):
        self._pytgcalls: PyTgCalls | None = None
        self._current: dict[int, dict] = {}
        self._paused:  dict[int, bool] = {}

    # ── ربط PyTgCalls ─────────────────────────────────────────────────────────

    def set_pytgcalls(self, pytgcalls: PyTgCalls):
        self._pytgcalls = pytgcalls

        @pytgcalls.on_stream_end()
        async def _on_end(client, update):
            chat_id = update.chat_id
            logger.info(f"[MusicPlayer] Stream ended in {chat_id}")
            await self._play_next(chat_id)

    # ── تشغيل أغنية ───────────────────────────────────────────────────────────

    async def play(self, chat_id: int, track: dict):
        """
        True  → يعزف الآن
        False → أُضيف للقائمة
        None  → فشل
        """
        if self._current.get(chat_id):
            await db_client.push_queue(chat_id, track)
            return False

        url = track.get("url") or track.get("title", "")
        logger.info(f"[MusicPlayer] Downloading: {url}")
        downloaded = await download_audio(url)
        if not downloaded:
            logger.error("[MusicPlayer] Download failed")
            return None

        track.update({
            "path":      downloaded["path"],
            "title":     downloaded.get("title",     track.get("title",    "Unknown")),
            "duration":  downloaded.get("duration",  "N/A"),
            "thumbnail": downloaded.get("thumbnail", ""),
        })
        self._current[chat_id] = track

        try:
            await self._pytgcalls.join_group_call(
                chat_id,
                AudioPiped(downloaded["path"], HighQualityAudio()),
            )
            self._paused[chat_id] = False
            logger.info(f"[MusicPlayer] ▶ Playing '{track['title']}' in {chat_id}")
            return True
        except Exception as e:
            logger.error(f"[MusicPlayer] join_group_call error: {e}")
            self._current.pop(chat_id, None)
            return None

    # ── تخطي ──────────────────────────────────────────────────────────────────

    async def skip(self, chat_id: int) -> bool:
        if chat_id not in self._current:
            return False
        await self._play_next(chat_id)
        return True

    # ── إيقاف ─────────────────────────────────────────────────────────────────

    async def stop(self, chat_id: int) -> bool:
        await db_client.clear_queue(chat_id)
        old = self._current.pop(chat_id, None)
        if old and old.get("path"):
            cleanup_file(old["path"])
        self._paused.pop(chat_id, None)
        try:
            await self._pytgcalls.leave_group_call(chat_id)
            return True
        except Exception:
            return False

    # ── إيقاف مؤقت ────────────────────────────────────────────────────────────

    async def pause(self, chat_id: int) -> bool:
        if chat_id not in self._current:
            return False
        try:
            await self._pytgcalls.pause_stream(chat_id)
            self._paused[chat_id] = True
            return True
        except Exception as e:
            logger.error(f"[MusicPlayer] pause error: {e}")
            return False

    # ── استئناف ───────────────────────────────────────────────────────────────

    async def resume(self, chat_id: int) -> bool:
        if chat_id not in self._current:
            return False
        try:
            await self._pytgcalls.resume_stream(chat_id)
            self._paused[chat_id] = False
            return True
        except Exception as e:
            logger.error(f"[MusicPlayer] resume error: {e}")
            return False

    # ── مغادرة ────────────────────────────────────────────────────────────────

    async def leave(self, chat_id: int) -> bool:
        return await self.stop(chat_id)

    # ── الأغنية التالية تلقائياً ──────────────────────────────────────────────

    async def _play_next(self, chat_id: int):
        old = self._current.pop(chat_id, None)
        if old and old.get("path"):
            cleanup_file(old["path"])
        self._paused.pop(chat_id, None)

        next_track = await db_client.pop_queue(chat_id)
        if not next_track:
            try:
                await self._pytgcalls.leave_group_call(chat_id)
                logger.info(f"[MusicPlayer] Queue empty — left VC {chat_id}")
            except Exception:
                pass
            return

        downloaded = await download_audio(next_track.get("url", ""))
        if not downloaded:
            logger.warning("[MusicPlayer] Next track failed, skipping...")
            await self._play_next(chat_id)
            return

        next_track.update({
            "path":     downloaded["path"],
            "title":    downloaded.get("title",    next_track.get("title", "Unknown")),
            "duration": downloaded.get("duration", "N/A"),
        })
        self._current[chat_id] = next_track

        try:
            await self._pytgcalls.change_stream(
                chat_id,
                AudioPiped(downloaded["path"], HighQualityAudio()),
            )
            logger.info(f"[MusicPlayer] ▶ Next: '{next_track['title']}' in {chat_id}")
        except Exception as e:
            logger.error(f"[MusicPlayer] change_stream error: {e}")
            await self._play_next(chat_id)

    # ── الحالة ────────────────────────────────────────────────────────────────

    def get_current(self, chat_id: int) -> dict | None:
        return self._current.get(chat_id)

    def is_paused(self, chat_id: int) -> bool:
        return self._paused.get(chat_id, False)

    def is_playing(self, chat_id: int) -> bool:
        return chat_id in self._current


music_player = MusicPlayer()
