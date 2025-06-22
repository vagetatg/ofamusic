#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from ._api import ApiData
from ._cacher import user_status_cache, ChatMemberStatus, chat_invite_cache, chat_cache
from ._database import db
from ._dataclass import CachedTrack, MusicTrack, PlatformTracks, TrackInfo, ChannelPlay
from ._downloader import MusicServiceWrapper
from ._jiosaavn import JiosaavnData
from ._lang import LangsButtons, i18n
from ._pytgcalls import call, start_clients
from ._save_cookies import save_all_cookies
from ._telegram import Telegram
from ._youtube import YouTubeData


def get_string(key: str, lang: str = "en") -> str:
    return i18n.get_string(key, lang)


__all__ = [
    "ApiData",
    "chat_cache",
    "user_status_cache",
    "chat_invite_cache",
    "ChatMemberStatus",
    "JiosaavnData",
    "db",
    "MusicServiceWrapper",
    "save_all_cookies",
    "CachedTrack",
    "TrackInfo",
    "MusicTrack",
    "PlatformTracks",
    "i18n",
    "LangsButtons",
    "call",
    "start_clients",
    "Telegram",
    "YouTubeData",
    "ChannelPlay",
    "get_string",
]
