# utils/helpers.py
import re
from typing import Optional, List

def extract_status_change(chat_member):
    status_change = {}
    
    if chat_member.old_chat_member.status != chat_member.new_chat_member.status:
        status_change['status'] = True
        status_change['old'] = chat_member.old_chat_member.status
        status_change['new'] = chat_member.new_chat_member.status
    
    return status_change

async def is_admin(client, chat_id, user_id):
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"] or user_id in [123456789]  # Replace with actual admin check
    except:
        return False

async def is_sudo(client, chat_id, user_id):
    try:
        # Replace with actual sudo check
        return user_id in [123456789]
    except:
        return False

async def check_flood(client, chat_id, user_id):
    # Implement flood check logic
    pass

async def check_spam(client, chat_id, user_id):
    # Implement spam check logic
    pass

async def download_song(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        
        file_path = ydl.prepare_filename(info)
        
        # Download the file
        ydl.download([url])
        
        return file_path
    
    return None

async def search_youtube(query):
    ydl_opts = {
        'quiet': True
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)
        return info['entries']

