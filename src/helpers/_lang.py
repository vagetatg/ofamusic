#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
import aiofiles
import json
import logging

from functools import lru_cache
from pathlib import Path
from typing import Dict

from pytdbot import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_LANG = "en"

LANG_NAMES = {
    "en": "English",
    "hi": "हिन्दी",
    "es": "Spanish",
    "fr": "French",
    "ar": "Arabic",
    "bn": "Bengali",
    "ru": "Russian",
    "id": "Indonesia",
    "kur": "Kurdish",
    "fa": "Persian",
}


class LanguageSystem:
    _instance = None
    langs: Dict[str, Dict[str, str]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def load_translations(self, locale_dir: str = "src/locales"):
        """Load all translation files"""
        locale_path = Path(locale_dir)
        await asyncio.gather(
            *[self._load_lang_file(f) for f in locale_path.glob("*.json")]
        )

    async def _load_lang_file(self, file_path: Path):
        lang_code = file_path.stem
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                self.langs[lang_code] = json.loads(await f.read())
        except Exception as e:
            logger.error(f"Failed to load {lang_code} translation: {e}")

    @lru_cache(maxsize=1024)
    def get_string(self, key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
        """Optimized string lookup with caching"""
        text = self.langs.get(lang, {}).get(key)
        if text is not None:
            return text.format(**kwargs) if kwargs else text

        text = self.langs.get(DEFAULT_LANG, {}).get(key)
        if text is not None:
            logger.warning(f"Missing key '{key}' in '{lang}', using '{DEFAULT_LANG}'.")
            return text.format(**kwargs) if kwargs else text

        logger.error(f"Missing key '{key}' in both '{lang}' and '{DEFAULT_LANG}'.")
        return key

    @staticmethod
    def generate_lang_buttons() -> types.ReplyMarkupInlineKeyboard:
        """Generate language selection keyboard"""
        buttons = []
        row = []

        for lang_code, lang_name in sorted(LANG_NAMES.items()):
            row.append(
                types.InlineKeyboardButton(
                    text=lang_name,
                    type=types.InlineKeyboardButtonTypeCallback(
                        f"lang_{lang_code}".encode()
                    ),
                )
            )

            if len(row) == 2:
                buttons.append(row)
                row = []

        if row:
            buttons.append(row)

        return types.ReplyMarkupInlineKeyboard(buttons)


# Initialize language system
i18n = LanguageSystem()
LangsButtons = i18n.generate_lang_buttons()
