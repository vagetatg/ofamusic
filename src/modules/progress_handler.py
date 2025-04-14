import time
import math
from pytdbot import Client, types
from src.logger import LOGGER
from src.platforms.telegram import Telegram

download_progress = {}  # file_id: tracking info


def _format_bytes(size: int) -> str:
    """Improved byte formatting with more precise thresholds"""
    if size < 1024:
        return f"{size} B"
    for unit in ["KB", "MB", "GB", "TB"]:
        size /= 1024
        if size < 1024:
            return f"{size:.1f} {unit}"
    return f"{size:.1f} PB"


def _format_time(seconds: int) -> str:
    """More compact time formatting"""
    seconds = seconds
    if seconds < 60:
        return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def _create_progress_bar(percentage: int, length: int = 10) -> str:
    """More visually distinct progress bar"""
    percentage = min(100, max(0, percentage))
    filled = round(length * percentage / 100)
    return "⬢" * filled + "⬡" * (length - filled)


def _calculate_update_interval(file_size: int, current_speed: float) -> float:
    """
    Smart update interval calculation based on:
    - File size (larger files get longer intervals)
    - Current speed (faster downloads can update more frequently)
    - Minimum 1s, maximum 5s interval
    """
    if file_size < 5 * 1024 * 1024:  # Small files (<5MB)
        base_interval = 1.0
    else:
        # Logarithmic scaling for larger files
        size_factor = min(math.log10(file_size / (5 * 1024 * 1024)), 2)
        base_interval = 1.0 + size_factor * 2.0

    # Adjust based on speed (faster downloads can update more often)
    speed_factor = 1.0
    if current_speed > 1024 * 1024:  # If >1MB/s
        speed_factor = max(0.5, 2.0 - (current_speed / (5 * 1024 * 1024)))

    return min(max(base_interval * speed_factor, 1.0), 5.0)


@Client.on_updateFile()
async def update_file(c: Client, update: types.UpdateFile):
    file = update.file
    unique_id = file.remote.unique_id

    tg = Telegram(None)
    meta = tg.get_cached_metadata(unique_id)
    if not meta:
        return
    button = types.ReplyMarkupInlineKeyboard(
        [
            [
                types.InlineKeyboardButton(
                    text="✗ Cancel Download",
                    type=types.InlineKeyboardButtonTypeCallback(f"play_cancel_{unique_id}".encode())
                ),
            ],
        ]
    )
    chat_id = meta["chat_id"]
    filename = meta["filename"]
    message_id = meta["message_id"]
    file_id = file.id
    now = time.time()

    total = file.size or 1
    downloaded = file.local.downloaded_size
    percentage = min(100, int((downloaded / total) * 100))

    # Initialize or update progress tracking
    if file_id not in download_progress:
        download_progress[file_id] = {
            "start_time": now,
            "last_update": now,
            "last_size": downloaded,
            "next_update": now + 1.0,  # First update after 1s
            "last_speed": 0,
        }

    progress = download_progress[file_id]

    # Skip if not time to update yet
    if now < progress["next_update"] and not file.local.is_downloading_completed:
        return

    # Calculate metrics
    elapsed = now - progress["last_update"]
    delta = downloaded - progress["last_size"]
    current_speed = delta / elapsed if elapsed > 0 else 0
    eta = int((total - downloaded) / current_speed) if current_speed > 0 else -1

    # Calculate dynamic update interval
    update_interval = _calculate_update_interval(total, current_speed)
    progress["next_update"] = now + update_interval
    progress["last_update"] = now
    progress["last_size"] = downloaded
    progress["last_speed"] = current_speed

    # Format progress message
    progress_text = (
        f"📥 <b>Downloading:</b> <code>{filename}</code>\n"
        f"💾 <b>Size:</b> {_format_bytes(total)}\n"
        f"📊 <b>Progress:</b> {percentage}% {_create_progress_bar(percentage)}\n"
        f"🚀 <b>Speed:</b> {_format_bytes(current_speed)}/s\n"
        f"⏳ <b>ETA:</b> {_format_time(eta) if eta >= 0 else 'Calculating...'}"
    )

    parse = await c.parseTextEntities(progress_text, types.TextParseModeHTML())
    edit = await c.editMessageText(chat_id, message_id, button, types.InputMessageText(parse))
    if isinstance(edit, types.Error):
        LOGGER.error(f"Progress update error: {edit}")

    if file.local.is_downloading_completed:
        elapsed_time = max(now - progress["start_time"], 1e-6)
        avg_speed = total / elapsed_time

        complete_text = (
            f"✅ <b>Download Complete:</b> <code>{filename}</code>\n"
            f"💾 <b>Size:</b> {_format_bytes(total)}\n"
            f"⏱ <b>Time Taken:</b> {_format_time(elapsed_time)}\n"
            f"⚡ <b>Avg Speed:</b> {_format_bytes(avg_speed)}/s"
        )

        parse = await c.parseTextEntities(complete_text, types.TextParseModeHTML())
        done = await c.editMessageText(chat_id, message_id, button, types.InputMessageText(parse))
        if isinstance(done, types.Error):
            LOGGER.error(f"Progress update error: {done}")

        download_progress.pop(file_id, None)
