from typing import Tuple, Union, Optional, Dict
from cachetools import TTLCache
from pytdbot import types
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
        self._file_info = None  # Cache for file info
        self.DownloaderCache = TTLCache(maxsize=5000, ttl=1200)

    @property
    def file_info(self) -> Tuple[int, str]:
        """Lazy-loaded property for file info."""
        if self._file_info is None:
            self._file_info = self._extract_file_info()
        return self._file_info

    def is_valid(self) -> bool:
        """Check if the message contains a supported media type within size limits."""
        if not self.msg or isinstance(self.msg, types.Error):
            return False

        if isinstance(self.content, self.UNSUPPORTED_TYPES):
            return False

        file_size, _ = self.file_info
        return 0 < file_size <= self.MAX_FILE_SIZE

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
                if mime.startswith(("audio/", "video/")):
                    return (
                        self.content.document.document.size,
                        self.content.document.file_name or "Document.mp4",
                    )
        except Exception as e:
            LOGGER.error("Error while extracting file info: %s", e)

        LOGGER.info("Unsupported content type: %s", type(self.content).__name__)
        return 0, "UnknownMedia"

    async def dl(self) -> Tuple[Union[types.Error, types.LocalFile], str]:
        """Download the media file with metadata caching."""
        if not self.is_valid():
            return types.Error(message="Invalid or unsupported media file."), "InvalidMedia",

        unique_id = self.msg.remote_unique_file_id
        chat_id = self.msg.chat_id
        _, file_name = self.file_info

        # Store metadata in cache
        if unique_id not in self.DownloaderCache:
            self.DownloaderCache[unique_id] = {
                "chat_id": chat_id,
                "filename": file_name
            }

        file_obj = await self.msg.download()
        return file_obj, file_name

    def get_cached_metadata(self, unique_id: str) -> Optional[Dict[str, Union[int, str]]]:
        return self.DownloaderCache.get(unique_id, None)
