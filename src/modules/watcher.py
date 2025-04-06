#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.
from types import NoneType

from pytdbot import Client, types

from src import call
from src.database import db
from src.logger import LOGGER
from src.modules.utils.admins import load_admin_cache
from src.modules.utils.buttons import add_me_button
from src.modules.utils.cacher import chat_cache
from src.modules.utils.play_helpers import user_status_cache


async def handle_non_supergroup(client: Client, chat_id: int):
    """Handles cases where the bot is added to a non-supergroup chat."""
    text = f"""{chat_id} is not a supergroup yet.
<b>⚠️: Please convert this chat to a supergroup and add me as admin.</b>

If you don't know how to convert, use this guide:
🔗 https://te.legra.ph/How-to-Convert-a-Group-to-a-Supergroup-01-02

If you have any questions, join our support group:
"""
    bot_username = client.me.usernames.editable_username
    await client.sendTextMessage(chat_id, text, parse_mode="HTML", reply_markup=add_me_button(bot_username))
    await client.leaveChat(chat_id)
    return


@Client.on_updateChatMember()
async def chat_member(client: Client, update: types.UpdateChatMember):
    """Handles member updates in the chat (joins, leaves, promotions, demotions, bans, and unbans)."""
    chat_id = update.chat_id
    if not str(chat_id).startswith("-100"):
        return await handle_non_supergroup(client, chat_id)

    await db.add_chat(chat_id)
    user_id = update.new_chat_member.member_id.user_id
    old_status = update.old_chat_member.status["@type"]
    new_status = update.new_chat_member.status["@type"]

    # User Joined (New Member)
    if old_status == "chatMemberStatusLeft" and new_status in {
        "chatMemberStatusMember",
        "chatMemberStatusAdministrator",
    }:
        LOGGER.info(f"User {user_id} joined the chat {chat_id}.")
        return

    # User Left (Left or Kicked)
    if (
        old_status in {"chatMemberStatusMember", "chatMemberStatusAdministrator"}
        and new_status == "chatMemberStatusLeft"
    ):
        LOGGER.info(f"User {user_id} left or was kicked from {chat_id}.")
        ub = await call.get_client(chat_id)
        if isinstance(ub, (types.Error, NoneType)):
            return
        user_key = f"{chat_id}:{ub.me.id}"
        if user_id == ub.me.id:
            user_status_cache[user_key] = "chatMemberStatusLeft"
        return

    # User Banned
    if new_status == "chatMemberStatusBanned":
        LOGGER.info(f"User {user_id} was banned in {chat_id}.")
        ub = await call.get_client(chat_id)
        if isinstance(ub, (types.Error, NoneType)):
            return
        user_key = f"{chat_id}:{ub.me.id}"
        if user_id == ub.me.id:
            user_status_cache[user_key] = "chatMemberStatusBanned"
        return

    # User Unbanned
    if old_status == "chatMemberStatusBanned" and new_status == "chatMemberStatusLeft":
        LOGGER.info(f"User {user_id} was unbanned in {chat_id}.")
        return

    is_promoted = (
        old_status != "chatMemberStatusAdministrator"
        and new_status == "chatMemberStatusAdministrator"
    )

    # Bot Promoted
    if user_id == client.options["my_id"] and is_promoted:
        LOGGER.info(f"Bot was promoted in {chat_id}, reloading admin permissions.")
        await load_admin_cache(client, chat_id, True)
        return

    # User Promoted
    if is_promoted:
        LOGGER.info(f"User {user_id} was promoted in {chat_id}.")
        await load_admin_cache(client, chat_id, True)
        return

    # User Demoted
    is_demoted = (
        old_status == "chatMemberStatusAdministrator"
        and new_status != "chatMemberStatusAdministrator"
    )

    if is_demoted:
        LOGGER.info(f"User {user_id} was demoted in {chat_id}.")
        if user_id == client.options["my_id"] or client.me.id:
            return
        await load_admin_cache(client, chat_id, True)
        return

    return


@Client.on_updateNewMessage(position=1)
async def new_message(c: Client, update: types.UpdateNewMessage):
    if not hasattr(update, "message"):
        return
    message = update.message
    if isinstance(message.content, types.MessageVideoChatEnded):
        LOGGER.info(f"Video chat ended in {message.chat_id}")
        await chat_cache.clear_chat(message.chat_id)
        _ = await c.sendTextMessage(message.chat_id, f"Video chat ended!\n")
        return
    elif isinstance(message.content, types.MessageVideoChatStarted):
        LOGGER.info(f"Video chat started in {message.chat_id}")
        await chat_cache.clear_chat(message.chat_id)
        return

    LOGGER.debug(f"New message in {message.chat_id}: {message}")
    return
