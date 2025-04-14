#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio

from config import OWNER_ID
from src import db
from src.logger import LOGGER
from src.modules.utils import Filter
from src.modules.utils.play_helpers import extract_argument, del_msg

from pytdbot import types, Client

REQUEST_LIMIT = 5
semaphore = asyncio.Semaphore(REQUEST_LIMIT)
VALID_ARGS = {"all", "users", "chats", "copy"}


async def get_broadcast_targets(target: str) -> tuple[list[int], list[int]]:
    users = await db.get_all_users() if target in {"all", "users"} else []
    chats = await db.get_all_chats() if target in {"all", "chats"} else []
    return users, chats


async def send_message(target_id: int, message: types.Message, is_copy: bool) -> bool:
    try:
        async with semaphore:
            result = await (
                message.copy(target_id) if is_copy else message.forward(target_id)
            )
            if isinstance(result, types.Error):
                if result.code == 429:
                    retry_after = (
                        int(result.message.split("retry after ")[1])
                        if "retry after" in result.message
                        else 5
                    )
                    LOGGER.warning(
                        f"Rate limited, retrying in {retry_after} seconds..."
                    )
                    await asyncio.sleep(retry_after)
                    await (
                        message.copy(target_id)
                        if is_copy
                        else message.forward(target_id)
                    )
                elif result.code == 400:
                    LOGGER.warning(f"Invalid target {target_id}: {result.message}")
                    return False
                return False
        return True
    except Exception as e:
        LOGGER.error(f"Failed to send to {target_id}: {str(e)}")
        return False


async def broadcast_to_targets(
    targets: list[int], message: types.Message, is_copy: bool
) -> tuple[int, int]:
    sent = failed = 0
    for target_id in targets:
        success = await send_message(target_id, message, is_copy)
        if success:
            sent += 1
        else:
            failed += 1
    return sent, failed


@Client.on_message(filters=Filter.command("broadcast"))
async def broadcast(_: Client, message: types.Message):
    if int(message.from_id) != OWNER_ID:
        await del_msg(message)
        return

    args = extract_argument(message.text)
    if not args or args.lower() not in VALID_ARGS:
        return await message.reply_text(
            "Usage: /broadcast [all|users|chats|copy]\n"
            "• all: Send to all users and chats\n"
            "• users: Send to users only\n"
            "• chats: Send to chats only\n"
            "• copy: Send as copy (no forward info)"
        )

    target = args.lower()
    reply = await message.getRepliedMessage() if message.reply_to_message_id else None
    if not reply or isinstance(reply, types.Error):
        error_msg = str(reply) if isinstance(reply, types.Error) else ""
        return await message.reply_text(
            f"Please reply to the message you want to broadcast.\n\n{error_msg}"
        )

    users, chats = await get_broadcast_targets(target)
    if not users and not chats:
        return await message.reply_text("No users or chats to broadcast to.")

    # Broadcast to users and chats concurrently
    user_task = (
        broadcast_to_targets(users, reply, "copy" in target) if users else (0, 0)
    )
    chat_task = (
        broadcast_to_targets(chats, reply, "copy" in target) if chats else (0, 0)
    )

    user_sent, user_failed = await user_task
    chat_sent, chat_failed = await chat_task

    summary = (
        f"✅ <b>Broadcast Summary</b>\n"
        f"• Total Sent: {user_sent + chat_sent}\n"
        f"  - Users: {user_sent}\n"
        f"  - Chats: {chat_sent}\n"
        f"• Total Failed: {user_failed + chat_failed}\n"
        f"  - Users: {user_failed}\n"
        f"  - Chats: {chat_failed}"
    )

    await message.reply_text(summary)
