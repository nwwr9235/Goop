"""
utils/music_downloader.py
Downloads audio from YouTube using yt-dlp and returns file path + metadata.
"""

import asyncio
import os
import re
import logging
from config import config

logger = logging.getLogger(__name__)

os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)


async def search_youtube(query: str) -> dict | None:
    """Search YouTube and return first result info."""
    try:
        from youtubesearchpython import VideosSearch
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, lambda: VideosSearch(query, limit=1).result()
        )
        items = results.get("result", [])
        if not items:
            return None
        item = items[0]
        return {
            "title": item.get("title", "Unknown"),
            "url": item.get("link", ""),
            "duration": item.get("duration", "N/A"),
            "thumbnail": item.get("thumbnails", [{}])[0].get("url", ""),
            "channel": item.get("channel", {}).get("name", "Unknown"),
        }
    except Exception as e:
        logger.error(f"YouTube search error: {e}")
        return None


def _is_youtube_url(text: str) -> bool:
    pattern = re.compile(
        r"(https?://)?(www\.)?(youtube\.com/watch|youtu\.be/|youtube\.com/shorts/)"
    )
    return bool(pattern.search(text))


async def download_audio(url: str) -> dict | None:
    """
    Downloads audio from URL using yt-dlp.
    Returns dict with: path, title, duration, thumbnail, channel
    """
    import yt_dlp

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(config.DOWNLOAD_DIR, "%(id)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }
        ],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    try:
        loop = asyncio.get_event_loop()

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return info

        info = await loop.run_in_executor(None, _download)

        if not info:
            return None

        video_id = info.get("id", "")
        file_path = os.path.join(config.DOWNLOAD_DIR, f"{video_id}.mp3")

        # Sometimes extension might differ — find actual file
        if not os.path.exists(file_path):
            for fname in os.listdir(config.DOWNLOAD_DIR):
                if fname.startswith(video_id):
                    file_path = os.path.join(config.DOWNLOAD_DIR, fname)
                    break

        duration_secs = info.get("duration", 0)
        m, s = divmod(int(duration_secs), 60)
        h, m = divmod(m, 60)
        duration_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

        return {
            "path": file_path,
            "title": info.get("title", "Unknown"),
            "duration": duration_str,
            "duration_secs": duration_secs,
            "thumbnail": info.get("thumbnail", ""),
            "channel": info.get("uploader", "Unknown"),
            "url": url,
        }

    except Exception as e:
        logger.error(f"Download error for {url}: {e}")
        return None


async def get_track_info(query_or_url: str) -> dict | None:
    """
    Accepts either a YouTube URL or a search query.
    Returns track info dict ready to pass to download_audio.
    """
    if _is_youtube_url(query_or_url):
        return {"url": query_or_url, "title": query_or_url, "duration": "N/A"}
    else:
        result = await search_youtube(query_or_url)
        return result


def cleanup_file(path: str):
    """Remove a downloaded file."""
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
