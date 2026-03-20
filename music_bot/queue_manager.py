"""
music_bot/queue_manager.py
إدارة قوائم انتظار الأغاني لكل مجموعة
"""

from collections import deque
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Track:
    title:    str
    url:      str        # رابط الملف الصوتي المحلي أو stream URL
    query:    str        # الاستعلام الأصلي من المستخدم
    user_id:  int


class GroupQueue:
    """قائمة انتظار خاصة بمجموعة واحدة"""

    def __init__(self):
        self._queue: deque[Track] = deque()
        self.is_playing: bool = False
        self.is_paused:  bool = False

    def add(self, track: Track) -> int:
        """إضافة أغنية — يُرجع موضعها في القائمة"""
        self._queue.append(track)
        return len(self._queue)

    def current(self) -> Optional[Track]:
        return self._queue[0] if self._queue else None

    def skip(self) -> Optional[Track]:
        """إزالة الأغنية الحالية وإرجاع التالية"""
        if self._queue:
            self._queue.popleft()
        return self.current()

    def clear(self):
        self._queue.clear()
        self.is_playing = False
        self.is_paused  = False

    def to_list(self) -> list[dict]:
        return [{"title": t.title, "query": t.query} for t in self._queue]

    def __len__(self):
        return len(self._queue)


class QueueManager:
    """مدير مركزي لجميع المجموعات"""

    def __init__(self):
        self._groups: dict[int, GroupQueue] = {}

    def get(self, chat_id: int) -> GroupQueue:
        if chat_id not in self._groups:
            self._groups[chat_id] = GroupQueue()
        return self._groups[chat_id]

    def remove(self, chat_id: int):
        self._groups.pop(chat_id, None)


# مثيل مشترك داخل بوت الموسيقى
queue_manager = QueueManager()
