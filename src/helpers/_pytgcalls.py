#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
import os
import random
import re
from pathlib import Path
from typing import Optional, Union

from ntgcalls import TelegramServerError
from pyrogram import Client as PyroClient
from pyrogram import errors
from pytdbot import Client, types
from pytgcalls import PyTgCalls, exceptions
from pytgcalls.types import (
    AudioQuality,
    ChatUpdate,
    MediaStream,
    Update,
    UpdatedGroupCallParticipant,
    VideoQuality,
    stream,
)

from src import config
from src.logger import LOGGER
from src.modules.utils import PlayButton, get_audio_duration, sec_to_min, send_logger
from src.modules.utils.thumbnails import gen_thumb
from ._api import ApiData
from ._cacher import chat_cache
from ._database import db
from ._dataclass import CachedTrack
from ._downloader import MusicServiceWrapper
from ._jiosaavn import JiosaavnData
from ._youtube import YouTubeData


class MusicBot:
    def __init__(self):
        self.calls: dict[str, PyTgCalls] = {}
        self.client_counter: int = 1
        self.available_clients: list[str] = []
        self.bot: Optional[Client] = None

    async def add_bot(self, client: Client) -> types.Ok:
        self.bot = client
        return types.Ok()

    async def _get_client_name(self, chat_id: int) -> Union[str, types.Error]:
        if not self.available_clients:
            return types.Error(code=400, message="No available clients to assign!")

        if chat_id == 1:
            return random.choice(self.available_clients)

        assistant = await db.get_assistant(chat_id)
        if assistant and assistant in self.available_clients:
            return assistant

        new_client = random.choice(self.available_clients)
        await db.set_assistant(chat_id, assistant=new_client)
        return new_client

    async def get_client(self, chat_id: int) -> Union[PyroClient, types.Error]:
        client_name = await self._get_client_name(chat_id)
        if isinstance(client_name, types.Error):
            return client_name

        ub = self.calls[client_name].mtproto_client
        if ub is None or not hasattr(ub, "me") or ub.me is None:
            return types.Error(code=400, message="Client not found or not ready")

        return ub

    async def start_client(
        self, api_id: int, api_hash: str, session_string: str
    ) -> None:
        client_name = f"client{self.client_counter}"
        try:
            user_bot = PyroClient(
                client_name,
                api_id=api_id,
                api_hash=api_hash,
                session_string=session_string,
            )
            calls = PyTgCalls(user_bot, cache_duration=100)
            self.calls[client_name] = calls
            self.available_clients.append(client_name)
            self.client_counter += 1

            await calls.start()
            LOGGER.info("Client %s started successfully", client_name)
        except Exception as e:
            LOGGER.error("Error starting client %s: %s", client_name, e)
            raise

    async def register_decorators(self) -> None:
        for call_instance in self.calls.values():

            @call_instance.on_update()
            async def general_handler(_, update: Update):
                try:
                    LOGGER.debug("Received update: %s", update)
                    if isinstance(update, stream.StreamEnded):
                        await self.play_next(update.chat_id)
                        return None
                    elif isinstance(update, UpdatedGroupCallParticipant):
                        return None
                    elif isinstance(update, ChatUpdate) and (
                        update.status.KICKED or update.status.LEFT_GROUP
                    ):
                        chat_cache.clear_chat(update.chat_id)
                        return None
                    return None
                except Exception as e:
                    LOGGER.error("Error in general handler: %s", e)
                    return None

    async def play_media(
        self,
        chat_id: int,
        file_path: Union[str, Path],
        video: bool = False,
        ffmpeg_parameters: Optional[str] = None,
    ) -> Union[types.Ok, types.Error]:
        LOGGER.info("Playing media for chat %s: %s", chat_id, file_path)
        client_name = await self._get_client_name(chat_id)
        if isinstance(client_name, types.Error):
            return client_name

        _stream = MediaStream(
            audio_path=file_path,
            media_path=file_path,
            audio_parameters=AudioQuality.HIGH if video else AudioQuality.STUDIO,
            video_parameters=(
                VideoQuality.FHD_1080p if video else VideoQuality.SD_360p
            ),
            video_flags=(
                MediaStream.Flags.AUTO_DETECT if video else MediaStream.Flags.IGNORE
            ),
            ffmpeg_parameters=ffmpeg_parameters,
        )

        try:
            await self.calls[client_name].play(chat_id, _stream)
            if await db.get_logger_status(self.bot.me.id):
                asyncio.create_task(
                    send_logger(self.bot, chat_id, chat_cache.get_current_song(chat_id))
                )
                return types.Ok()
            return types.Ok()
        except (errors.ChatAdminRequired, exceptions.NoActiveGroupCall) as e:
            LOGGER.warning("Error playing media for chat %s: %s", chat_id, e)
            chat_cache.clear_chat(chat_id)
            return types.Error(
                code=400,
                message="No active group call found\nPlease start a call first.",
            )
        except TelegramServerError:
            LOGGER.warning(
                "Error playing media for chat %s: TelegramServerError", chat_id
            )
            return types.Error(code=400, message="TelegramServerError")
        except Exception as e:
            LOGGER.error("Error playing media for chat %s: %s", chat_id, e)
            return types.Error(code=400, message=str(e))

    async def play_next(self, chat_id: int) -> None:
        LOGGER.info("Playing next song for chat %s", chat_id)
        try:
            loop = chat_cache.get_loop_count(chat_id)
            if loop > 0:
                chat_cache.set_loop_count(chat_id, loop - 1)
                if current_song := chat_cache.get_current_song(chat_id):
                    await self._play_song(chat_id, current_song)
                    return

            if next_song := chat_cache.get_next_song(chat_id):
                chat_cache.remove_current_song(chat_id)
                await self._play_song(chat_id, next_song)
            else:
                await self._handle_no_songs(chat_id)
        except Exception as e:
            LOGGER.error("Error in play_next for chat %s: %s", chat_id, e)

    async def _play_song(self, chat_id: int, song: CachedTrack) -> None:
        LOGGER.info("Playing song for chat %s", chat_id)
        try:
            reply = await self.bot.sendTextMessage(chat_id, "⏹️ Loading... Please wait.")
            if isinstance(reply, types.Error):
                LOGGER.error("Error sending message: %s", reply)
                return

            file_path = song.file_path or await self.song_download(song)
            if not file_path:
                await reply.edit_text(
                    "Failed to download the song.\nPlaying next song..."
                )
                await self.play_next(chat_id)
                return

            await self.play_media(chat_id, file_path, video=song.is_video)
            duration = song.duration or await get_audio_duration(file_path)
            text = (
                f"<b>Now playing <a href='{song.thumbnail or 'https://t.me/FallenProjects'}'>:</a></b>\n\n"
                f"‣ <b>Title:</b> {song.name}\n"
                f"‣ <b>Duration:</b> {sec_to_min(duration)}\n"
                f"‣ <b>Requested by:</b> {song.user}"
            )

            thumbnail = (
                await gen_thumb(song) if await db.get_thumb_status(chat_id) else ""
            )
            parse = await self.bot.parseTextEntities(text, types.TextParseModeHTML())
            if isinstance(parse, types.Error):
                LOGGER.error("Parse error: %s", parse)
                parse = parse.message

            if thumbnail:
                input_content = types.InputMessagePhoto(
                    photo=types.InputFileLocal(thumbnail), caption=parse
                )
                reply = await self.bot.editMessageMedia(
                    chat_id=chat_id,
                    message_id=reply.id,
                    input_message_content=input_content,
                    reply_markup=(
                        PlayButton if await db.get_buttons_status(chat_id) else None
                    ),
                )
            else:
                reply = await self.bot.editMessageText(
                    chat_id=chat_id,
                    message_id=reply.id,
                    input_message_content=types.InputMessageText(
                        text=parse,
                        link_preview_options=types.LinkPreviewOptions(is_disabled=True),
                    ),
                    reply_markup=(
                        PlayButton if await db.get_buttons_status(chat_id) else None
                    ),
                )
            if isinstance(reply, types.Error):
                LOGGER.warning("Error editing message: %s", reply)
                return
        except Exception as e:
            LOGGER.error("Error in _play_song for chat %s: %s", chat_id, e)
            return

    @staticmethod
    async def song_download(song: CachedTrack) -> Union[Path, None]:
        platform_handlers = {
            "youtube": YouTubeData(song.track_id),
            "jiosaavn": JiosaavnData(song.url),
            "spotify": ApiData(song.track_id),
            "apple_music": ApiData(song.url),
            "soundcloud": ApiData(song.url),
        }

        if handler := platform_handlers.get(song.platform.lower()):
            if track := await handler.get_track():
                return await handler.download_track(track, song.is_video)

        LOGGER.warning(
            "Unknown platform: %s for track: %s", song.platform, song.track_id
        )
        return None

    async def _handle_no_songs(self, chat_id: int) -> None:
        try:
            await self.end(chat_id)
            if recommendations := await MusicServiceWrapper().get_recommendations():
                buttons = [
                    [
                        types.InlineKeyboardButton(
                            f"{track.name[:18]} - {track.artist}",
                            type=types.InlineKeyboardButtonTypeCallback(
                                f"play_{track.platform}_{track.id}".encode()
                            ),
                        )
                    ]
                    for track in recommendations.tracks
                ]

                reply = await self.bot.sendTextMessage(
                    chat_id,
                    text="No more songs in queue. Here are some recommendations:\n\n",
                    reply_markup=types.ReplyMarkupInlineKeyboard(buttons),
                )

                if isinstance(reply, types.Error):
                    LOGGER.warning("Error sending recommendations: %s", reply)
                return

            reply = await self.bot.sendTextMessage(
                chat_id, text="No more songs in queue. Use /play to add some."
            )

            if isinstance(reply, types.Error):
                LOGGER.warning("Error sending empty queue message: %s", reply)

        except Exception as e:
            LOGGER.error("Error in _handle_no_songs for chat %s: %s", chat_id, e)

    async def end(self, chat_id: int) -> Union[types.Ok, types.Error]:
        LOGGER.info("Ending call for chat %s", chat_id)
        client_name = await self._get_client_name(chat_id)
        if isinstance(client_name, types.Error):
            return client_name

        try:
            chat_cache.clear_chat(chat_id)
            await self.calls[client_name].leave_call(chat_id)
            return types.Ok()
        except (exceptions.NotInCallError, errors.GroupCallInvalid):
            return types.Ok()
        except Exception as e:
            LOGGER.error("Error ending call for chat %s: %s", chat_id, e)
            return types.Error(code=400, message=str(e))

    async def seek_stream(
        self,
        chat_id: int,
        file_path_or_url: str,
        to_seek: int,
        duration: int,
        is_video: bool,
    ) -> Union[types.Ok, types.Error]:
        try:
            is_url = bool(re.match(r"http(s)?://", file_path_or_url))
            if is_url or not os.path.isfile(file_path_or_url):
                ffmpeg_params = f"-ss {to_seek} -i {file_path_or_url} -to {duration}"
            else:
                ffmpeg_params = f"-ss {to_seek} -to {duration}"
            await self.play_media(chat_id, file_path_or_url, is_video, ffmpeg_params)
            return types.Ok()
        except Exception as e:
            LOGGER.error("Error in seek_stream: %s", e)
            return types.Error(code=400, message=str(e))

    async def speed_change(
        self, chat_id: int, speed: float = 1.0
    ) -> Union[types.Ok, types.Error]:
        if not 0.5 <= speed <= 4.0:
            return types.Error(code=400, message="Speed must be between 0.5 and 4.0")

        curr_song = chat_cache.get_current_song(chat_id)
        if not curr_song or not curr_song.file_path:
            return types.Error(code=400, message="No song is currently playing")

        return await self.play_media(
            chat_id,
            curr_song.file_path,
            curr_song.is_video,
            ffmpeg_parameters=f"-atend -filter:v setpts=0.5*PTS -filter:a atempo={speed}",
        )

    async def change_volume(
        self, chat_id: int, volume: int
    ) -> Union[None, types.Error]:
        try:
            client_name = await self._get_client_name(chat_id)
            if isinstance(client_name, types.Error):
                return client_name

            if volume < 1 or volume > 200:
                return types.Error(code=400, message="Volume must be between 1 and 200")
            await self.calls[client_name].change_volume_call(chat_id, volume)
            return None
        except Exception as e:
            LOGGER.error("Error changing volume for chat %s: %s", chat_id, e)
            return types.Error(code=400, message=str(e))

    async def mute(self, chat_id: int) -> Union[types.Ok, types.Error]:
        try:
            client_name = await self._get_client_name(chat_id)
            if isinstance(client_name, types.Error):
                return client_name

            await self.calls[client_name].mute(chat_id)
            return types.Ok()
        except Exception as e:
            LOGGER.error("Error muting chat %s: %s", chat_id, e)
            return types.Error(code=400, message=str(e))

    async def unmute(self, chat_id: int) -> Union[types.Ok, types.Error]:
        LOGGER.info("Unmuting stream for chat %s", chat_id)
        try:
            client_name = await self._get_client_name(chat_id)
            if isinstance(client_name, types.Error):
                return client_name

            await self.calls[client_name].unmute(chat_id)
            return types.Ok()
        except Exception as e:
            LOGGER.error("Error unmuting chat %s: %s", chat_id, e)
            return types.Error(code=400, message=str(e))

    async def resume(self, chat_id: int) -> Union[types.Ok, types.Error]:
        LOGGER.info("Resuming stream for chat %s", chat_id)
        try:
            client_name = await self._get_client_name(chat_id)
            if isinstance(client_name, types.Error):
                return client_name

            await self.calls[client_name].resume(chat_id)
            return types.Ok()
        except Exception as e:
            LOGGER.error("Error resuming chat %s: %s", chat_id, e)
            return types.Error(code=400, message=str(e))

    async def pause(self, chat_id: int) -> Union[types.Ok, types.Error]:
        LOGGER.info("Pausing stream for chat %s", chat_id)
        try:
            client_name = await self._get_client_name(chat_id)
            if isinstance(client_name, types.Error):
                return client_name
            await self.calls[client_name].pause(chat_id)
            return types.Ok()
        except Exception as e:
            LOGGER.error("Error pausing chat %s: %s", chat_id, e)
            return types.Error(code=400, message=str(e))

    async def played_time(self, chat_id: int) -> Union[int, types.Error]:
        LOGGER.info("Getting played time for chat %s", chat_id)
        try:
            client_name = await self._get_client_name(chat_id)
            return await self.calls[client_name].time(chat_id)
        except exceptions.NotInCallError:
            chat_cache.clear_chat(chat_id)
            return 0
        except Exception as e:
            LOGGER.error("Error getting played time for chat %s: %s", chat_id, e)
            return types.Error(code=400, message=str(e))

    async def vc_users(self, chat_id: int) -> Union[list, types.Error]:
        LOGGER.info("Getting VC users for chat %s", chat_id)
        try:
            client_name = await self._get_client_name(chat_id)
            if isinstance(client_name, types.Error):
                return client_name
            return await self.calls[client_name].get_participants(chat_id)
        except exceptions.UnsupportedMethod:
            return types.Error(code=400, message="Method not supported")
        except Exception as e:
            LOGGER.error("Error getting participants for chat %s: %s", chat_id, e)
            return types.Error(code=400, message=str(e))

    async def stats_call(self, chat_id: int) -> Union[tuple[float, float], types.Error]:
        try:
            client_name = await self._get_client_name(chat_id)
            return (
                self.calls[client_name].ping,
                await self.calls[client_name].cpu_usage,
            )
        except Exception as e:
            LOGGER.error("Error getting stats for chat %s: %s", chat_id, e)
            return types.Error(code=400, message=str(e))


async def start_clients() -> None:
    try:
        await asyncio.gather(
            *[
                call.start_client(config.API_ID, config.API_HASH, s)
                for s in config.SESSION_STRINGS
            ]
        )
        LOGGER.info("✅ Clients started successfully.")
    except Exception as exc:
        LOGGER.error("Error starting clients: %s", exc)
        raise SystemExit(1) from exc


call: MusicBot = MusicBot()
