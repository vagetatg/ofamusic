import asyncio
from typing import Optional

from pyrogram import types, errors

from src.logger import LOGGER


class Telegram:
    """A helper class to process Telegram messages containing playable media (audio/video)."""

    def __init__(self, reply: Optional[types.Message]):
        """Initialize with a Telegram message object."""
        self.msg = reply

    def is_valid(self) -> bool:
        """Checks if the message contains a playable media file (audio or video)."""
        if not self.msg:
            return False
        return bool(self.msg.audio or self.msg.video or self.msg.voice)

    def get_file_name(self) -> str:
        """Retrieves the file name from the media message."""
        if not self.is_valid():
            return "Unknown Media"
        if self.msg.audio and self.msg.audio.file_name:
            return self.msg.audio.file_name
        elif self.msg.video and self.msg.video.file_name:
            return self.msg.video.file_name
        elif self.msg.voice:
            return "Voice Message"
        return "Unknown Media"

    async def dl(self) -> str:
        """Downloads the media file asynchronously."""
        try:
            return await self.msg.download()
        except errors.FloodWait as e:
            LOGGER.warning(f"FloodWait detected, waiting {e.value}s")
            await asyncio.sleep(e.value + 1)
            return await self.msg.download()
        except Exception as e:
            LOGGER.error(f"Error downloading media: {e}")
            return ""
