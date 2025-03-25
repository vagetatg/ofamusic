from datetime import datetime

from cachetools import TTLCache
from pyrogram import Client, filters, types

from src.database import db
from src.modules.utils import sec_to_min
from src.modules.utils.admins import load_admin_cache
from src.modules.utils.buttons import AddMeButton
from src.modules.utils.play_helpers import (
    check_user_status,
    chat_invite_cache,
    user_status_cache,
)
from src.pytgcalls import call


@Client.on_message(filters.command("start"))
async def start_cmd(c: Client, message: types.Message):
    chat_id = message.chat.id
    if chat_id < 0:
        await db.add_chat(chat_id)
    else:
        await db.add_user(chat_id)

    text = f"""
    нєу {message.from_user.mention} 👋

<b>Welcome to {c.me.first_name} </b>

Your ultimate music companion for Telegram voice chats! 

<b>Supported Platforms:</b> Spotify, YouTube and Telegram Audio.

<b>📢 Note:</b> This bot works best in groups and requires admin permissions to function.
    """

    await message.reply_text(text, reply_markup=AddMeButton)
    return None


@Client.on_message(filters.command("help"))
async def help_cmd(c: Client, message: types.Message):
    text = f"""<b>Help for {c.me.first_name}:</b>
<b>/start:</b> Start the bot.
<b>/reload:</b> Reload chat administrator list.
<b>/speed:</b> Change the playback speed of the current song. (0.5 - 4.0)
<b>/play:</b> Reply to an audio or provide a song name to play music.  
<b>/skip:</b> Skip the current song.  
<b>/remove x:</b> Remove x song from the queue.
<b>/pause:</b> Pause the current song.  
<b>/resume:</b> Resume the current song.  
<b>/end:</b> End the current song.  
<b>/seek:</b> Seek to a specific time in the current song.
<b>/mute:</b> Mute the current song.  
<b>/unmute:</b> Unmute the current song. 
<b>/volume:</b> Change the volume of the current song.
<b>/loop:</b> Loop the current song. use /loop 0 to disable.
<b>/queue:</b> Get the queue of the current chat.
<b>/clear:</b> Clear the queue of the current chat.
<b>/song:</b> Download a song from YouTube, Spotify.
<b>/setPlayType:</b> Change the play type of the bot.
<b>/privacy:</b> Read our privacy policy.

──────────────────────────────────────────
<b>Note:</b> This bot works best in groups and requires admin permissions to function.
"""

    await message.reply_text(text=text)


@Client.on_message(filters.command("privacy"))
async def privacy_handler(c: Client, message: types.Message):
    bot_name = c.me.first_name
    text = f"""
    <u><b>Privacy Policy for {bot_name}:</b></u>

<b>1. Data Storage:</b>
- {bot_name} does not store any personal data on the user's device.
- We do not collect or store any data about your device or personal browsing activity.

<b>2. What We Collect:</b>
- We only collect your Telegram <b>user ID</b> and <b>chat ID</b> to provide the music streaming and interaction functionalities of the bot.
- No personal data such as your name, phone number, or location is collected.

<b>3. Data Usage:</b>
- The collected data (Telegram UserID, ChatID) is used strictly to provide the music streaming and interaction functionalities of the bot.
- We do not use this data for any marketing or commercial purposes.

<b>4. Data Sharing:</b>
- We do not share any of your personal or chat data with any third parties, organizations, or individuals.
- No sensitive data is sold, rented, or traded to any outside entities.

<b>5. Data Security:</b>
- We take reasonable security measures to protect the data we collect. This includes standard practices like encryption and safe storage.
- However, we cannot guarantee the absolute security of your data, as no online service is 100% secure.

<b>6. Cookies and Tracking:</b>
- {bot_name} does not use cookies or similar tracking technologies to collect personal information or track your behavior.

<b>7. Third-Party Services:</b>
- {bot_name} does not integrate with any third-party services that collect or process your personal information, aside from Telegram's own infrastructure.

<b>8. Your Rights:</b>
- You have the right to request the deletion of your data. Since we only store your Telegram ID and chat ID temporarily to function properly, these can be removed upon request.
- You may also revoke access to the bot at any time by removing or blocking it from your chats.

<b>9. Changes to the Privacy Policy:</b>
- We may update this privacy policy from time to time. Any changes will be communicated through updates within the bot.

<b>10. Contact Us:</b>
If you have any questions or concerns about our privacy policy, feel free to contact us at <a href="https://t.me/GuardxSupport">Support Group</a>

──────────────────
<b>Note:</b> This privacy policy is in place to help you understand how your data is handled and to ensure that your experience with {bot_name} is safe and respectful.
    """

    reply = await message.reply_text(text)
    if isinstance(reply, types.Error):
        c.logger.warning(f"Error sending privacy policy message: {reply.message}")
    return


rate_limit_cache = TTLCache(maxsize=100, ttl=180)


@Client.on_message(filters.command("reload"))
async def reload_cmd(c: Client, message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if chat_id > 0:
        return

    if user_id in rate_limit_cache:
        last_used_time = rate_limit_cache[user_id]
        time_remaining = 180 - (datetime.now() - last_used_time).total_seconds()
        await message.reply_text(
            f"🚫 You can use this command again in ({sec_to_min(time_remaining)} Min."
        )
        return

    rate_limit_cache[user_id] = datetime.now()
    reply = await message.reply_text("🔄 Reloading...")
    ub = await call.get_client(chat_id)
    chat_invite_cache.pop(chat_id, None)
    user_key = f"{chat_id}:{ub.me.id}"
    user_status_cache.pop(user_key, None)
    load_admins, _ = await load_admin_cache(c, chat_id, True)

    ub_stats = await check_user_status(c, chat_id, ub.me.id)
    loaded = "✅" if load_admins else "❌"
    text = (
        f"<b>Assistant Status:</b> {ub_stats}\n"
        f"<b>Admins Loaded:</b> {loaded}\n"
        f"<b>» Reloaded by:</b> {message.from_user.mention}"
    )

    await reply.edit_text(
        text,
    )
    return


@Client.on_message(filters.command("song"))
async def song_cmd(c: Client, message: types.Message):
    await message.reply_text("🎶 USE: @SpTubeBot")
    return
