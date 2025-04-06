#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from typing import Union, Optional

from pytdbot import types

from src.logger import LOGGER


class Telegram:
    """Helper class to validate and process playable Telegram media messages."""

    MAX_FILE_SIZE = 400 * 1024 * 1024  # 400MB
    UNSUPPORTED_TYPES = (
        types.MessagePhoto,
        types.MessageSticker,
        types.MessageAnimation,
    )

    def __init__(self, reply: Optional[types.Message]):
        self.msg = reply
        self.content = reply.content if reply else None

    def is_valid(self) -> bool:
        """Check if the message contains a supported media type within size limits."""
        if not self.msg or isinstance(self.msg, types.Error):
            return False

        if isinstance(self.content, self.UNSUPPORTED_TYPES):
            LOGGER.info("Unsupported media type: %s", type(self.content).__name__)
            return False

        file_size, _ = self._extract_file_info()
        if file_size == 0 or file_size > self.MAX_FILE_SIZE:
            LOGGER.info("Invalid file size: %s", file_size)
            return False

        return True

    def _extract_file_info(self) -> tuple[int, str]:
        """Extract file size and filename from supported media types."""
        try:
            if isinstance(self.content, types.MessageVideo):
                return self.content.video.video.size, self.content.video.file_name or "Video.mp4"

            elif isinstance(self.content, types.MessageAudio):
                return self.content.audio.audio.size, self.content.audio.file_name or "Audio.mp3"

            elif isinstance(self.content, types.MessageVoiceNote):
                return self.content.voice_note.voice.size, "VoiceNote.ogg"

            elif isinstance(self.content, types.MessageVideoNote):
                return self.content.video_note.video.size, "VideoNote.mp4"

            elif isinstance(self.content, types.MessageDocument):
                mime = (self.content.document.mime_type or "").lower()
                if mime.startswith("audio/") or mime.startswith("video/"):
                    return self.content.document.document.size, self.content.document.file_name or "Document.mp4"
        except Exception as e:
            LOGGER.error("Error while extracting file info: %s", e)
    
        LOGGER.info("Unknown or unsupported content type: %s", type(self.content).__name__)
        return 0, "UnknownMedia"

    async def dl(self) -> tuple[Union["types.Error", "types.LocalFile"], str]:
        """Asynchronously download the media file."""
        if not self.is_valid():
            return types.Error(message="Invalid or unsupported media file."), "InvalidMedia"

        _, file_name = self._extract_file_info()
        return await self.msg.download(), file_name
