#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import re

from pytdbot import Client, types

from TgMusic import db, call, tg
from TgMusic.core import YouTubeData, DownloaderWrapper
from TgMusic.core import (
    CachedTrack,
    MusicTrack,
    PlatformTracks,
    chat_cache,
)
from TgMusic.logger import LOGGER
from TgMusic.core import (
    Filter,
    SupportButton,
    control_buttons,
)
from TgMusic.core.admins import is_admin, load_admin_cache
from TgMusic.modules.utils import sec_to_min, get_audio_duration
from TgMusic.modules.utils.play_helpers import (
    del_msg,
    edit_text,
    extract_argument,
    get_url,
)
from TgMusic.core.thumbnails import gen_thumb


def _get_jiosaavn_url(track_id: str) -> str:
    """
    Generate JioSaavn URL from track ID.
    """
    try:
        title, song_id = track_id.rsplit("/", 1)
    except ValueError:
        return ""
    title = re.sub(r'[\(\)"\',]', "", title.lower()).replace(" ", "-")
    return f"https://www.jiosaavn.com/song/{title}/{song_id}"


def _get_platform_url(platform: str, track_id: str) -> str:
    """
    Generate platform URL from track ID.
    """
    platform = platform.lower()
    if not track_id:
        return ""
    url_map = {
        "youtube": f"https://youtube.com/watch?v={track_id}",
        "spotify": f"https://open.spotify.com/track/{track_id}",
        "jiosaavn": _get_jiosaavn_url(track_id),
    }
    return url_map.get(platform, "")


def build_song_selection_message(user_by: str, tracks: list[MusicTrack]) -> tuple[str, types.ReplyMarkupInlineKeyboard]:
    """
    Build a message and inline keyboard for song selection.
    """
    text = f"{user_by}, select a song to play:" if user_by else "Select a song to play:"
    buttons = [
        [
            types.InlineKeyboardButton(
                f"{rec.name[:18]} - {rec.artist}",
                type=types.InlineKeyboardButtonTypeCallback(
                    f"play_{rec.platform.lower()}_{rec.id}".encode()
                ),
            )
        ]
        for rec in tracks[:4]
    ]
    return text, types.ReplyMarkupInlineKeyboard(buttons)


async def _update_msg_with_thumb(
    c: Client,
    msg: types.Message,
    text: str,
    thumb: str,
    button: types.ReplyMarkupInlineKeyboard,
):
    """
    Update a message with thumbnail if available.
    """
    if not thumb:
        return await edit_text(
            msg, text=text, reply_markup=button, disable_web_page_preview=True
        )

    parsed_text = await c.parseTextEntities(text, types.TextParseModeHTML())
    if isinstance(parsed_text, types.Error):
        return await edit_text(msg, text=parsed_text.message, reply_markup=button)

    input_content = types.InputMessagePhoto(
        types.InputFileLocal(thumb), caption=parsed_text
    )
    reply = await c.editMessageMedia(
        chat_id=msg.chat_id,
        message_id=msg.id,
        input_message_content=input_content,
        reply_markup=button,
    )

    return (
        await edit_text(msg, text=str(reply), reply_markup=button)
        if isinstance(reply, types.Error)
        else reply
    )


async def _handle_single_track(
    c: Client,
    msg: types.Message,
    track: MusicTrack,
    user_by: str,
    file_path: str = None,
    is_video: bool = False,
):
    """
    Handle playback of a single track.
    """
    chat_id = msg.chat_id
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
        is_video=is_video,
        url=track.url,
    )

    if not song.file_path:
        file_path = await call.song_download(song)
        if isinstance(file_path, types.Error):
            return await edit_text(msg, f"❌ {file_path.message}")

        song.file_path = file_path
        if not file_path:
            return await edit_text(msg, f"❌ Error downloading the song.")

    song.duration = song.duration or await get_audio_duration(song.file_path)
    if chat_cache.is_active(chat_id):
        queue = chat_cache.get_queue(chat_id)
        chat_cache.add_song(chat_id, song)
        text = (
            f"<b>➻ Added to Queue at #{len(queue)}:</b>\n\n"
            f"‣ <b>Title:</b> <a href='{song.url}'>{song.name}</a>\n"
            f"‣ <b>Duration:</b> {sec_to_min(song.duration)}\n"
            f"‣ <b>Requested by:</b> {song.user}"
        )
        thumb = ""  # await gen_thumb(song) if await db.get_thumb_status(chat_id) else ""
        await _update_msg_with_thumb(c, msg, text, thumb, control_buttons("play") if await db.get_buttons_status(chat_id) else None)
        return None

    chat_cache.set_active(chat_id, True)
    chat_cache.add_song(chat_id, song)

    _call = await call.play_media(chat_id, song.file_path, video=is_video)
    if isinstance(_call, types.Error):
        return await edit_text(msg, text=f"⚠️ {_call.message}")

    thumb = await gen_thumb(song) if await db.get_thumb_status(chat_id) else ""
    text = (
        f"🎵 <b>Now playing:</b>\n\n"
        f"‣ <b>Title:</b> <a href='{song.url}'>{song.name}</a>\n"
        f"‣ <b>Duration:</b> {sec_to_min(song.duration)}\n"
        f"‣ <b>Requested by:</b> {song.user}"
    )

    reply = await _update_msg_with_thumb(c, msg, text, thumb, control_buttons("play") if await db.get_buttons_status(chat_id) else None)
    if isinstance(reply, types.Error):
        LOGGER.info("sending reply: %s", reply)
        return None
    return None


async def _handle_multiple_tracks(msg: types.Message, tracks: list[MusicTrack], user_by: str):
    """
    Handle multiple tracks (playlist/album).
    """
    chat_id = msg.chat_id
    is_active = chat_cache.is_active(chat_id)
    queue = chat_cache.get_queue(chat_id)
    text = (
        "<b>➻ "
        + "Added to Queue at"
        + ":</b>\n<blockquote expandable>\n"
    )

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
                is_video=False,
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

    await edit_text(msg, text, reply_markup=control_buttons("play"))


async def play_music(
    c: Client,
    msg: types.Message,
    url_data: PlatformTracks,
    user_by: str,
    tg_file_path: str = None,
    is_video: bool = False,
):
    """
    Handle playing music from a given URL or file.
    """
    if not url_data or not url_data.tracks:
        return await edit_text(msg, "Unable to retrieve song info.")

    await edit_text(msg, text="🎶 Song found. Downloading...")
    if len(url_data.tracks) == 1:
        return await _handle_single_track(c, msg, url_data.tracks[0], user_by, tg_file_path, is_video)
    return await _handle_multiple_tracks(msg, url_data.tracks, user_by)

async def _handle_telegram_file(c: Client, reply: types.Message, reply_message: types.Message, user_by: str):
    """
    Handle Telegram audio/video files.
    """
    # Determine if the message contains a video (Document or Video type)
    content = reply.content
    docs_vid = (
        isinstance(content, types.Document) and content.mime_type.startswith("video/")
    ) or (
        isinstance(content, types.MessageDocument)
        and content.document.mime_type.startswith("video/")
    )
    is_video = isinstance(content, types.MessageVideo) or docs_vid

    # Download the file
    file_path, file_name = await tg.download_msg(reply, reply_message)
    if isinstance(file_path, types.Error):
        return await edit_text(
            reply_message,
            text="<b>Download Failed</b>\n\n🎶 <b>File:</b> <code>{file}</code>\n💬 <b>Error:</b> <code>{error}</code>".format(file=file_name, error=file_path.message))

    duration = await get_audio_duration(file_path.path)
    _song = PlatformTracks(
        tracks=[
            MusicTrack(
                name=file_name,
                artist="AshokShau",
                id=reply.remote_unique_file_id,
                year=0,
                cover="",
                duration=duration,
                url="",
                platform="telegram",
            )
        ]
    )

    await play_music(c, reply_message, _song, user_by, file_path.path, is_video)
    return None


async def _handle_text_search(
    c: Client,
    msg: types.Message,
    wrapper: DownloaderWrapper,
    user_by: str,
):
    """
    Handle text-based music search.
    """
    chat_id = msg.chat_id
    play_type = await db.get_play_type(chat_id)
    search = await wrapper.search()
    if isinstance(search, types.Error):
        return await edit_text(msg, text=search.message, reply_markup=SupportButton)

    if not search or not search.tracks:
        return await edit_text(
            msg,
            text="No results found. Please report if you think it's a bug.",
            reply_markup=SupportButton,
        )

    if play_type == 0:
        url = search.tracks[0].url
        song = await DownloaderWrapper(url).get_info()
        if isinstance(song, types.Error):
            return await edit_text(
                msg,
                text=song.message,
                reply_markup=SupportButton,
            )
        return await play_music(c, msg, song, user_by)

    text, keyboard = build_song_selection_message(user_by, search.tracks)
    await edit_text(
        msg, text=text, reply_markup=keyboard, disable_web_page_preview=True
    )
    return None


async def handle_play_command(c: Client, msg: types.Message, is_video: bool = False):
    """
    Generic handler for /play and /vplay.
    """
    chat_id = msg.chat_id
    if chat_id > 0:
        return await msg.reply_text("This command is only available in supergroups.")

    # Queue limit
    queue = chat_cache.get_queue(chat_id)
    if len(queue) > 10:
        return await msg.reply_text("❌ Queue limit reached! You have {count} tracks. Use /end to reset.".format(count=len(queue)))

    await load_admin_cache(c, chat_id)
    if not await is_admin(chat_id, c.me.id):
        text = "I need admin with invite user permission if group is private.\n\nAfter promoting me, try again or use /reload."
        return await msg.reply_text(text)

    reply = await msg.getRepliedMessage() if msg.reply_to_message_id else None
    url = await get_url(msg, reply)
    args = extract_argument(msg.text)

    reply_message = await msg.reply_text("🔎")
    if isinstance(reply_message, types.Error):
        LOGGER.warning("Error sending reply: %s", reply_message)
        return None

    await del_msg(msg)
    wrapper = (YouTubeData if is_video else DownloaderWrapper)(url or args)
    # No args or reply
    if not args and not url and not (reply and tg.is_valid(reply)):
        if is_video:
            return await edit_text(reply_message, text="Usage: /play song_name or YouTube link", reply_markup=SupportButton)
        else:
            text = "ᴜsᴀɢᴇ: /play song_name\n\nSupported platforms are: YouTube, SoundCloud, Spotify, Apple Music & Jiosaavn."
            return await edit_text(reply_message, text=text, reply_markup=SupportButton)


    user_by = await msg.mention()
    # Telegram file support
    if reply and tg.is_valid(reply):
        return await _handle_telegram_file(c, reply, reply_message, user_by)

    if url:
        if not wrapper.is_valid(url):
            return await edit_text(
                reply_message,
                text="Invalid URL! Provide a valid link.\nSupported platforms are: YouTube, SoundCloud, Spotify, Apple Music & Jiosaavn.",
                reply_markup=SupportButton,
            )

        song = await wrapper.get_info()
        if isinstance(song, types.Error):
            return await edit_text(
                reply_message,
                "Unable to retrieve song info." + "\n\n" + song.message,
                reply_markup=SupportButton,
            )

        return await play_music(c, reply_message, song, user_by, is_video=is_video)

    # Search
    if is_video:
        search = await wrapper.search()
        if isinstance(search, types.Error):
            return await edit_text(
                reply_message,
                text=search.message,
                reply_markup=SupportButton,
            )

        if not search or not search.tracks:
            return await edit_text(
                reply_message,
                text="No results found.",
                reply_markup=SupportButton,
            )

        if song := await DownloaderWrapper(search.tracks[0].url).get_info():
            if isinstance(song, types.Error):
                return await edit_text(
                    reply_message,
                    text=song.message,
                    reply_markup=SupportButton,
                )

            return await play_music(
                c, reply_message, song, user_by, is_video=True
            )

        return await edit_text(
            reply_message,
            text="Unable to retrieve song info.",
            reply_markup=SupportButton,
        )
    else:
        return await _handle_text_search(c, reply_message, wrapper, user_by)


@Client.on_message(filters=Filter.command("play"))
async def play_audio(c: Client, msg: types.Message) -> None:
    await handle_play_command(c, msg, False)


@Client.on_message(filters=Filter.command("vplay"))
async def play_video(c: Client, msg: types.Message) -> None:
    await handle_play_command(c, msg, True)
