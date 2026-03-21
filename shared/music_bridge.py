"""
shared/music_bridge.py
طبقة الاتصال: يستخدمها بوت الإدارة لإرسال أوامر الموسيقى إلى بوت الموسيقى
"""

import aiohttp
import logging
from shared.config import AdminConfig

logger = logging.getLogger(__name__)


class MusicBridge:
    """
    واجهة برمجية بسيطة تتيح لبوت الإدارة إرسال طلبات
    إلى بوت الموسيقى عبر HTTP مع التحقق من المفتاح السري.
    """

    BASE_URL = AdminConfig.MUSIC_API_URL
    SECRET   = AdminConfig.INTERNAL_SECRET
    HEADERS  = {
        "X-Internal-Secret": AdminConfig.INTERNAL_SECRET,
        "Content-Type": "application/json",
    }

    # ------------------------------------------------------------------ #

    @classmethod
    async def _post(cls, endpoint: str, payload: dict) -> dict:
        """إرسال طلب POST داخلي وإرجاع استجابة JSON"""
        url = f"{cls.BASE_URL}{endpoint}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=cls.HEADERS,
                    timeout=aiohttp.ClientTimeout(total=60),  # ✅ زيادة الـ timeout لـ 60 ثانية
                ) as resp:
                    data = await resp.json()
                    return data
        except aiohttp.ClientConnectorError as e:
            logger.error(f"❌ تعذر الاتصال ببوت الموسيقى: {e}")
            return {"ok": False, "error": "music_bot_unreachable"}
        except aiohttp.ServerTimeoutError:
            logger.error("❌ انتهت مهلة الاتصال ببوت الموسيقى (timeout)")
            return {"ok": False, "error": "timeout"}
        except Exception as e:
            logger.error(f"❌ خطأ في MusicBridge: {type(e).__name__}: {e}")
            return {"ok": False, "error": str(e) or type(e).__name__}

    # ------------------------------------------------------------------ #
    #  الأوامر العامة
    # ------------------------------------------------------------------ #

    @classmethod
    async def play(cls, chat_id: int, user_id: int, query: str) -> dict:
        """
        طلب تشغيل أغنية.
        المعاملات:
            chat_id  - معرّف المجموعة
            user_id  - معرّف المستخدم الذي أصدر الأمر
            query    - اسم الأغنية أو رابط YouTube
        """
        return await cls._post("/play", {
            "chat_id": chat_id,
            "user_id": user_id,
            "query":   query,
        })

    @classmethod
    async def stop(cls, chat_id: int, user_id: int) -> dict:
        """إيقاف التشغيل ومسح القائمة"""
        return await cls._post("/stop", {
            "chat_id": chat_id,
            "user_id": user_id,
        })

    @classmethod
    async def skip(cls, chat_id: int, user_id: int) -> dict:
        """تخطي الأغنية الحالية"""
        return await cls._post("/skip", {
            "chat_id": chat_id,
            "user_id": user_id,
        })

    @classmethod
    async def pause(cls, chat_id: int, user_id: int) -> dict:
        """إيقاف مؤقت"""
        return await cls._post("/pause", {
            "chat_id": chat_id,
            "user_id": user_id,
        })

    @classmethod
    async def resume(cls, chat_id: int, user_id: int) -> dict:
        """استئناف التشغيل"""
        return await cls._post("/resume", {
            "chat_id": chat_id,
            "user_id": user_id,
        })

    @classmethod
    async def queue(cls, chat_id: int) -> dict:
        """جلب قائمة الانتظار الحالية"""
        return await cls._post("/queue", {"chat_id": chat_id})
