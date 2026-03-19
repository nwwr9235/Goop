"""
utils/music_player.py — pytgcalls==0.0.24

API المعروفة في 0.0.24:
  from pytgcalls import PyTgCalls
  from pytgcalls.types.input_stream import AudioPiped
  from pytgcalls.types.input_stream.quality import HighQualityAudio
  on_stream_end → callback(client, update)
  update.chat_id
  join_group_call / change_stream / leave_group_call
  pause_stream / resume_stream
"""

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

    def set_pytgcalls(self, pytgcalls: PyTgCalls):
        self._pytgcalls = pytgcalls

        @pytgcalls.on_stream_end()
        async def _on_end(client, update):
            chat_id = update.chat_id
            logger.info(f"[Music] Stream ended in {chat_id}")
            await self._play_next(chat_id)

    async def play(self, chat_id: int, track: dict):
        """True=يعزف | False=قائمة | None=فشل"""
        if self._current.get(chat_id):
            await db_client.push_queue(chat_id, track)
            return False

        url = track.get("url") or track.get("title", "")
        downloaded = await download_audio(url)
        if not downloaded:
            return None

        track.update({
            "path":      downloaded["path"],
            "title":     downloaded.get("title",     track.get("title", "Unknown")),
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
            logger.info(f"[Music] ▶ Playing '{track['title']}' in {chat_id}")
            return True
        except Exception as e:
            logger.error(f"[Music] join_group_call error: {e}")
            self._current.pop(chat_id, None)
            return None

    async def skip(self, chat_id: int) -> bool:
        if chat_id not in self._current:
            return False
        await self._play_next(chat_id)
        return True

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

    async def pause(self, chat_id: int) -> bool:
        if chat_id not in self._current:
            return False
        try:
            await self._pytgcalls.pause_stream(chat_id)
            self._paused[chat_id] = True
            return True
        except Exception as e:
            logger.error(f"[Music] pause error: {e}")
            return False

    async def resume(self, chat_id: int) -> bool:
        if chat_id not in self._current:
            return False
        try:
            await self._pytgcalls.resume_stream(chat_id)
            self._paused[chat_id] = False
            return True
        except Exception as e:
            logger.error(f"[Music] resume error: {e}")
            return False

    async def leave(self, chat_id: int) -> bool:
        return await self.stop(chat_id)

    async def _play_next(self, chat_id: int):
        old = self._current.pop(chat_id, None)
        if old and old.get("path"):
            cleanup_file(old["path"])
        self._paused.pop(chat_id, None)

        next_track = await db_client.pop_queue(chat_id)
        if not next_track:
            try:
                await self._pytgcalls.leave_group_call(chat_id)
            except Exception:
                pass
            return

        downloaded = await download_audio(next_track.get("url", ""))
        if not downloaded:
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
            logger.info(f"[Music] ▶ Next: '{next_track['title']}' in {chat_id}")
        except Exception as e:
            logger.error(f"[Music] change_stream error: {e}")
            await self._play_next(chat_id)

    def get_current(self, chat_id: int) -> dict | None:
        return self._current.get(chat_id)

    def is_paused(self, chat_id: int) -> bool:
        return self._paused.get(chat_id, False)

    def is_playing(self, chat_id: int) -> bool:
        return chat_id in self._current


music_player = MusicPlayer()
