import asyncio
import contextlib
from typing import Union

from cachetools import TTLCache
from pyrogram import Client, enums, errors, types

from src.logger import LOGGER

user_status_cache = TTLCache(maxsize=5000, ttl=600)
chat_invite_cache = TTLCache(maxsize=1000, ttl=600)


async def get_url(message_1: types.Message) -> Union[str, None]:
    messages = [message_1]

    if message_1.reply_to_message:
        messages.append(message_1.reply_to_message)

    text = ""
    offset = None
    length = None

    for message in messages:
        if offset:
            break
        if message.entities:
            for entity in message.entities:
                if entity.type == enums.MessageEntityType.URL:
                    text = message.text or message.caption
                    offset, length = entity.offset, entity.length
                    break

    return None if offset in (None,) else text[offset : offset + length]


def extract_argument(text: str, enforce_digit: bool = False) -> str | None:
    """Extracts the argument from the command text.

    Args:
        text (str): The full command text.
        enforce_digit (bool): Whether to enforce that the argument is a digit.

    Returns:
        str | None: The extracted argument or None if invalid.
    """
    args = text.strip().split(maxsplit=1)

    if len(args) < 2:
        return None

    argument = args[1].strip()
    return None if enforce_digit and not argument.isdigit() else argument


async def del_msg(msg: types.Message):
    with contextlib.suppress(errors.RPCError):
        await msg.delete()


async def edit_text(msg: types.Message, text: str, **kwargs) -> types.Message | None:
    if msg is None or text is None:
        LOGGER.warning("⚠️ edit_text: msg or text is None")
        return None

    try:
        if msg.caption:
            return await msg.edit_caption(text, **kwargs)
        return await msg.edit_text(text, **kwargs)
    except errors.FloodWait as e:
        await asyncio.sleep(e.value + 0.5)
        return await edit_text(msg, text, **kwargs)
    except errors.MessageNotModified:
        return msg
    except errors.MessageEmpty:
        return await msg.reply_text(text, **kwargs)
    except errors.MsgIdInvalid:
        return await msg.reply_text(text, **kwargs)
    except Exception as e:
        LOGGER.error(f"❌ Unexpected error in edit_text: {e}")
        return None


async def join_ub(chat_id: int, c: Client, ub: Client):
    """Handles the userbot joining a chat via invite link or approval."""
    invite_link = chat_invite_cache.get(
        chat_id, (await c.get_chat(chat_id)).invite_link
    )
    if not invite_link:
        raise Exception("Invite link not found!")

    chat_invite_cache[chat_id] = invite_link
    invite_link = invite_link.replace("https://t.me/+", "https://t.me/joinchat/")
    user_key = f"{chat_id}:{ub.me.id}"
    try:
        await ub.join_chat(invite_link)
        user_status_cache[user_key] = enums.ChatMemberStatus.MEMBER
    except errors.InviteRequestSent:
        with contextlib.suppress(Exception):
            await c.approve_chat_join_request(chat_id=chat_id, user_id=ub.me.id)
    except errors.UserAlreadyParticipant:
        user_status_cache[user_key] = enums.ChatMemberStatus.MEMBER
    except Exception as e:
        # user_status_cache[user_key] = enums.ChatMemberStatus.BANNED
        raise Exception(
            f"⚠️ Something went wrong while joining the chat.\nError: {str(e).replace('Telegram says', '')}"
        ) from e


async def unban_ub(c: Client, chat_id: int, user_id: int):
    try:
        await c.unban_chat_member(chat_id=chat_id, user_id=user_id)
    except Exception as e:
        raise Exception(
            f"⚠️ Something went wrong while un-banning the my assistant.\nError:"
            + str(e).replace("Telegram says", "")
        ) from e


async def check_user_status(
    c: Client, chat_id: int, user_id: int
) -> enums.ChatMemberStatus:
    user_key = f"{chat_id}:{user_id}"
    user_status = user_status_cache.get(user_key, None)
    if not user_status:
        try:
            user = await c.get_chat_member(chat_id, user_id)
            user_status = user.status
        except errors.UserNotParticipant:
            user_status = enums.ChatMemberStatus.LEFT

        user_status_cache[user_key] = user_status

    return user_status
