"""
utils/music_player.py
Core music player — مُصحَّح لـ pytgcalls==3.0.0.dev24

التغييرات الرئيسية في dev24:
  - AudioPiped أصبح من pytgcalls.types.stream  (وليس input_stream)
  - HighQualityAudio أصبح من pytgcalls.types.stream
  - on_stream_end يستقبل (update) فقط وليس (client, update)
  - pause/resume/leave الدوال تغيّرت أسماؤها
"""

import asyncio
import logging

from pytgcalls import PyTgCalls

# ── الاستيراد الصحيح لـ dev24 ─────────────────────────────────────────────────
try:
    # dev24+ — المسار الجديد
    from pytgcalls.types import Update
    from pytgcalls.types.stream import AudioPiped, HighQualityAudio
    _STREAM_IMPORT = "new"
except ImportError:
    try:
        # fallback للإصدارات القديمة قليلاً
        from pytgcalls.types import Update
        from pytgcalls.types.input_stream import AudioPiped
        from pytgcalls.types.input_stream.quality import HighQualityAudio
        _STREAM_IMPORT = "old"
    except ImportError:
        # آخر محاولة
        from pytgcalls.types import Update, AudioPiped, HighQualityAudio
        _STREAM_IMPORT = "fallback"

from database import db_client
from utils.music_downloader import download_audio, cleanup_file

logger = logging.getLogger(__name__)
logger.info(f"[MusicPlayer] Using stream import: {_STREAM_IMPORT}")


class MusicPlayer:
    def __init__(self):
        self._pytgcalls: PyTgCalls | None = None
        self._current: dict[int, dict] = {}   # chat_id → track info
        self._paused:  dict[int, bool] = {}   # chat_id → paused flag

    # ── ربط PyTgCalls ─────────────────────────────────────────────────────────

    def set_pytgcalls(self, pytgcalls: PyTgCalls):
        self._pytgcalls = pytgcalls

        # dev24: on_stream_end يمرر update فقط (بدون client)
        @pytgcalls.on_stream_end()
        async def _on_end(update: Update):
            try:
                chat_id = update.chat_id
            except AttributeError:
                # بعض الإصدارات تمرر (client, update)
                chat_id = update
            logger.info(f"[MusicPlayer] Stream ended in {chat_id}")
            await self._play_next(chat_id)

    # ── واجهة التشغيل العامة ──────────────────────────────────────────────────

    async def play(self, chat_id: int, track: dict):
        """
        تحميل وتشغيل أغنية.
        يُرجع: True  ← بدأ التشغيل الآن
                False ← أُضيف للقائمة (هناك شيء يعزف)
                None  ← فشل التحميل أو الاتصال
        """
        # إذا كان هناك شيء يعزف — أضف للقائمة
        if self._current.get(chat_id):
            await db_client.push_queue(chat_id, track)
            return False

        # تحميل الأغنية
        url_or_query = track.get("url") or track.get("title", "")
        logger.info(f"[MusicPlayer] Downloading: {url_or_query}")
        downloaded = await download_audio(url_or_query)

        if not downloaded:
            logger.error("[MusicPlayer] Download failed")
            return None

        # تحديث معلومات المسار
        track.update({
            "path":      downloaded["path"],
            "title":     downloaded.get("title",     track.get("title",    "Unknown")),
            "duration":  downloaded.get("duration",  "N/A"),
            "thumbnail": downloaded.get("thumbnail", ""),
        })
        self._current[chat_id] = track

        # الانضمام للمحادثة الصوتية والبث
        try:
            await self._pytgcalls.join_group_call(
                chat_id,
                AudioPiped(
                    downloaded["path"],
                    HighQualityAudio(),
                ),
            )
            self._paused[chat_id] = False
            logger.info(f"[MusicPlayer] ▶ Playing '{track['title']}' in {chat_id}")
            return True

        except Exception as e:
            logger.error(f"[MusicPlayer] join_group_call error: {e}")
            self._current.pop(chat_id, None)
            return None

    async def skip(self, chat_id: int) -> bool:
        """تخطي الأغنية الحالية."""
        if chat_id not in self._current:
            return False
        await self._play_next(chat_id)
        return True

    async def stop(self, chat_id: int) -> bool:
        """إيقاف التشغيل وتفريغ القائمة."""
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
        """إيقاف مؤقت."""
        if chat_id not in self._current:
            return False
        try:
            # dev24 API
            await self._pytgcalls.pause_stream(chat_id)
            self._paused[chat_id] = True
            return True
        except AttributeError:
            # إصدارات أقدم قد تستخدم اسماً مختلفاً
            try:
                await self._pytgcalls.pause(chat_id)
                self._paused[chat_id] = True
                return True
            except Exception as e:
                logger.error(f"[MusicPlayer] pause error: {e}")
                return False
        except Exception as e:
            logger.error(f"[MusicPlayer] pause error: {e}")
            return False

    async def resume(self, chat_id: int) -> bool:
        """استئناف التشغيل."""
        if chat_id not in self._current:
            return False
        try:
            await self._pytgcalls.resume_stream(chat_id)
            self._paused[chat_id] = False
            return True
        except AttributeError:
            try:
                await self._pytgcalls.resume(chat_id)
                self._paused[chat_id] = False
                return True
            except Exception as e:
                logger.error(f"[MusicPlayer] resume error: {e}")
                return False
        except Exception as e:
            logger.error(f"[MusicPlayer] resume error: {e}")
            return False

    async def leave(self, chat_id: int) -> bool:
        """مغادرة المحادثة الصوتية."""
        return await self.stop(chat_id)

    # ── التشغيل التلقائي للأغنية التالية ─────────────────────────────────────

    async def _play_next(self, chat_id: int):
        """تشغيل الأغنية التالية من القائمة، أو المغادرة إن كانت فارغة."""

        # تنظيف الملف القديم
        old = self._current.pop(chat_id, None)
        if old and old.get("path"):
            cleanup_file(old["path"])
        self._paused.pop(chat_id, None)

        # سحب التالي من قاعدة البيانات
        next_track = await db_client.pop_queue(chat_id)
        if not next_track:
            # القائمة فارغة — غادر المحادثة الصوتية
            try:
                await self._pytgcalls.leave_group_call(chat_id)
                logger.info(f"[MusicPlayer] Queue empty, left VC in {chat_id}")
            except Exception:
                pass
            return

        # تحميل الأغنية التالية
        downloaded = await download_audio(next_track.get("url", ""))
        if not downloaded:
            logger.warning(f"[MusicPlayer] Failed to download next track, skipping...")
            # تجاهل هذا المسار وجرب التالي
            await self._play_next(chat_id)
            return

        next_track.update({
            "path":     downloaded["path"],
            "title":    downloaded.get("title",    next_track.get("title", "Unknown")),
            "duration": downloaded.get("duration", "N/A"),
        })
        self._current[chat_id] = next_track

        try:
            # dev24: change_stream لتبديل الصوت بدون إعادة الانضمام
            await self._pytgcalls.change_stream(
                chat_id,
                AudioPiped(downloaded["path"], HighQualityAudio()),
            )
            logger.info(f"[MusicPlayer] ▶ Next: '{next_track['title']}' in {chat_id}")

        except Exception as e:
            logger.error(f"[MusicPlayer] change_stream error: {e}")
            # حاول تشغيل ما بعده
            await self._play_next(chat_id)

    # ── قراءة الحالة ──────────────────────────────────────────────────────────

    def get_current(self, chat_id: int) -> dict | None:
        return self._current.get(chat_id)

    def is_paused(self, chat_id: int) -> bool:
        return self._paused.get(chat_id, False)

    def is_playing(self, chat_id: int) -> bool:
        return chat_id in self._current


# Singleton عام — يُستورد في كل مكان
music_player = MusicPlayer()
