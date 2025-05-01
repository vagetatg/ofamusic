#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import json
import os

LANG_DIR = "src/locales"
DEFAULT_LANG = "en"

langs = {}

def load_translations():
    for f_name in os.listdir(LANG_DIR):
        lang_code = f_name.replace(".json", "")
        file_path = os.path.join(LANG_DIR, f_name)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                langs[lang_code] = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON for language '{lang_code}' in file '{f_name}': {e}")
        except Exception as e:
            print(f"Error loading translation file '{f_name}' for language '{lang_code}': {e}")

def get_string(key: str, lang: str = DEFAULT_LANG) -> str:
    return langs.get(lang, langs[DEFAULT_LANG]).get(key, key)

