#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
import re
from pathlib import Path
from typing import Any, Optional, Union

import yt_dlp
from pytdbot import types

from src import config
from src.logger import LOGGER
from ._dataclass import MusicTrack, PlatformTracks, TrackInfo
from ._downloader import MusicService
from ._httpx import DownloadResult, HttpxClient


class JiosaavnData(MusicService):
    """
    JioSaavn music service handler for searching, parsing and downloading tracks.
    """
    JIOSAAVN_SONG_PATTERN = re.compile(
        r"^(https?://)?(www\.)?jiosaavn\.com/song/[\w-]+/[a-zA-Z0-9_-]+", re.IGNORECASE
    )
    JIOSAAVN_PLAYLIST_PATTERN = re.compile(
        r"^(https?://)?(www\.)?jiosaavn\.com/featured/[\w-]+/[a-zA-Z0-9_-]+$",
        re.IGNORECASE,
    )

    # API endpoints
    API_SEARCH_ENDPOINT = (
        "https://www.jiosaavn.com/api.php?"
        "__call=autocomplete.get&"
        "query={query}&"
        "_format=json&"
        "_marker=0&"
        "ctx=wap6dot0"
    )
    DEFAULT_ARTIST = "Unknown Artist"
    DEFAULT_ALBUM = "Unknown Album"
    DEFAULT_DURATION = 0
    DEFAULT_YEAR = 0

    def __init__(self, query: Optional[str] = None) -> None:
        self.query = query
        self._ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "socket_timeout": 10,
        }

    def is_valid(self, url: str) -> bool:
        if not url:
            return False
        return bool(
            self.JIOSAAVN_SONG_PATTERN.match(url)
            or self.JIOSAAVN_PLAYLIST_PATTERN.match(url)
        )

    async def search(self) -> Union[PlatformTracks, types.Error]:
        if not self.query:
            return types.Error(code=400, message="No query provided for search")

        if self.is_valid(self.query):
            return await self.get_info()

        url = self.API_SEARCH_ENDPOINT.format(query=self.query)
        response = await HttpxClient().make_request(url)
        if not response or not response.get("songs", {}).get("data"):
            return types.Error(code=404, message="No results found for search query")

        data = {"results": [self._format_track(track) for track in response["songs"]["data"] if track]}
        return self._create_platform_tracks(data)

    async def get_recommendations(self) -> Union[PlatformTracks, None]:
        # TODO: Implement recommendations using JioSaavn API
        return None

    async def get_info(self) -> Union[PlatformTracks, types.Error]:
        if not self.query or not self.is_valid(self.query):
            return types.Error(
                code=400, message="Invalid URL provided for get_info"
            )

        url = self.query
        if self.JIOSAAVN_SONG_PATTERN.match(url):
            data = await self.get_track_data(url)
        else:
            data = await self.get_playlist_data(url)
        return self._create_platform_tracks(data)

    async def get_track(self) -> Union[TrackInfo, types.Error]:
        if not self.query:
            return types.Error(code=400, message="No query provided for get track")

        url = (
            self.query
            if self.is_valid(self.query)
            else self.format_jiosaavn_url(self.query)
        )
        data = await self.get_track_data(url)
        if not data or not data.get("results"):
            return types.Error(code=404, message="Track not found")

        track_data = data["results"][0]
        return TrackInfo(
            cdnurl=track_data.get("cdnurl", ""),
            key="nil",
            name=track_data.get("name", ""),
            artist=track_data.get("artist", self.DEFAULT_ARTIST),
            tc=track_data.get("id", ""),
            album=track_data.get("album", self.DEFAULT_ALBUM),
            cover=track_data.get("cover", ""),
            lyrics="None",
            duration=track_data.get("duration", self.DEFAULT_DURATION),
            year=track_data.get("year", self.DEFAULT_YEAR),
            url=track_data.get("url", ""),
            platform="jiosaavn",
        )

    async def get_track_data(self, url: str) -> Optional[dict[str, Any]]:
        try:
            with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                return {"results": [self._format_track(info)]} if info else None
        except yt_dlp.DownloadError as e:
            LOGGER.error("YT-DLP error getting track %s: %s", url, str(e))
        except Exception as e:
            LOGGER.error("Unexpected error getting track %s: %s", url, str(e))
        return None

    async def get_playlist_data(self, url: str) -> Optional[dict[str, Any]]:
        try:
            with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)

                if not info or not info.get("entries"):
                    LOGGER.warning("No entries found in playlist: %s", url)
                    return None

                return {
                    "results": [
                        self._format_track(track) for track in info["entries"] if track
                    ]
                }
        except yt_dlp.DownloadError as e:
            LOGGER.error("YT-DLP error getting playlist %s: %s", url, str(e))
        except Exception as e:
            LOGGER.error("Unexpected error getting playlist %s: %s", url, str(e))
        return None

    async def download_track(
        self, track: TrackInfo, video: bool = False
    ) -> Union[Path, types.Error]:
        if not track or not track.cdnurl:
            return types.Error(code=400, message=f"No download URL available for track: {track.tc}")

        download_path = config.DOWNLOADS_DIR / f"{track.tc}.m4a"
        dl: DownloadResult = await HttpxClient(max_redirects=1).download_file(track.cdnurl, download_path)
        return dl.file_path if dl.success else types.Error(code=500,
                                                           message=dl.error or f"Download failed for track: {track.tc}")

    @staticmethod
    def format_jiosaavn_url(name_and_id: str) -> str:
        if not name_and_id:
            return ""

        try:
            title, song_id = name_and_id.rsplit("/", 1)
            title = re.sub(r'[\(\)"\',]', "", title.lower())
            title = re.sub(r"\s+", "-", title.strip())
            return f"https://www.jiosaavn.com/song/{title}/{song_id}"
        except ValueError:
            LOGGER.warning("Invalid name_and_id format: %s", name_and_id)
            return ""

    @classmethod
    def _format_track(cls, track_data: dict[str, Any]) -> dict[str, Any]:
        if not track_data:
            return {}

        # Get the highest quality format
        formats = track_data.get("formats", [])
        best_format = max(formats, key=lambda x: x.get("abr", 0), default={})

        # Extract artist information
        artists = track_data.get("artists", [])
        artist = track_data.get("artist", artists[0] if artists else cls.DEFAULT_ARTIST)

        # Generate display ID
        title = track_data.get("title", "")
        display_id = f"{title}/{track_data.get('url', '').split('/')[-1]}"

        return {
            "id": track_data.get("display_id", display_id),
            "tc": track_data.get("display_id", display_id),
            "name": title,
            "album": track_data.get("album", cls.DEFAULT_ALBUM),
            "duration": track_data.get("duration", cls.DEFAULT_DURATION),
            "artist": artist,
            "cover": track_data.get("thumbnail", ""),
            "year": track_data.get("release_year", cls.DEFAULT_YEAR),
            "platform": "jiosaavn",
            "url": track_data.get("webpage_url", ""),
            "cdnurl": best_format.get("url", ""),
        }

    @staticmethod
    def _create_platform_tracks(data: dict[str, Any]) -> Union[PlatformTracks, types.Error]:
        if not data or not data.get("results"):
            return types.Error(
                code=404, message="No results found"
            )

        return PlatformTracks(
            tracks=[MusicTrack(**track) for track in data["results"] if track]
        )
