__all__ = [
    "sec_to_min",
    "get_audio_duration",
    "play_button",
    "PauseButton",
    "ResumeButton",
    "SupportButton",
]

from mutagen import File

from src.logger import LOGGER
from .buttons import play_button, PauseButton, ResumeButton, SupportButton


def sec_to_min(seconds):
    """Convert seconds to minutes:seconds format."""
    try:
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}:{remaining_seconds:02}"
    except Exception as e:
        LOGGER.warning(f"Failed to convert seconds to minutes:seconds format: {e}")
        return None


async def get_audio_duration(file_path):
    try:
        audio = File(file_path)
        return int(audio.info.length)
    except Exception as e:
        LOGGER.warning(f"Failed to get audio duration: {e}")
        return 0
