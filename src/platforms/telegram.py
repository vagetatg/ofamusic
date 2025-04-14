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
        except Exception as e:
            LOGGER.error("Error while extracting file info: %s", e)

        LOGGER.info(
            "Unknown or unsupported content type: %s", type(self.content).__name__
        )
        return 0, "UnknownMedia"

    async def dl(self) -> Union[Tuple[Error, str], Tuple[LocalFile, str]]:
        """Download file with proper progress tracking and 1-second sleep."""
        if not self.is_valid():
            return (
                types.Error(message="Invalid or unsupported media file."),
                "InvalidMedia",
            )

        total_size, file_name = self._extract_file_info()
        file_id = "TODo" # self.msg.remote_file_id
        button = types.ReplyMarkupInlineKeyboard(
            [
                [
                    types.InlineKeyboardButton(
                        text="✗ Cancel Download",
                        type=types.InlineKeyboardButtonTypeCallback(f"play_cancel_{file_id}".encode())
                    ),
                ],
            ]
        )

        # Send initial progress message
        msg = await self.msg._client.sendTextMessage(
            chat_id=self.msg.chat_id,
            text=f"📥 <b>Downloading:</b> <code>{file_name}</code>\n"
                 f"💾 <b>Size:</b> {self._format_bytes(total_size)}\n"
                 "📊 <b>Progress:</b> 0% ▱▱▱▱▱▱▱▱▱▱\n"
                 "🚀 <b>Speed:</b> 0B/s\n"
                 "⏳ <b>ETA:</b> Calculating...",
            reply_markup=button,
        )
        if isinstance(msg, types.Error):
            LOGGER.error("Error sending download message: %s", msg)
            return msg, "ErrorSendingMessage"

        try:
            # Start download and get file descriptor
            file_descriptor = await self.msg.download(synchronous=False)
            if isinstance(file_descriptor, types.Error):
                LOGGER.error("Error downloading file: %s", file_descriptor)
                return file_descriptor, "ErrorDownloadingFile"

            start_time = time.time()
            last_update_time = start_time
            last_bytes = 0
            last_message = ""
            consecutive_zero_updates = 0
            max_zero_updates = 5

            while True:
                LOGGER.info("Downloading file... %s", file_descriptor)
                await asyncio.sleep(1)
                current_bytes = file_descriptor.downloaded_prefix_size
                current_time = time.time()
                if current_bytes == 0:
                    consecutive_zero_updates += 1
                    if consecutive_zero_updates >= max_zero_updates:
                        return types.Error(code=500, message="Download stalled - no progress made"), "WTF ?"
                    continue
                else:
                    consecutive_zero_updates = 0

                progress = (current_bytes / total_size) * 100 if total_size > 0 else 0

                # Calculate speed and ETA
                time_diff = current_time - last_update_time
                bytes_diff = current_bytes - last_bytes
                speed = bytes_diff / time_diff if time_diff > 0 else 0
                eta = (total_size - current_bytes) / speed if speed > 0 else 0

                progress_bar = self._create_progress_bar(progress)
                current_message = (
                    f"📥 <b>Downloading:</b> <code>{file_name}</code>\n"
                    f"💾 <b>Size:</b> {self._format_bytes(total_size)}\n"
                    f"📊 <b>Progress:</b> {progress:.1f}% {progress_bar}\n"
                    f"🚀 <b>Speed:</b> {self._format_bytes(speed)}/s\n"
                    f"⏳ <b>ETA:</b> {self._format_time(eta)}"
                )

                if current_message != last_message:
                    try:
                        new_msg = await msg.edit_text(
                            text=current_message,
                            reply_markup=button,
                        )
                        if isinstance(new_msg, types.Error):
                            if new_msg.message == "MESSAGE_NOT_MODIFIED":
                                LOGGER.debug("Message not modified (no changes)")
                            else:
                                LOGGER.error("Error updating message: %s", new_msg)
                        else:
                            last_message = current_message
                    except Exception as e:
                        return types.Error(code=500, message=str(e)), "DownloadFailed"

                last_update_time = current_time
                last_bytes = current_bytes
                if current_bytes >= total_size > 0 or file_descriptor.is_downloading_completed:
                    break

            if not file_descriptor.is_downloading_completed:
                raise Exception("Download did not complete successfully")

            # Download completed
            total_time = time.time() - start_time
            avg_speed = total_size / total_time if total_time > 0 else 0

            await msg.edit_text(
                f"✅ <b>Download Complete</b>\n"
                f"📦 <b>File:</b> <code>{file_name}</code>\n"
                f"📏 <b>Size:</b> {self._format_bytes(total_size)}\n"
                f"⏱ <b>Time:</b> {self._format_time(total_time)}\n"
                f"🚀 <b>Avg Speed:</b> {self._format_bytes(avg_speed)}/s"
            )

            # Auto-delete after delay
            async def delete_msg():
                await asyncio.sleep(5)
                await msg.delete()

            asyncio.create_task(delete_msg())
            return file_descriptor, file_name

        except Exception as e:
            LOGGER.error("Download failed: %s", e)
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
