from pyrogram import Client, errors
from pyrogram.enums import ChatMemberStatus as Cms, ChatType
from pyrogram.types import Message, ChatMemberUpdated

from src import call
from src.logger import LOGGER
from src.modules.utils import SupportButton
from src.modules.utils.admins import load_admin_cache
from src.modules.utils.cacher import chat_cache
from src.modules.utils.play_helpers import user_status_cache


async def video_chat_watcher(client: Client, message: Message):
    """Handles ending an active video chat when a new one starts."""
    chat = message.chat
    if chat.type != ChatType.SUPERGROUP:
        await handle_non_supergroup(client, chat)
        return

    chat_id = chat.id
    if await chat_cache.is_active(chat_id):
        try:
            await chat_cache.clear_chat(chat_id)
            await call.end(chat_id)
        except Exception as e:
            LOGGER.warning(f"Failed to stop video chat in {chat_id}: {e}")
    else:
        await chat_cache.clear_chat(chat_id)


async def handle_non_supergroup(client: Client, chat):
    """Handles cases where the bot is added to a non-supergroup chat."""
    text = f"""{chat.title} is not a supergroup yet.
<b>⚠️: Please convert this chat to a supergroup and add me as admin.</b>

If you don't know how to convert, use this guide:
🔗 https://te.legra.ph/How-to-Convert-a-Group-to-a-Supergroup-01-02

If you have any questions, join our support group:
"""
    try:
        await client.send_message(chat.id, text, reply_markup=SupportButton)
        await client.leave_chat(chat.id)
    except errors.RPCError:
        pass
    except Exception as e:
        LOGGER.warning(f"Error handling non-supergroup {chat.id}: {e}")


async def handle_member_update(client: Client, member: ChatMemberUpdated):
    """Handles member updates in the chat (joins, leaves, promotions, demotions)."""
    chat = member.chat
    new_status = member.new_chat_member.status if member.new_chat_member else None
    old_status = member.old_chat_member.status if member.old_chat_member else None
    user = member.new_chat_member.user if member.new_chat_member else member.old_chat_member.user

    if chat.type != ChatType.SUPERGROUP:
        await handle_non_supergroup(client, chat)
        return

    ub = await call.get_client(chat.id)
    if ub is None:
        LOGGER.warning(f"Client not found for {chat.id}")
        return

    # Handle user joins
    if new_status and new_status not in {Cms.RESTRICTED, Cms.BANNED} and old_status is None:
        await handle_user_join(client, ub, chat, user)

    # Handle user leaves
    elif old_status and old_status not in {Cms.BANNED, Cms.RESTRICTED} and new_status is None:
        await handle_user_leave(client, ub, chat, user)

    # Handle promotions/demotions
    elif old_status and new_status and old_status != new_status:
        await handle_promotion_or_demotion(client, chat, user, old_status, new_status)


async def handle_user_join(client: Client, ub: Client, chat, user):
    """Handles when a user joins the chat."""
    if user.id == client.me.id:
        try:
            await client.resolve_peer(chat.id)
        except Exception as e:
            LOGGER.warning(f"Error resolving peer for bot join event in {chat.id}: {e}")
        return

    if user.id == ub.me.id:
        try:
            chat_id = chat.username or chat.id
            await ub.resolve_peer(chat_id)
        except Exception as e:
            LOGGER.warning(f"Error resolving bot peer in {chat.id}: {e}")


async def handle_user_leave(client: Client, ub: Client, chat, user):
    """Handles when a user leaves the chat."""
    user_key = f"{chat.id}:{ub.me.id}"
    try:
        if user.id == client.me.id:
            await chat_cache.clear_chat(chat.id)
            await ub.leave_chat(chat.id)
        if user.id == ub.me.id:
            if await chat_cache.is_active(chat.id):
                await call.end(chat.id)
            return
        user_status_cache.pop(user_key, None)
    except errors.RPCError:
        return


async def handle_promotion_or_demotion(client: Client, chat, user, old_status, new_status):
    """Handles admin promotions and demotions."""
    is_promoted = new_status in {Cms.ADMINISTRATOR, Cms.OWNER} and old_status not in {Cms.ADMINISTRATOR, Cms.OWNER}
    is_demoted = old_status in {Cms.ADMINISTRATOR, Cms.OWNER} and new_status not in {Cms.ADMINISTRATOR, Cms.OWNER}

    if is_promoted or is_demoted:
        LOGGER.info(f"User {user.id} was {'promoted' if is_promoted else 'demoted'} in {chat.id}.")
        try:
            await load_admin_cache(client, chat.id, True)
        except Exception as e:
            LOGGER.warning(f"Error updating admin cache for {chat.id}: {e}")

    # Reload bot permissions if it was promoted
    if user.id == client.me.id and is_promoted:
        LOGGER.info(f"Bot was promoted in {chat.id}, reloading admin permissions.")
        try:
            await load_admin_cache(client, chat.id, True)
        except Exception as e:
            LOGGER.warning(f"Error reloading bot permissions in {chat.id}: {e}")
