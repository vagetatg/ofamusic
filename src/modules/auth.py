#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from pytdbot import Client, types
from typing import Optional
from src import db
from src.modules.utils import Filter
from src.modules.utils.admins import is_owner, is_admin


async def _validate_auth_command(msg: types.Message) -> Optional[types.Message]:
    chat_id = msg.chat_id
    if chat_id > 0:  # Private chat
        return None

    if not await is_owner(chat_id, msg.from_id):
        await msg.reply_text("You must be an owner to use this command.")
        return None

    reply = await msg.getRepliedMessage() if msg.reply_to_message_id else None
    if not reply:
        await msg.reply_text("Reply to a user to modify their auth permissions.")
        return None

    if isinstance(reply, types.Error):
        await msg.reply_text(f"⚠️ {reply.message}")
        return None

    if reply.from_id == msg.from_id:
        await msg.reply_text("You cannot modify your own auth permissions.")
        return None

    if isinstance(reply.sender_id, types.MessageSenderChat):
        await msg.reply_text("You cannot modify auth permissions of a group or another channel.")
        return None

    return reply


@Client.on_message(filters=Filter.command("auth"))
async def auth(_: Client, msg: types.Message):
    """Grant auth permissions to a user."""
    reply = await _validate_auth_command(msg)
    if not reply:
        return

    chat_id = msg.chat_id
    user_id = reply.from_id
    auth_users = await db.get_auth_users(chat_id)

    if user_id in auth_users:
        await msg.reply_text("User already has auth permissions.")
        return

    await db.add_auth_user(chat_id, user_id)
    await msg.reply_text("User has been given auth permissions.")
    return


@Client.on_message(filters=Filter.command("unauth"))
async def un_auth(_: Client, msg: types.Message):
    """Remove auth permissions from a user."""
    reply = await _validate_auth_command(msg)
    if not reply:
        return

    chat_id = msg.chat_id
    user_id = reply.from_id
    auth_users = await db.get_auth_users(chat_id)

    if user_id not in auth_users:
        await msg.reply_text("User does not have auth permissions.")
        return

    await db.remove_auth_user(chat_id, user_id)
    await msg.reply_text("User's auth permissions have been removed.")
    return

@Client.on_message(filters=Filter.command("authlist"))
async def auth_list(_: Client, msg: types.Message):
    chat_id = msg.chat_id
    if chat_id > 0:  # Private chat
        await msg.reply_text("This command can only be used in supergroups.")
        return None
    user_id = msg.from_id

    if not await is_admin(chat_id, user_id):
        await msg.reply_text("You must be an admin to use this command.")
        return

    auth_users = await db.get_auth_users(chat_id)
    if not auth_users:
        await msg.reply_text("No users have auth permissions.")
        return

    _auth_list = "\n".join([f"{user_id}" for user_id in auth_users])
    await msg.reply_text(f"Auth users:\n{_auth_list}")
    return
