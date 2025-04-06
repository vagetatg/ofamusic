#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

__all__ = [
    "Filter",
    "sec_to_min",
    "get_audio_duration",
    "play_button",
    "PauseButton",
    "ResumeButton",
    "SupportButton",
]

import asyncio
import json
import re
from typing import Union

from pytdbot import filters, types

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
        proc = await asyncio.create_subprocess_exec(
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout)
        duration = float(data['format']['duration'])
        return int(duration)
    except Exception as e:
        LOGGER.warning(f"Failed to get audio duration using ffprobe: {e}")
        return 0


class Filter:
    @staticmethod
    def _extract_text(event) -> str | None:
        if isinstance(event, types.Message) and isinstance(event.content, types.MessageText):
            return event.content.text.text
        if isinstance(event, types.UpdateNewMessage) and isinstance(event.message, types.MessageText):
            return event.message.text.text
        if isinstance(event, types.UpdateNewCallbackQuery) and event.payload:
            return event.payload.data.decode()

        return None

    @staticmethod
    def command(commands: Union[str, list[str]], prefixes: str = "/!") -> filters.Filter:
        """
        Filter for commands. Supports multiple commands and prefixes like / or !.
        Also handles commands with @mentions (e.g., /start@BotName).
        """
        if isinstance(commands, str):
            commands = [commands]
        commands_set = {cmd.lower() for cmd in commands}

        pattern = re.compile(
            fr"^[{re.escape(prefixes)}](\w+)(?:@(\w+))?",
            re.IGNORECASE
        )

        async def filter_func(client, event) -> bool:
            text = Filter._extract_text(event)
            if not text:
                return False

            match = pattern.match(text.strip())
            if not match:
                return False

            cmd, mentioned_bot = match.groups()
            if cmd.lower() not in commands_set:
                return False

            if mentioned_bot:
                bot_username = client.me.usernames.editable_username
                return bot_username and mentioned_bot.lower() == bot_username.lower()

            return True

        return filters.create(filter_func)

    @staticmethod
    def regex(pattern: str) -> filters.Filter:
        """
        Filter for messages or callback queries matching a regex pattern.
        """

        compiled = re.compile(pattern)

        async def filter_func(_, event) -> bool:
            text = Filter._extract_text(event)
            return bool(compiled.search(text)) if text else False

        return filters.create(filter_func)

    @staticmethod
    def user(user_ids: Union[int, list[int]]) -> filters.Filter:
        """
        Filter for specific user IDs.
        """
        user_ids = {user_ids} if isinstance(user_ids, int) else set(user_ids)
        async def filter_func(_, event) -> bool:
            sender = event.sender_id

            if isinstance(sender, types.MessageSenderChat):
                return sender.chat_id in user_ids
            elif isinstance(sender, types.MessageSenderUser):
                return sender.user_id in user_ids

            return False

        return filters.create(filter_func)

    @staticmethod
    def chat(chat_ids: Union[int, list[int]]) -> filters.Filter:
        """
        Filter for specific chat IDs.
        """
        chat_ids = {chat_ids} if isinstance(chat_ids, int) else set(chat_ids)

        async def filter_func(_, event) -> bool:
            return getattr(event, "chat_id", None) in chat_ids

        return filters.create(filter_func)
