"""
music_bot/main.py
اختبار تثبيت NTgCalls
"""

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ اختبار 1: هل ntgcalls مثبت؟
try:
    import ntgcalls
    logger.info(f"✅ NTgCalls imported: {ntgcalls.__version__}")
except ImportError as e:
    logger.error(f"❌ NTgCalls NOT installed: {e}")
    logger.error("الحل: pip install ntgcalls")
    raise

# ✅ اختبار 2: هل py-tgcalls يعمل؟
try:
    from pytgcalls import PyTgCalls
    logger.info("✅ PyTgCalls imported")
except ImportError as e:
    logger.error(f"❌ PyTgCalls error: {e}")
    raise

# ✅ اختبار 3: ما هي الأنواع المتاحة؟
try:
    import pytgcalls.types
    logger.info(f"Available in pytgcalls.types: {dir(pytgcalls.types)}")
except Exception as e:
    logger.error(f"Error checking types: {e}")

# ... باقي الكود
