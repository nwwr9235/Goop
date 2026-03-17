"""
utils/arabic_commands.py
Central list of all Arabic text commands (no slash prefix).
"""

# ── Admin ─────────────────────────────────────────────────────────────────────
CMD_PROMOTE        = "رفع"
CMD_DEMOTE         = "تنزيل"
CMD_BAN            = "حظر"
CMD_UNBAN          = "الغاء الحظر"
CMD_MUTE           = "كتم"
CMD_UNMUTE         = "الغاء الكتم"
CMD_KICK           = "طرد"
CMD_ADMIN_LIST     = ["عرض الادمنية", "قائمة الادمنية"]

# ── Warnings ──────────────────────────────────────────────────────────────────
CMD_WARN           = "انذار"
CMD_SHOW_WARNS     = "عرض الانذارات"
CMD_CLEAR_WARNS    = "مسح الانذارات"

# ── Locks ─────────────────────────────────────────────────────────────────────
LOCK_MAP = {
    "قفل الروابط":    ("links",    True),
    "فتح الروابط":    ("links",    False),
    "قفل المعرفات":   ("usernames", True),
    "فتح المعرفات":   ("usernames", False),
    "قفل البوتات":    ("bots",     True),
    "فتح البوتات":    ("bots",     False),
    "قفل الصور":      ("photos",   True),
    "فتح الصور":      ("photos",   False),
    "قفل الفيديو":    ("videos",   True),
    "فتح الفيديو":    ("videos",   False),
    "قفل المتحركة":   ("stickers", True),
    "فتح المتحركة":   ("stickers", False),
    "قفل الملفات":    ("files",    True),
    "فتح الملفات":    ("files",    False),
    "قفل التكرار":    ("flood",    True),
    "فتح التكرار":    ("flood",    False),
    "قفل السبام":     ("spam",     True),
    "فتح السبام":     ("spam",     False),
}

LOCK_NAMES_AR = {
    "links":     "الروابط",
    "usernames": "المعرفات",
    "bots":      "البوتات",
    "photos":    "الصور",
    "videos":    "الفيديو",
    "stickers":  "الملصقات المتحركة",
    "files":     "الملفات",
    "flood":     "التكرار",
    "spam":      "السبام",
}

# ── Welcome ───────────────────────────────────────────────────────────────────
CMD_WELCOME_ON     = "تفعيل الترحيب"
CMD_WELCOME_OFF    = "تعطيل الترحيب"
CMD_SET_WELCOME    = "تعيين رسالة الترحيب"

# ── Auto replies ──────────────────────────────────────────────────────────────
CMD_ADD_REPLY      = "اضافة رد"
CMD_DEL_REPLY      = "حذف رد"
CMD_LIST_REPLIES   = "عرض الردود"

# ── Music ─────────────────────────────────────────────────────────────────────
CMD_PLAY           = "تشغيل"
CMD_SKIP           = "تخطي"
CMD_STOP           = "ايقاف"
CMD_PAUSE          = "ايقاف مؤقت"
CMD_RESUME         = "استئناف"
CMD_QUEUE          = "قائمة التشغيل"
CMD_REMOVE_QUEUE   = "حذف من القائمة"
CMD_LEAVE_VC       = "مغادرة"

# ── Info ──────────────────────────────────────────────────────────────────────
CMD_ID             = "ايدي"
CMD_MY_INFO        = "معلوماتي"
CMD_USER_INFO      = "معلومات"
CMD_GROUP_INFO     = "معلومات المجموعة"

# ── Utility ───────────────────────────────────────────────────────────────────
CMD_HELP           = "مساعدة"
CMD_COMMANDS       = "الاوامر"
CMD_ADMIN_CMDS     = "الاوامر الادارية"
CMD_PROTECT_CMDS   = "اوامر الحماية"
CMD_MUSIC_CMDS     = "اوامر الموسيقى"

# ── Owner ─────────────────────────────────────────────────────────────────────
CMD_RESTART        = "اعادة تشغيل"
CMD_BOT_STATUS     = "حالة البوت"
CMD_BOT_SPEED      = "سرعة البوت"
CMD_BROADCAST      = "اذاعة"
