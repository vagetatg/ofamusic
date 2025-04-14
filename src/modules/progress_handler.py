import time
from typing import Optional, Dict
from pytdbot import Client, types

from src.logger import LOGGER
from src.platforms.telegram import Telegram

# Store download progress data {file_id: {"start_time": float, "last_update": float, "last_size": int}}
download_progress = {}


def _format_bytes(size: int) -> str:
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


def _format_time(seconds: int) -> str:
    """Convert seconds to human-readable time."""
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _create_progress_bar(percentage: int, length: int = 10) -> str:
    """Create a text-based progress bar."""
    filled = int(round(length * percentage / 100))
    return '▰' * filled + '▱' * (length - filled)


@Client.on_updateFile()
async def update_file(c: Client, update: types.UpdateFile):
    """Handle file download progress updates."""
    unique_id = update.file.remote.unique_id
    data = Telegram(None).get_cached_metadata(unique_id)
    if not data:
        return

    chat_id = data["chat_id"]
    filename = data["filename"]
    file_id = update.file.id
    file_data = update.file

    # Initialize progress tracking
    if file_id not in download_progress:
        download_progress[file_id] = {
            "start_time": time.time(),
            "last_update": time.time(),
            "last_size": 0
        }

    # Get current progress data
    progress = download_progress[file_id]
    current_time = time.time()
    elapsed = current_time - progress["last_update"]

    # Calculate download speed
    downloaded = file_data.local.downloaded_size
    total_size = file_data.size
    speed = (downloaded - progress["last_size"]) / elapsed if elapsed > 0 else 0

    # Update progress tracking
    progress["last_update"] = current_time
    progress["last_size"] = downloaded

    # Calculate progress percentage
    percentage = min(100, int((downloaded / total_size) * 100))

    # Calculate ETA
    remaining_bytes = total_size - downloaded
    eta = int(remaining_bytes / speed) if speed > 0 else 0

    # Prepare progress text
    progress_text = (
        f"📥 <b>Downloading:</b> <code>{filename}</code>\n"
        f"💾 <b>Size:</b> {_format_bytes(total_size)}\n"
        f"📊 <b>Progress:</b> {percentage}% {_create_progress_bar(percentage)}\n"
        f"🚀 <b>Speed:</b> {_format_bytes(speed)}/s\n"
        f"⏳ <b>ETA:</b> {_format_time(eta) if speed > 0 else 'Calculating...'}"
    )

    try:
        parse = await c.parseTextEntities(progress_text, types.TextParseModeHTML())
        # Edit or send new progress message
        if hasattr(progress, "message_id"):
            await c.editMessageText(
                chat_id=chat_id,
                message_id=progress.message_id,
                input_message_content=types.InputMessageText(parse)
            )
        else:
            msg = await c.sendMessage(chat_id=chat_id, input_message_content=types.InputMessageText(parse))
            progress.message_id = msg.id

    except Exception as e:
        LOGGER.error(f"Error updating progress: {e}")

    # Clean up when download completes
    if file_data.local.is_downloading_completed:
        download_progress.pop(file_id, None)
        completed_text = (
            f"✅ <b>Download Complete:</b> <code>{filename}</code>\n"
            f"💾 <b>Size:</b> {_format_bytes(total_size)}\n"
            f"⏱ <b>Time Taken:</b> {_format_time(int(time.time() - progress['start_time']))}"
        )
        parse = await c.parseTextEntities(completed_text, types.TextParseModeHTML())
        try:
            await c.editMessageText(
                chat_id=chat_id,
                message_id=progress.message_id,
                input_message_content=types.InputMessageText(parse)
            )
        except Exception as e:
            LOGGER.error(f"Error sending completion message: {e}")
