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

# Broadcast tuning
REQUEST_LIMIT = 10  # concurrency per batch
BATCH_SIZE = 100    # targets per batch
BATCH_DELAY = 5     # seconds between batches
MAX_RETRIES = 2

semaphore = asyncio.Semaphore(REQUEST_LIMIT)
VALID_TARGETS = {"all", "users", "chats"}


async def get_broadcast_targets(target: str) -> tuple[list[int], list[int]]:
    users = await db.get_all_users() if target in {"all", "users"} else []
    chats = await db.get_all_chats() if target in {"all", "chats"} else []
    return users, chats


async def send_message_with_retry(target_id: int, message: types.Message, is_copy: bool) -> int:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with semaphore:
                result = await (message.copy(target_id) if is_copy else message.forward(target_id))

            if isinstance(result, types.Error):
                if result.code == 429:
                    retry_after = (
                        int(result.message.split("retry after ")[1])
                        if "retry after" in result.message
                        else 2
                    )
                    LOGGER.warning(f"[FloodWait] Retry {attempt}/{MAX_RETRIES} in {retry_after}s for {target_id}")
                    await asyncio.sleep(retry_after)
                    continue
                elif result.code == 400:
                    LOGGER.warning(f"Bad request for {target_id}: {result.message}")
                    return 0
                return 0

            return 1

        except Exception as e:
            LOGGER.error(f"[Error] {target_id}: {e}")
            await asyncio.sleep(2)

    return 0


async def broadcast_to_targets(targets: list[int], message: types.Message, is_copy: bool) -> tuple[int, int]:
    sent = failed = 0

    for i in range(0, len(targets), BATCH_SIZE):
        batch = targets[i:i + BATCH_SIZE]
        LOGGER.info(f"Sending batch {i // BATCH_SIZE + 1}/{(len(targets) + BATCH_SIZE - 1) // BATCH_SIZE}")

        results = await asyncio.gather(*[
            send_message_with_retry(tid, message, is_copy) for tid in batch
        ])

        batch_sent = sum(results)
        batch_failed = len(batch) - batch_sent
        sent += batch_sent
        failed += batch_failed

        LOGGER.info(f"Batch sent: {batch_sent}, failed: {batch_failed}")
        await asyncio.sleep(BATCH_DELAY)

    return sent, failed


@Client.on_message(filters=Filter.command("broadcast"))
async def broadcast(_: Client, message: types.Message):
    if int(message.from_id) != OWNER_ID:
        await del_msg(message)
        return

    args = extract_argument(message.text)
    if not args:
        return await message.reply_text(
            "Usage: <code>/broadcast [all|users|chats] [copy]</code>\n"
            "• <b>all</b>: All users and chats\n"
            "• <b>users</b>: Only users\n"
            "• <b>chats</b>: Only groups/channels\n"
            "• <b>copy</b>: Send as copy (no forward tag)"
        )

    parts = args.lower().split()
    is_copy = "copy" in parts
    target = next((p for p in parts if p in VALID_TARGETS), None)

    if not target:
        return await message.reply_text("Please specify a valid target: all, users, or chats.")

    reply = await message.getRepliedMessage() if message.reply_to_message_id else None
    if not reply or isinstance(reply, types.Error):
        return await message.reply_text("Please reply to a message to broadcast.")

    users, chats = await get_broadcast_targets(target)
    if not users and not chats:
        return await message.reply_text("No users or chats to broadcast to.")

    started = await message.reply_text(
        text=f"📣 Starting broadcast to {len(users) + len(chats)} target(s)...\n"
        f"• Users: {len(users)}\n"
        f"• Chats: {len(chats)}\n"
        f"• Mode: {'Copy' if is_copy else 'Forward'}",
        disable_web_page_preview=True,
    )

    if isinstance(started, types.Error):
        LOGGER.warning(f"Error starting broadcast: {started}")
        return

    user_sent, user_failed = await broadcast_to_targets(users, reply, is_copy)
    chat_sent, chat_failed = await broadcast_to_targets(chats, reply, is_copy)

    await started.edit_text(
        text=f"✅ <b>Broadcast Summary</b>\n"
        f"• Total Sent: {user_sent + chat_sent}\n"
        f"  - Users: {user_sent}\n"
        f"  - Chats: {chat_sent}\n"
        f"• Total Failed: {user_failed + chat_failed}\n"
        f"  - Users: {user_failed}\n"
        f"  - Chats: {chat_failed}",
        disable_web_page_preview=True,
    )
