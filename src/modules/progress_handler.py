import time

from pytdbot import Client, types
from src.logger import LOGGER
from src.platforms.telegram import Telegram

download_progress = {}  # file_id: tracking info
last_progress_update = {}  # file_id: (last_time, last_percent)


def _format_bytes(size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


def _format_time(seconds: int) -> str:
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _create_progress_bar(percentage: int, length: int = 12) -> str:
    filled = int(length * percentage / 100)
    return '▰' * filled + '▱' * (length - filled)


def should_update_progress(file_id: int, percent: int) -> bool:
    now = time.time()
    last = last_progress_update.get(file_id)

    if not last:
        last_progress_update[file_id] = (now, percent)
        return True

    last_time, last_percent = last
    if now - last_time >= 2 or abs(percent - last_percent) >= 1:
        last_progress_update[file_id] = (now, percent)
        return True

    return False


@Client.on_updateFile()
async def update_file(c: Client, update: types.UpdateFile):
    # LOGGER.info("File updated: %s", update.file)
    file = update.file
    unique_id = file.remote.unique_id

    tg = Telegram(None)
    meta = tg.get_cached_metadata(unique_id)
    if not meta:
        return

    chat_id = meta["chat_id"]
    filename = meta["filename"]
    message_id = meta["message_id"]
    file_id = file.id
    now = time.time()

    total = file.size or 1
    downloaded = file.local.downloaded_size
    percentage = min(100, int((downloaded / total) * 100))

    # Init tracking
    if file_id not in download_progress:
        download_progress[file_id] = {
            "start_time": now,
            "last_update": 0,
            "last_size": 0,
            "message_id": None,
        }

    progress = download_progress[file_id]
    elapsed = now - progress["last_update"]
    delta = downloaded - progress["last_size"]
    speed = delta / elapsed if elapsed > 0 else 0
    eta = int((total - downloaded) / speed) if speed > 0 else -1

    if not should_update_progress(file_id, percentage) and not file.local.is_downloading_completed:
        return

    # Update tracking state
    progress["last_update"] = now
    progress["last_size"] = downloaded

    # Format progress message
    progress_text = (
        f"📥 <b>Downloading:</b> <code>{filename}</code>\n"
        f"💾 <b>Size:</b> {_format_bytes(total)}\n"
        f"📊 <b>Progress:</b> {percentage}% {_create_progress_bar(percentage)}\n"
        f"🚀 <b>Speed:</b> {_format_bytes(speed)}/s\n"
        f"⏳ <b>ETA:</b> {_format_time(eta) if eta >= 0 else 'Calculating...'}"
    )

    parse = await c.parseTextEntities(progress_text, types.TextParseModeHTML())
    edit = await c.editMessageText(chat_id, message_id, input_message_content=types.InputMessageText(parse))
    if isinstance(edit, types.Error):
        LOGGER.error(f"Edit progress message failed: {edit}")

    # Final completion message
    if file.local.is_downloading_completed:
        complete_text = (
            f"✅ <b>Download Complete:</b> <code>{filename}</code>\n"
            f"💾 <b>Size:</b> {_format_bytes(total)}\n"
            f"⏱ <b>Time Taken:</b> {_format_time(now - progress['start_time'])}"
        )
        try:
            parse = await c.parseTextEntities(complete_text, types.TextParseModeHTML())
            await c.editMessageText(chat_id, message_id, input_message_content=types.InputMessageText(parse))
        except Exception as e:
            LOGGER.error(f"Completion message error: {e}")
        finally:
            download_progress.pop(file_id, None)
            last_progress_update.pop(file_id, None)
            tg.clear_cache(unique_id)
