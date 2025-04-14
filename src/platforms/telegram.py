#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
import time
from typing import Optional, Tuple, Union

from pytdbot import types
from pytdbot.types import Error, LocalFile

from src.logger import LOGGER


class Telegram:
    """Helper class to validate and process playable Telegram media messages."""

    MAX_FILE_SIZE = 400 * 1024 * 1024  # 400MB
    UNSUPPORTED_TYPES = (
        types.MessageText,
        types.MessagePhoto,
        types.MessageSticker,
        types.MessageAnimation,
    )

    def __init__(self, reply: Optional[types.Message]):
        self.msg = reply
        self.content = reply.content if reply else None
        self._download_start_time = 0
        self._last_update_time = 0
        self._last_bytes_received = 0

    def is_valid(self) -> bool:
        """Check if the message contains a supported media type within size limits."""
        if not self.msg or isinstance(self.msg, types.Error):
            return False

        if isinstance(self.content, self.UNSUPPORTED_TYPES):
            return False

        file_size, _ = self._extract_file_info()
        if file_size == 0 or file_size > self.MAX_FILE_SIZE:
            LOGGER.info("Invalid file size: %s", file_size)
            return False

        return True

    def _extract_file_info(self) -> Tuple[int, str]:
        """Extract file size and filename from supported media types."""
        try:
            if isinstance(self.content, types.MessageVideo):
                return (
                    self.content.video.video.size,
                    self.content.video.file_name or "Video.mp4",
                )

            elif isinstance(self.content, types.MessageAudio):
                return (
                    self.content.audio.audio.size,
                    self.content.audio.file_name or "Audio.mp3",
                )

            elif isinstance(self.content, types.MessageVoiceNote):
                return self.content.voice_note.voice.size, "VoiceNote.ogg"

            elif isinstance(self.content, types.MessageVideoNote):
                return self.content.video_note.video.size, "VideoNote.mp4"

            elif isinstance(self.content, types.MessageDocument):
                mime = (self.content.document.mime_type or "").lower()
                if (mime and mime.startswith("audio/")) or (
                        mime and mime.startswith("video/")
                ):
                    return (
                        self.content.document.document.size,
                        self.content.document.file_name or "Document.mp4",
                    )
                # TODO: remove this , this is just for test
                else:
                    return (
                        self.content.document.document.size,
                        self.content.document.file_name or "Document.IDK",
                    )
        except Exception as e:
            LOGGER.error("Error while extracting file info: %s", e)

        LOGGER.info(
            "Unknown or unsupported content type: %s", type(self.content).__name__
        )
        return 0, "UnknownMedia"

    async def dl(self) -> Union[Tuple[Error, str], Tuple[LocalFile, str]]:
        """Asynchronously download the media file with progress, speed and ETA."""
        if not self.is_valid():
            return (
                types.Error(message="Invalid or unsupported media file."),
                "InvalidMedia",
            )

        total_size, file_name = self._extract_file_info()
        file_id = self.msg.remote_unique_file_id
        button = types.ReplyMarkupInlineKeyboard(
            [
                [
                    types.InlineKeyboardButton(
                        text="Stop Download",
                        type=types.InlineKeyboardButtonTypeCallback(f"cancel_{file_id}".encode())
                    ),
                ],
            ]
        )

        msg = await self.msg._client.sendTextMessage(
            self.msg.chat_id,
            f"📥 <b>Downloading:</b> <code>{file_name}</code>\n"
            f"💾 <b>Size:</b> {self._format_bytes(total_size)}\n"
            "📊 <b>Progress:</b> 0% ▱▱▱▱▱▱▱▱▱▱\n"
            "🚀 <b>Speed:</b> 0B/s\n"
            "⏳ <b>ETA:</b> Calculating...",
            reply_markup=button,
        )

        if isinstance(msg, types.Error):
            LOGGER.error("Error sending download message: %s", msg)
            return msg, "ErrorSendingMessage"

        # Initialize tracking variables
        self._download_start_time = time.time()
        self._last_update_time = self._download_start_time
        self._last_bytes_received = 0
        last_reported = 0
        update_threshold = max(total_size // 5, 10 * 1024 * 1024)  # Update every 20% or 10MB
        progress_updates = 0
        max_updates = 6

        try:
            while True:
                local_file = await self.msg.download()
                if local_file.is_downloading_completed:
                    break

                current_size = local_file.downloaded_prefix_size
                current_time = time.time()
                progress = (current_size / max(total_size, 1)) * 100

                # Calculate speed and ETA
                time_diff = current_time - self._last_update_time
                bytes_diff = current_size - self._last_bytes_received

                if time_diff > 0 and bytes_diff > 0:
                    speed = bytes_diff / time_diff  # Bytes per second
                    remaining_bytes = total_size - current_size
                    eta = remaining_bytes / speed if speed > 0 else 0

                    # Update only if significant progress or last update
                    if (current_size - last_reported) >= update_threshold or progress >= 99:
                        if progress_updates < max_updates:
                            progress_bar = self._create_progress_bar(progress)
                            try:
                                await msg.edit_text(
                                    f"📥 <b>Downloading:</b> <code>{file_name}</code>\n"
                                    f"💾 <b>Size:</b> {self._format_bytes(total_size)}\n"
                                    f"📊 <b>Progress:</b> {progress:.1f}% {progress_bar}\n"
                                    f"📦 <b>Downloaded:</b> {self._format_bytes(current_size)}\n"
                                    f"🚀 <b>Speed:</b> {self._format_bytes(speed)}/s\n"
                                    f"⏳ <b>ETA:</b> {self._format_time(eta)}"
                                )
                                last_reported = current_size
                                progress_updates += 1
                                self._last_update_time = current_time
                                self._last_bytes_received = current_size
                            except Exception as e:
                                LOGGER.debug("Progress update failed: %s", e)

                await asyncio.sleep(1)

            # Download completed
            total_time = time.time() - self._download_start_time
            avg_speed = total_size / total_time if total_time > 0 else 0

            await msg.edit_text(
                f"✅ <b>Downloaded Successfully</b>\n"
                f"🎶 <b>File:</b> <code>{file_name}</code>\n"
                f"💾 <b>Size:</b> {self._format_bytes(total_size)}\n"
                f"⏱️ <b>Time:</b> {self._format_time(total_time)}\n"
                f"🚀 <b>Avg Speed:</b> {self._format_bytes(avg_speed)}/s\n"
                f"📈 <b>Progress:</b> 100% [✅ Completed]"
            )

            async def delete_msg():
                await asyncio.sleep(1)
                await msg.delete()

            asyncio.create_task(delete_msg())
            return local_file, file_name

        except Exception as e:
            LOGGER.error("Download failed: %s", e)
            asyncio.create_task(msg.delete())
            return types.Error(code=500, message=str(e)), "DownloadFailed"

    @staticmethod
    def _create_progress_bar(progress: float, length: int = 10) -> str:
        """Create a text progress bar with smooth animation."""
        blocks = ['▱', '▰']
        filled_length = int(progress / (100 / length))
        return '[' + blocks[1] * filled_length + blocks[0] * (length - filled_length) + ']'

    @staticmethod
    def _format_bytes(size: float) -> str:
        """Convert bytes to human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if abs(size) < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Convert seconds to human-readable time format."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{int(hours)}h {int(minutes)}m"
