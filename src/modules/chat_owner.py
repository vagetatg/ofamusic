#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from typing import Union

from pytdbot import Client, types

from src.helpers import db, get_string
from src.logger import LOGGER
from src.modules.utils import Filter
from src.modules.utils.admins import is_admin, is_owner, load_admin_cache
from src.modules.utils.play_helpers import extract_argument


async def _validate_auth_command(msg: types.Message) -> Union[types.Message, None]:
    chat_id = msg.chat_id
    if chat_id > 0:
        return None

    lang = await db.get_lang(chat_id)

    if not await is_owner(chat_id, msg.from_id):
        reply = await msg.reply_text(get_string("only_owner", lang))
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)
        return None

    if not msg.reply_to_message_id:
        reply = await msg.reply_text(get_string("reply_manage_auth", lang))
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)
        return None

    reply = await msg.getRepliedMessage()
    if isinstance(reply, types.Error):
        reply = await msg.reply_text(f"⚠️ {reply.message}")
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)
        return None

    if reply.from_id == msg.from_id:
        _reply = await msg.reply_text(get_string("cannot_change_self", lang))
        if isinstance(_reply, types.Error):
            LOGGER.warning(_reply.message)
        return None

    if isinstance(reply.sender_id, types.MessageSenderChat):
        _reply = await msg.reply_text(get_string("cannot_change_channel", lang))
        if isinstance(_reply, types.Error):
            LOGGER.warning(_reply.message)
        return None

    return reply


@Client.on_message(filters=Filter.command("auth"))
async def auth(c: Client, msg: types.Message) -> None:
    reply = await _validate_auth_command(msg)
    if not reply:
        return

    chat_id = msg.chat_id
    user_id = reply.from_id
    lang = await db.get_lang(chat_id)

    if user_id in await db.get_auth_users(chat_id):
        reply =await msg.reply_text(get_string("user_already_auth", lang))
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)
    else:
        await db.add_auth_user(chat_id, user_id)
        reply = await msg.reply_text(get_string("user_granted_auth", lang))
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)


@Client.on_message(filters=Filter.command("unauth"))
async def un_auth(c: Client, msg: types.Message) -> None:
    reply = await _validate_auth_command(msg)
    if not reply:
        return

    chat_id = msg.chat_id
    user_id = reply.from_id
    lang = await db.get_lang(chat_id)

    if user_id not in await db.get_auth_users(chat_id):
        reply = await msg.reply_text(get_string("user_not_auth", lang))
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)
    else:
        await db.remove_auth_user(chat_id, user_id)
        reply = await msg.reply_text(get_string("user_removed_auth", lang))
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)


@Client.on_message(filters=Filter.command("authlist"))
async def auth_list(c: Client, msg: types.Message) -> None:
    chat_id = msg.chat_id
    lang = await db.get_lang(chat_id)

    if chat_id > 0:
        reply = await msg.reply_text(get_string("only_group", lang))
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)
        return

    if not await is_admin(chat_id, msg.from_id):
        reply = await msg.reply_text(get_string("only_admin", lang))
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)
        return

    auth_users = await db.get_auth_users(chat_id)
    if not auth_users:
        reply = await msg.reply_text(get_string("no_auth_users", lang))
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)
        return

    text = (
        get_string("auth_list_header", lang)
        + "\n"
        + "\n".join([f"- <code>{uid}</code>" for uid in auth_users])
    )
    reply = await msg.reply_text(text)
    if isinstance(reply, types.Error):
        c.logger.warning(reply.message)


async def _handle_toggle_command(
    msg: types.Message, key: str, label: str, get_func, set_func
) -> None:
    chat_id = msg.chat_id
    lang = await db.get_lang(chat_id)

    if chat_id > 0:
        reply = await msg.reply_text(get_string("only_group", lang))
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)
        return

    if not await is_owner(chat_id, msg.from_id):
        reply = await msg.reply_text(get_string("only_owner", lang))
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)
        return

    current = await get_func(chat_id)
    args = extract_argument(msg.text)
    if not args:
        status = (
            get_string("enabled", lang) if current else get_string("disabled", lang)
        )
        reply = await msg.reply_text(
            get_string("toggle_status", lang).format(
                label=label, status=status, key=key
            )
        )
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)
        return

    arg = args.lower()
    if arg in ["on", "enable"]:
        await set_func(chat_id, True)
        reply = await msg.reply_text(get_string(f"{key}_status_enabled", lang))
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)
    elif arg in ["off", "disable"]:
        await set_func(chat_id, False)
        reply = await msg.reply_text(get_string(f"{key}_status_disabled", lang))
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)
    else:
        reply = await msg.reply_text(get_string("invalid_toggle_usage", lang).format(key=key))
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)


@Client.on_message(filters=Filter.command("buttons"))
async def buttons(_: Client, msg: types.Message) -> None:
    await _handle_toggle_command(
        msg, "buttons", "Button control", db.get_buttons_status, db.set_buttons_status
    )
    return


@Client.on_message(filters=Filter.command(["thumbnail", "thumb"]))
async def thumbnail(_: Client, msg: types.Message) -> None:
    await _handle_toggle_command(
        msg, "thumbnail", "Thumbnail", db.get_thumb_status, db.set_thumb_status
    )
    return

@Client.on_message(filters=Filter.command("channelplay"))
async def set_channel_id(c: Client, msg: types.Message) -> None:
    chat_id = msg.chat_id
    reply = await msg.getRepliedMessage() if msg.reply_to_message_id else None
    if not reply or isinstance(reply, types.Error):
        await msg.reply_text("⚠️ Reply to a channel to set it as the channel to play from. (with forward tag)")
        return

    if reply.forward_info is None:
        await msg.reply_text("⚠️ Reply to a channel to set it as the channel to play from. (with forward tag)")
        return

    forward_info = reply.forward_info
    if forward_info.origin is None:
        await msg.reply_text("⚠️ Reply to a channel to set it as the channel to play from. (with forward tag)")
        return

    if forward_info.origin.getType() != types.MessageOriginChannel().getType():
        await msg.reply_text("⚠️ Reply to a channel to set it as the channel to play from. (with forward tag)")
        return

    channel_id = reply.forward_info.origin.chat_id
    user_id = msg.from_id

    # MAKE SURE USER IS OWNER OF CHAT OR CHANNEL
    if not await is_owner(chat_id, user_id):
        await msg.reply_text("You must be an owner of this chat to set the channel to play from this chat\n\nIf you are use /reload")
        return

    # TODO: Remove this
    await load_admin_cache(c, channel_id)

    if not await is_owner(channel_id, user_id):
        await msg.reply_text("You must be an owner of the channel to set it as the channel to play from this chat\n\nIf you are use /creload")
        return

    await db.set_channel_id(chat_id, channel_id)
    await msg.reply_text(f"Channel set to: {channel_id}")
