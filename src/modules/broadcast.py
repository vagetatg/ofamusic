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

REQUEST = 5
semaphore = asyncio.Semaphore(REQUEST)
VALID_ARGS = {"all", "users", "chats", "copy"}

@Client.on_message(filters=Filter.command("broadcast"))
async def broadcast(_: Client, message: types.Message):
    if int(message.from_id) != OWNER_ID:
        await del_msg(message)
        return

    args = extract_argument(message.text)
    if not args or args.lower() not in VALID_ARGS:
        return await message.reply_text("Usage: /broadcast [all|users|chats|copy]")

    target = args.lower()
    reply = await message.getRepliedMessage() if message.reply_to_message_id else None
    if not reply or isinstance(reply, types.Error):
        return await message.reply_text(f"Please reply to the message you want to broadcast.\n\n{str(reply if isinstance(reply, types.Error) else '')}")

    all_users: list[int] = await db.get_all_users() if target in ("all", "users") else []
    all_chats: list[int] = await db.get_all_chats() if target in ("all", "chats") else []

    if not all_users and not all_chats:
        return await message.reply_text("No users or chats to broadcast to.")

    async def broadcast_to(targets: list[int]):
        sent = failed = 0
        for target_id in targets:
            try:
                async with semaphore:
                    fwd = await reply.copy(target_id) if target in "copy" else await reply.forward(target_id)
                    if isinstance(fwd, types.Error):
                        if fwd.code == 429:
                            retry_after = int(fwd.message.split("retry after ")[1]) if "retry after" in fwd.message else 0
                            LOGGER.warning(f"Rate limited, retrying in {retry_after} seconds...")
                            await asyncio.sleep(retry_after)
                            await reply.forward(target_id)
                        elif fwd.code == 400:
                            # TODO: remove from db
                            failed += 1
                            continue
                        failed += 1
                        continue
                sent += 1
            except Exception as e:
                LOGGER.error(f"Failed to send to {target_id}: {e}")
                failed += 1
        return sent, failed

    user_sent = user_failed = chat_sent = chat_failed = 0
    if all_users:
        user_sent, user_failed = await broadcast_to(all_users)
    if all_chats:
        chat_sent, chat_failed = await broadcast_to(all_chats)

    await message.reply_text(
        f"✅ <b>Broadcast Summary</b>\n"
        f"- Sent: {user_sent + chat_sent}\n"
        f"  • Users: {user_sent}\n"
        f"  • Chats: {chat_sent}\n"
        f"- Failed: {user_failed + chat_failed}\n"
        f"  • Users: {user_failed}\n"
        f"  • Chats: {chat_failed}"
    )
