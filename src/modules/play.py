#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import re
from types import NoneType

from pytdbot import Client, types

from src.database import db
from src.logger import LOGGER
from src.modules.utils import (
    Filter, SupportButton, get_audio_duration, sec_to_min
)
from src.modules.utils.admins import load_admin_cache, is_admin
from src.modules.utils.buttons import PlayButton
from src.modules.utils.cacher import chat_cache
from src.modules.utils.play_helpers import (
    get_url, edit_text, user_status_cache, unban_ub, join_ub,
    extract_argument, check_user_status, del_msg
)
from src.modules.utils.thumbnails import gen_thumb
from src.platforms.dataclass import CachedTrack, MusicTrack, PlatformTracks
from src.platforms.downloader import MusicServiceWrapper
from src.platforms.telegram import Telegram
from src.pytgcalls import call, CallError


def _get_jiosaavn_url(track_id: str) -> str:
    """Generate JioSaavn URL from track ID."""
    try:
        title, song_id = track_id.rsplit("/", 1)
    except ValueError:
        return ""
    title = re.sub(r'[\(\)"\',]', "", title.lower()).replace(" ", "-")
    return f"https://www.jiosaavn.com/song/{title}/{song_id}"


def _get_platform_url(platform: str, track_id: str) -> str:
    """Generate platform URL from track ID."""
    platform = platform.lower()
    if not track_id:
        return ""
    url_map = {
            "youtube": f"https://youtube.com/watch?v={track_id}",
            "spotify": f"https://open.spotify.com/track/{track_id}",
            "jiosaavn": _get_jiosaavn_url(track_id)
    }
    return url_map.get(platform, "")


async def _update_msg_with_thumb(c: Client, msg: types.Message, text: str, thumb: str,
                                 button: types.ReplyMarkupInlineKeyboard):
    """Update message with thumbnail if available."""
    if not thumb:
        return await edit_text(msg, text=text, reply_markup=button)

    parsed_text = await c.parseTextEntities(text, types.TextParseModeHTML())
    if isinstance(parsed_text, types.Error):
        return await edit_text(msg, text=str(parsed_text), reply_markup=button)

    input_content = types.InputMessagePhoto(
            photo=types.InputFileRemote(thumb) if thumb.startswith("http")
            else types.InputFileLocal(thumb),
            caption=parsed_text,
    )

    reply = await c.editMessageMedia(
            chat_id=msg.chat_id,
            message_id=msg.id,
            input_message_content=input_content,
            reply_markup=button,
    )

    return await edit_text(
                       msg, text=str(reply), reply_markup=button
               ) if isinstance(reply, types.Error) else reply


async def _handle_single_track(c: Client, msg: types.Message, chat_id: int,
                               track: MusicTrack, user_by: str, file_path: str = None,
                               is_video: bool = False):
    """Handle playback of a single track."""
    song = CachedTrack(
            name=track.name,
            artist=track.artist,
            track_id=track.id,
            loop=0,
            duration=track.duration,
            file_path=file_path or "",
            thumbnail=track.cover,
            user=user_by,
            platform=track.platform,
            url=track.url,
    )

    if not song.file_path:
        if file_path := await call.song_download(song):
            song.file_path = file_path
        else:
            return await edit_text(msg, "❌ Error downloading the song.")

    song.duration = song.duration or await get_audio_duration(song.file_path)
    if chat_cache.is_active(chat_id):
        queue = chat_cache.get_queue(chat_id)
        chat_cache.add_song(chat_id, song)
        text = (
                f"<b>➻ Added to Queue at #{len(queue)}:</b>\n\n"
                f"‣ <b>Title:</b> {song.name}\n"
                f"‣ <b>Duration:</b> {sec_to_min(song.duration)}\n"
                f"‣ <b>Requested by:</b> {song.user}"
        )
        thumb = await gen_thumb(song)
        await _update_msg_with_thumb(c, msg, text, thumb, PlayButton)
        return None

    chat_cache.set_active(chat_id, True)
    chat_cache.add_song(chat_id, song)

    try:
        await call.play_media(chat_id, song.file_path, video=is_video)
    except CallError as e:
        return await edit_text(msg, text=f"⚠️ {e}")

    thumb = await gen_thumb(song)
    text = (
            f"🎵 <b>Now playing:</b>\n\n"
            f"‣ <b>Title:</b> {song.name}\n"
            f"‣ <b>Duration:</b> {sec_to_min(song.duration)}\n"
            f"‣ <b>Requested by:</b> {song.user}"
    )

    reply = await _update_msg_with_thumb(c, msg, text, thumb, PlayButton)
    if isinstance(reply, types.Error):
        LOGGER.info(f"sending reply: {reply}")
        return None


async def _handle_multiple_tracks(_: Client, msg: types.Message, chat_id: int,
                                  tracks: list[MusicTrack], user_by: str):
    """Handle multiple tracks (playlist/album)."""
    is_active = chat_cache.is_active(chat_id)
    queue = chat_cache.get_queue(chat_id)
    text = "<b>➻ Added to Queue:</b>\n<blockquote expandable>\n"
    for index, track in enumerate(tracks):
        position = len(queue) + index
        chat_cache.add_song(
                chat_id,
                CachedTrack(
                        name=track.name,
                        artist=track.artist,
                        track_id=track.id,
                        loop=1 if not is_active and index == 0 else 0,
                        duration=track.duration,
                        thumbnail=track.cover,
                        user=user_by,
                        file_path="",
                        platform=track.platform,
                        url=track.url,
                ),
        )
        text += f"<b>{position}.</b> {track.name}\n└ Duration: {sec_to_min(track.duration)}\n"

    text += "</blockquote>\n"
    total_dur = sum(t.duration for t in tracks)
    text += (
            f"<b>📋 Total Queue:</b> {len(chat_cache.get_queue(chat_id))}\n"
            f"<b>⏱️ Total Duration:</b> {sec_to_min(total_dur)}\n"
            f"<b>👤 Requested by:</b> {user_by}"
    )

    if len(text) > 4096:
        text = (
                f"<b>📋 Total Queue:</b> {len(chat_cache.get_queue(chat_id))}\n"
                f"<b>⏱️ Total Duration:</b> {sec_to_min(total_dur)}\n"
                f"<b>👤 Requested by:</b> {user_by}"
        )

    if not is_active:
        await call.play_next(chat_id)

    await edit_text(msg, text, reply_markup=PlayButton)


async def play_music(c: Client, msg: types.Message, url_data: PlatformTracks,
                     user_by: str, tg_file_path: str = None, is_video: bool = False):
    """Handle playing music from given URL or file."""
    if not url_data or not url_data.tracks:
        return await edit_text(msg, "❌ Unable to retrieve song info.")

    chat_id = msg.chat_id
    await edit_text(msg, text="🎶 Song found. Downloading...")
    if len(url_data.tracks) == 1:
        return await _handle_single_track(
                c, msg, chat_id, url_data.tracks[0], user_by, tg_file_path, is_video
        )

    return await _handle_multiple_tracks(c, msg, chat_id, url_data.tracks, user_by)


async def _handle_recommendations(_: Client, msg: types.Message, wrapper: MusicServiceWrapper):
    """Show music recommendations when no query is provided."""
    recommendations = await wrapper.get_recommendations()
    text = "ᴜsᴀɢᴇ: /play song_name\nSupports Spotify track, playlist, album, artist links.\n\n"

    if not recommendations:
        await edit_text(msg, text=text, reply_markup=SupportButton)
        return

    platform = recommendations.tracks[0].platform
    text += "Tap on a song name to play it."
    buttons = [
            [types.InlineKeyboardButton(
                    f"{track.name[:18]} - {track.artist}",
                    type=types.InlineKeyboardButtonTypeCallback(
                            f"play_{platform}_{track.id}".encode()
                    )
            )] for track in recommendations.tracks
    ]

    await edit_text(
            msg, text=text, reply_markup=types.ReplyMarkupInlineKeyboard(buttons)
    )


async def _handle_telegram_file(c: Client, _: types.Message, reply: types.Message,
                                reply_message: types.Message, user_by: str):
    """Handle Telegram audio/video files."""
    telegram = Telegram(reply)
    docs_vid = (isinstance(reply.content, types.Document) and
                reply.content.mime_type.startswith("video/"))
    is_video = isinstance(reply.content, types.MessageVideo) or docs_vid

    file_path, file_name = await telegram.dl()
    if isinstance(file_path, types.Error):
        return await edit_text(reply_message, text=f"❌ {str(file_path)}")

    _song = PlatformTracks(tracks=[MusicTrack(
            name=file_name,
            artist="AshokShau",
            id=reply.remote_unique_file_id,
            year=0,
            cover="",
            duration=await get_audio_duration(file_path.path),
            url="",
            platform="telegram",
    )])

    await play_music(c, reply_message, _song, user_by, file_path.path, is_video)


async def _handle_text_search(c: Client, msg: types.Message, chat_id: int,
                              wrapper: MusicServiceWrapper, user_by: str):
    """Handle text-based music search."""
    play_type = await db.get_play_type(chat_id)
    search = await wrapper.search()

    if not search or not search.tracks:
        return await edit_text(
                msg,
                text="❌ No results found. Please report if you think it's a bug.",
                reply_markup=SupportButton,
        )

    if play_type == 0:
        url = search.tracks[0].url
        if song := await MusicServiceWrapper(url).get_info():
            return await play_music(c, msg, song, user_by)

        return await edit_text(
                msg, text="❌ Unable to retrieve song info.", reply_markup=SupportButton
        )

    buttons = [
            [types.InlineKeyboardButton(
                    f"{rec.name[:18]} - {rec.artist}",
                    type=types.InlineKeyboardButtonTypeCallback(
                            f"play_{rec.platform.lower()}_{rec.id}".encode()
                    )
            )] for rec in search.tracks[:4]
    ]

    await edit_text(
            msg,
            text=f"{user_by}, select a song to play:",
            reply_markup=types.ReplyMarkupInlineKeyboard(buttons),
            disable_web_page_preview=True,
    )


@Client.on_message(filters=Filter.command("play"))
async def play_audio(c: Client, msg: types.Message) -> None:
    """Handle /play command."""
    chat_id = msg.chat_id
    if chat_id > 0:
        await msg.reply_text("This command is only available in supergroups.")
        return

    await load_admin_cache(c, chat_id)
    if not await is_admin(chat_id, c.options["my_id"] or c.me.id):
        await msg.reply_text(
                "I need admin with invite user permission if group is private.\n\n"
                "After promoting me, try again or use /reload."
        )
        return

    reply = await msg.getRepliedMessage() if msg.reply_to_message_id else None
    url = await get_url(msg, reply)
    args = extract_argument(msg.text)

    reply_message = await msg.reply_text("🔎 Searching...")
    if isinstance(reply_message, types.Error):
        LOGGER.warning(f"Error sending reply: {reply_message}")
        return

    # Handle assistant bot checks
    ub = await call.get_client(chat_id)
    if isinstance(ub, (types.Error, NoneType)):
        await edit_text(reply_message, "❌ Assistant not found for this chat.")
        return

    # Check queue limit
    queue = chat_cache.get_queue(chat_id)
    if len(queue) > 10:
        await edit_text(
                reply_message,
                text=f"❌ Queue full! You have {len(queue)} tracks. Use /end to reset.",
        )
        return

    # Check user status
    user_key = f"{chat_id}:{ub.me.id}"
    user_status = user_status_cache.get(user_key) or await check_user_status(
            c, chat_id, ub.me.id
    )

    if isinstance(user_status, types.Error):
        await edit_text(reply_message, text=f"❌ {str(user_status)}")
        return

    if user_status in {"chatMemberStatusBanned", "chatMemberStatusLeft", "chatMemberStatusRestricted"}:
        if user_status == "chatMemberStatusBanned":
            await unban_ub(c, chat_id, ub.me.id)

        join = await join_ub(chat_id, c, ub)
        if isinstance(join, types.Error):
            await edit_text(reply_message, text=f"❌ {str(join)}")
            return

    await del_msg(msg)
    wrapper = MusicServiceWrapper(url or args)

    # Handle different play scenarios
    if not args and not url and not (reply and Telegram(reply).is_valid()):
        return await _handle_recommendations(c, reply_message, wrapper)

    user_by = await msg.mention()
    if reply and Telegram(reply).is_valid():
        return await _handle_telegram_file(c, msg, reply, reply_message, user_by)

    if url:
        if not wrapper.is_valid(url):
            await edit_text(reply_message, text="❌ Invalid URL! Provide a valid link.", reply_markup=SupportButton)
            return

        if song := await wrapper.get_info():
            return await play_music(c, reply_message, song, user_by)

        await edit_text(reply_message, text="❌ Unable to retrieve song info.", reply_markup=SupportButton)
        return

    return await _handle_text_search(c, reply_message, chat_id, wrapper, user_by)
