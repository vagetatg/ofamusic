#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

#  CATATAN: JANGAN EDIT FILE INI KECUALI ANDA TAHU APA YANG ANDA LAKUKAN.
#  Konfigurasi variabel lingkungan menggunakan file `.env` sebagai gantinya.

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from src.logger import LOGGER

load_dotenv()


def get_env_int(name: str, default: Optional[int] = None) -> Optional[int]:
    """
    Mengambil variabel lingkungan dan mengkonversinya ke integer.

    Args:
        name (str): Nama variabel lingkungan.
        default (Optional[int]): Nilai fallback jika parsing gagal.

    Returns:
        Optional[int]: Integer yang diuraikan atau nilai default.
    """
    value = os.getenv(name)
    try:
        return int(value)
    except (TypeError, ValueError):
        LOGGER.warning("Nilai tidak valid untuk %s: %s (default: %s)", name, value, default)
        return default


def get_env_bool(name: str, default: bool = False) -> bool:
    """
    Mengambil variabel lingkungan dan menginterpretasikannya sebagai boolean.

    Args:
        name (str): Nama variabel lingkungan.
        default (bool): Nilai boolean default.

    Returns:
        bool: Nilai boolean yang diuraikan.
    """
    return os.getenv(name, str(default)).lower() == "true"


def get_session_strings(prefix: str = "STRING", count: int = 10) -> list[str]:
    """
    Mengambil beberapa string sesi dari lingkungan.

    Args:
        prefix (str): Awalan variabel lingkungan.
        count (int): Jumlah kunci sesi yang akan diperiksa.

    Returns:
        list[str]: Daftar string sesi yang valid.
    """
    return [s.strip() for i in range(1, count + 1) if (s := os.getenv(f"{prefix}{i}"))]


def process_cookie_urls(value: Optional[str]) -> list[str]:
    """
    Menguraikan URL yang dipisahkan spasi atau koma menjadi daftar.

    Args:
        value (Optional[str]): Nilai mentah variabel lingkungan COOKIES_URL.

    Returns:
        list[str]: Daftar string URL yang telah dibersihkan.
    """
    if not value:
        return []
    return [url.strip() for url in value.replace(",", " ").split() if url.strip()]


# Konfigurasi Bot Inti
API_ID: Optional[int] = get_env_int("API_ID")
API_HASH: Optional[str] = os.getenv("API_HASH")
TOKEN: Optional[str] = os.getenv("TOKEN")

SESSION_STRINGS: list[str] = get_session_strings()
MONGO_URI: Optional[str] = os.getenv("MONGO_URI")
API_URL: str = os.getenv("API_URL", "https://tgmusic.fallenapi.fun")
API_KEY: Optional[str] = os.getenv("API_KEY")

# Pemilik dan Logger
OWNER_ID: int = get_env_int("OWNER_ID", 5938660179)
LOGGER_ID: int = get_env_int("LOGGER_ID", -1002166934878)

# Pengaturan Opsional
PROXY: Optional[str] = os.getenv("PROXY")
DEFAULT_SERVICE: str = os.getenv("DEFAULT_SERVICE", "youtube").lower()
MIN_MEMBER_COUNT: int = get_env_int("MIN_MEMBER_COUNT", 50)

DOWNLOADS_DIR: Path = Path(os.getenv("DOWNLOADS_DIR", "database/music"))

SUPPORT_GROUP: str = os.getenv("SUPPORT_GROUP", "https://t.me/GuardxSupport")
SUPPORT_CHANNEL: str = os.getenv("SUPPORT_CHANNEL", "https://t.me/FallenProjects")

IGNORE_BACKGROUND_UPDATES: bool = get_env_bool("IGNORE_BACKGROUND_UPDATES", True)
AUTO_LEAVE: bool = get_env_bool("AUTO_LEAVE", True)

# Cookies
COOKIES_URL: list[str] = process_cookie_urls(os.getenv("COOKIES_URL"))

# Pengembang
devs_env: Optional[str] = os.getenv("DEVS")
DEVS: list[int] = list(map(int, devs_env.split())) if devs_env else []
if OWNER_ID and OWNER_ID not in DEVS:
    DEVS.append(OWNER_ID)

# Konfigurasi AI
GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY") # Tambahkan baris ini
