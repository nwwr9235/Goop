# plugins/music/player.py
import re
import yt_dlp
from pytgcalls import PyTgCalls
from pytgcalls.types import Update
from database.models import Queue, Song

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Initialize PyTgCalls
pytgcalls = None

@app.on_message(filters.regex(r'^تشغيل\s+(.+)') & filters.group)
async def play_handler(client, message):
    query = message.matches[0].group(1)
    
    # Search for the song
    results = await search_youtube(query)
    
    if results:
        # Add to queue
        queue = await Queue.get_or_create(message.chat.id)
        song = Song(
            title=results[0]['title'],
            url=results[0]['webpage_url'],
            requested_by=message.from_user.username or message.from_user.first_name
        )
        
        queue.songs.append(song)
        await queue.save()
        
        if not queue.is_playing:
            await start_playback(client, message, queue)
        else:
            await message.reply(f"🎵 تم إضافة {results[0]['title']} إلى قائمة الانتظار!")
    else:
        await message.reply("❌ لم يتم العثور على نتائج!")

async def start_playback(client, message, queue):
    song = queue.songs[queue.current_index]
    
    # Download and play
    file_path = await download_song(song.url)
    
    if file_path:
        # Play the file
        await pytgcalls.play(message.chat.id, file_path)
        
        # Update queue status
        queue.is_playing = True
        queue.current_song = song
        await queue.save()
        
        await message.reply(f"🎵 يتم تشغيل {song.title} الآن!")

@app.on_message(filters.regex(r'^تخطي') & filters.group)
async def skip_handler(client, message):
    queue = await Queue.get_or_create(message.chat.id)
    
    if queue.is_playing:
        # Stop current song and play next
        await pytgcalls.stop(message.chat.id)
        
        # Move to next song
        queue.current_index += 1
        queue.is_playing = False
        await queue.save()
        
        # Start next song
        await start_playback(client, message, queue)

@app.on_message(filters.regex(r'^ايقاف') & filters.group)
async def stop_handler(client, message):
    queue = await Queue.get_or_create(message.chat.id)
    
    if queue.is_playing:
        await pytgcalls.stop(message.chat.id)
        queue.is_playing = False
        await queue.save()
        
        await message.reply("⏹ تم إيقاف التشغيل!")

@app.on_message(filters.regex(r'^ايقاف\s+مؤقت') & filters.group)
async def pause_handler(client, message):
    await pytgcalls.pause(message.chat.id)
    await message.reply("⏸ تم إيقاف التشغيل مؤقتاً!")

@app.on_message(filters.regex(r'^استئناف') & filters.group)
async def resume_handler(client, message):
    await pytgcalls.resume(message.chat.id)
    await message.reply("▶️ تم استئناف التشغيل!")

@app.on_message(filters.regex(r'^قائمة\s+التشغيل') & filters.group)
async def queue_handler(client, message):
    queue = await Queue.get_or_create(message.chat.id)
    
    if queue.songs:
        text = "📋 قائمة التشغيل:\n\n"
        for i, song in enumerate(queue.songs, 1):
            marker = "▶️" if i == queue.current_index + 1 else "⏹️" if i < queue.current_index + 1 else "⏸️"
            text += f"{i}. {marker} {song.title} - بواسطة {song.requested_by}\n"
        
        await message.reply(text)
    else:
        await message.reply("📭 قائمة التشغيل فارغة!")

@app.on_message(filters.regex(r'^مغادرة') & filters.group)
async def leave_handler(client, message):
    await pytgcalls.leave_call(message.chat.id)
    await message.reply("👋 تم مغادرة الدردشة الصوتية!")
