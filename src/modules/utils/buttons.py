import asyncio
from pyrogram import Client, types
from src.logger import LOGGER
from src.modules.utils.cacher import chat_cache


def play_button(current_seconds: int, total_seconds: int) -> types.InlineKeyboardMarkup:
    if total_seconds == 0:
        button_text = " 🎵 Playing"
    else:
        progress = round((current_seconds / total_seconds) * 10) if total_seconds > 0 else 0
        bar = ["—"] * 10
        bar[min(progress, 9)] = "◉"
        progress_bar_text = "".join(bar)
        button_text = f"{current_seconds // 60}:{current_seconds % 60} {progress_bar_text} {total_seconds // 60}:{total_seconds % 60}"

    return types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton(button_text, callback_data="timer")],
        [
            types.InlineKeyboardButton("▶️ Skip", callback_data="play_skip"),
            types.InlineKeyboardButton("⏹️ End", callback_data="play_stop"),
        ],
        [
            types.InlineKeyboardButton("⏸️ Pause", callback_data="play_pause"),
            types.InlineKeyboardButton("⏯️ Resume", callback_data="play_resume"),
        ],
    ])


async def update_progress_bar(message: types.Message, current_seconds: int, total_seconds: int) -> None:
    """Updates the progress bar in the message at regular intervals."""
    if not message:
        return
    chat_id = message.chat.id
    error_count = 0
    update_interval = total_seconds // 15 if total_seconds > 150 else 6
    max_errors = 3

    while current_seconds <= total_seconds and await chat_cache.is_active(chat_id):
        keyboard = play_button(current_seconds, total_seconds)
        try:
            await message.edit_reply_markup(reply_markup=keyboard)
            error_count = 0  # Reset on success
        except Exception as e:
            LOGGER.error(f"Error updating progress bar: {e}")
            error_count += 1
            if error_count >= max_errors:
                LOGGER.warning(f"Max errors ({max_errors}) reached, stopping updates")
                break

        await asyncio.sleep(update_interval)
        current_seconds += update_interval

PauseButton = types.InlineKeyboardMarkup(
    [
        [
            types.InlineKeyboardButton(
                text="▶️ Skip", callback_data="play_skip"
            ),
            types.InlineKeyboardButton(
                text="⏹️ End", callback_data="play_stop"
            ),
        ],
        [
            types.InlineKeyboardButton(
                text="⏯️ Resume",
                callback_data="play_resume",
            ),
        ],
    ]
)

ResumeButton = types.InlineKeyboardMarkup(
    [
        [
            types.InlineKeyboardButton(
                text="▶️ Skip", callback_data="play_skip"
            ),
            types.InlineKeyboardButton(
                text="⏹️ End", callback_data="play_stop"
            ),
        ],
        [
            types.InlineKeyboardButton(
                text="⏸️ Pause",
                callback_data="play_pause",
            ),
        ],
    ]
)

SupportButton = types.InlineKeyboardMarkup(
    [
        [
            types.InlineKeyboardButton(
                text="❄ Channel",
                url="https://t.me/FallenProjects",
            ),
            types.InlineKeyboardButton(
                text="✨ Group",
                url="https://t.me/GuardxSupport",
            ),
        ]
    ]
)

AddMeButton = types.InlineKeyboardMarkup(
    [
        [
            types.InlineKeyboardButton(
                text="Add me to your group",
                url="https://t.me/FallenBeatzBot?startgroup=true",
            ),
        ],
        [
            types.InlineKeyboardButton(
                text="❄ Channel",
                url="https://t.me/FallenProjects",
            ),
            types.InlineKeyboardButton(
                text="✨ Group",
                url="https://t.me/GuardxSupport",
            ),
        ],
    ]
)
