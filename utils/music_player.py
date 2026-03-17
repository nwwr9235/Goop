"""
utils/music_player.py
Core music player manager: tracks active calls, manages per-chat queues,
handles PyTgCalls streaming lifecycle.
"""

import asyncio
import logging
from pytgcalls import PyTgCalls
from pytgcalls.types import Update
from pytgcalls.types.input_stream import AudioPiped
from pytgcalls.types.input_stream.quality import HighQualityAudio
from database import db_client
from utils.music_downloader import download_audio, cleanup_file
from config import config

logger = logging.getLogger(__name__)


class MusicPlayer:
    def __init__(self):
        self._pytgcalls: PyTgCalls | None = None
        # Per-chat: current playing track info
        self._current: dict[int, dict] = {}
        # Per-chat: is paused?
        self._paused: dict[int, bool] = {}

    def set_pytgcalls(self, pytgcalls: PyTgCalls):
        self._pytgcalls = pytgcalls
        # Register stream end callback
        pytgcalls.on_stream_end()(self._on_stream_end)

    async def _on_stream_end(self, client, update: Update):
        """Called by PyTgCalls when current track finishes."""
        chat_id = update.chat_id
        logger.info(f"Stream ended in {chat_id}, trying next in queue.")
        await self._play_next(chat_id)

    async def join_vc(self, chat_id: int):
        """Join voice chat if not already in it."""
        try:
            active = await self._pytgcalls.get_active_calls()
            for call in active:
                if call.chat_id == chat_id:
                    return  # Already in VC
            # PyTgCalls join is implicit on play
        except Exception:
            pass

    async def play(self, chat_id: int, track: dict) -> bool:
        """
        Download and stream a track. If already playing, add to queue.
        Returns True if started playing, False if added to queue.
        """
        current = self._current.get(chat_id)

        if current:
            # Already playing — add to queue
            await db_client.push_queue(chat_id, track)
            return False

        # Download the track
        logger.info(f"Downloading: {track.get('url', track.get('title'))}")
        downloaded = await download_audio(track.get("url", track.get("title", "")))

        if not downloaded:
            return None  # Download failed

        track["path"] = downloaded["path"]
        track["title"] = downloaded.get("title", track.get("title", "Unknown"))
        track["duration"] = downloaded.get("duration", "N/A")
        track["thumbnail"] = downloaded.get("thumbnail", "")

        self._current[chat_id] = track

        try:
            await self._pytgcalls.join_group_call(
                chat_id,
                AudioPiped(
                    downloaded["path"],
                    HighQualityAudio(),
                ),
            )
            self._paused[chat_id] = False
            logger.info(f"Playing '{track['title']}' in {chat_id}")
            return True
        except Exception as e:
            logger.error(f"PyTgCalls error: {e}")
            self._current.pop(chat_id, None)
            return None

    async def _play_next(self, chat_id: int):
        """Pop next from queue and start playing."""
        # Clean up old track file
        old = self._current.pop(chat_id, None)
        if old and old.get("path"):
            cleanup_file(old["path"])

        next_track = await db_client.pop_queue(chat_id)
        if not next_track:
            # Nothing left — leave VC
            try:
                await self._pytgcalls.leave_group_call(chat_id)
            except Exception:
                pass
            return

        # Download and stream next
        downloaded = await download_audio(next_track.get("url", ""))
        if not downloaded:
            await self._play_next(chat_id)
            return

        next_track["path"] = downloaded["path"]
        next_track["title"] = downloaded.get("title", next_track.get("title", "Unknown"))
        next_track["duration"] = downloaded.get("duration", "N/A")
        self._current[chat_id] = next_track

        try:
            await self._pytgcalls.change_stream(
                chat_id,
                AudioPiped(downloaded["path"], HighQualityAudio()),
            )
            logger.info(f"Next track: '{next_track['title']}' in {chat_id}")
        except Exception as e:
            logger.error(f"change_stream error: {e}")
            await self._play_next(chat_id)

    async def add_to_queue(self, chat_id: int, track: dict):
        """Add a track to the queue."""
        await db_client.push_queue(chat_id, track)

    async def skip(self, chat_id: int) -> bool:
        """Skip current track."""
        if chat_id not in self._current:
            return False
        await self._play_next(chat_id)
        return True

    async def stop(self, chat_id: int) -> bool:
        """Stop playback and clear queue."""
        await db_client.clear_queue(chat_id)
        old = self._current.pop(chat_id, None)
        if old and old.get("path"):
            cleanup_file(old["path"])
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
        except Exception:
            return False

    async def resume(self, chat_id: int) -> bool:
        if chat_id not in self._current:
            return False
        try:
            await self._pytgcalls.resume_stream(chat_id)
            self._paused[chat_id] = False
            return True
        except Exception:
            return False

    async def leave(self, chat_id: int) -> bool:
        """Leave VC and cleanup."""
        return await self.stop(chat_id)

    def get_current(self, chat_id: int) -> dict | None:
        return self._current.get(chat_id)

    def is_paused(self, chat_id: int) -> bool:
        return self._paused.get(chat_id, False)

    def is_playing(self, chat_id: int) -> bool:
        return chat_id in self._current


# Singleton
music_player = MusicPlayer()
