#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import time
import math
from pytdbot import Client, types
from src.logger import LOGGER
from src.platforms.telegram import Telegram

download_progress = {}  # Tracks per-file download status by file_id


def _format_bytes(size: int) -> str:
    """Convert bytes to human-readable format with precision."""
    if size < 1024:
        return f"{size} B"
    for unit in ["KB", "MB", "GB", "TB"]:
        size /= 1024
        if size < 1024:
            return f"{size:.1f} {unit}"
    return f"{size:.1f} PB"


def _format_time(seconds: int) -> str:
    """Convert time in seconds to a compact human-readable string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)}m {int(seconds)}s"
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours)}h {int(minutes)}m"


def _create_progress_bar(percentage: int, length: int = 10) -> str:
    """Create a textual progress bar based on percentage."""
    percentage = min(100, max(0, percentage))
    filled = round(length * percentage / 100)
    return "⬢" * filled + "⬡" * (length - filled)


def _calculate_update_interval(file_size: int, current_speed: float) -> float:
    """
    Determine the next update interval based on file size and speed.
    Larger files = longer base interval.
    Higher speed = shorter interval.
    Returns a float between 1.0s and 5.0s.
    """
    if file_size < 5 * 1024 * 1024:  # <5MB
        base = 1.0
    else:
        scale = min(math.log10(file_size / (5 * 1024 * 1024)), 2)
        base = 1.0 + scale * 2.0

    if current_speed > 1024 * 1024:  # >1MB/s
        speed_mod = max(0.5, 2.0 - (current_speed / (5 * 1024 * 1024)))
    else:
        speed_mod = 1.0

    return min(max(base * speed_mod, 1.0), 5.0)


@Client.on_updateFile()
async def update_file(client: Client, update: types.UpdateFile):
    file = update.file
    unique_id = file.remote.unique_id
    tg = Telegram(None)
    meta = tg.get_cached_metadata(unique_id)
    if not meta:
        return

    # UI Elements
    button_markup = types.ReplyMarkupInlineKeyboard(
        [[
            types.InlineKeyboardButton(
                text="✗ Stop Downloading",
                type=types.InlineKeyboardButtonTypeCallback(f"play_c_{unique_id}".encode())
            ),
        ]]
    )

    chat_id = meta["chat_id"]
    filename = meta["filename"]
    message_id = meta["message_id"]
    file_id = file.id
    now = time.time()

    total = file.size or 1
    downloaded = file.local.downloaded_size
    percentage = min(100, int((downloaded / total) * 100))

    if file_id not in download_progress:
        download_progress[file_id] = {
            "start_time": now,
            "last_update": now,
            "last_size": downloaded,
            "next_update": now + 1.0,
            "last_speed": 0,
        }

    progress = download_progress[file_id]

    # Skip update if it's not time yet and the file is still downloading
    if now < progress["next_update"] and not file.local.is_downloading_completed:
        return

    elapsed = now - progress["last_update"]
    delta = downloaded - progress["last_size"]
    speed = delta / elapsed if elapsed > 0 else 0
    eta = int((total - downloaded) / speed) if speed > 0 else -1

    interval = _calculate_update_interval(total, speed)
    progress.update({
        "next_update": now + interval,
        "last_update": now,
        "last_size": downloaded,
        "last_speed": speed,
    })

    # Progress message
    progress_text = (
        f"📥 <b>Downloading:</b> <code>{filename}</code>\n"
        f"💾 <b>Size:</b> {_format_bytes(total)}\n"
        f"📊 <b>Progress:</b> {percentage}% {_create_progress_bar(percentage)}\n"
        f"🚀 <b>Speed:</b> {_format_bytes(speed)}/s\n"
        f"⏳ <b>ETA:</b> {_format_time(eta) if eta >= 0 else 'Calculating...'}"
    )

    parsed = await client.parseTextEntities(progress_text, types.TextParseModeHTML())
    edit = await client.editMessageText(chat_id, message_id, button_markup, types.InputMessageText(parsed))
    if isinstance(edit, types.Error):
        LOGGER.error(f"Progress update error: {edit}")

    if file.local.is_downloading_completed:
        duration = max(now - progress["start_time"], 1e-6)
        avg_speed = total / duration

        complete_text = (
            f"✅ <b>Download Complete:</b> <code>{filename}</code>\n"
            f"💾 <b>Size:</b> {_format_bytes(total)}\n"
            f"⏱ <b>Time Taken:</b> {_format_time(duration)}\n"
            f"⚡ <b>Average Speed:</b> {_format_bytes(avg_speed)}/s"
        )

        parsed = await client.parseTextEntities(complete_text, types.TextParseModeHTML())
        done = await client.editMessageText(chat_id, message_id, button_markup, types.InputMessageText(parsed))
        if isinstance(done, types.Error):
            LOGGER.error(f"Download complete update error: {done}")

        download_progress.pop(file_id, None)
