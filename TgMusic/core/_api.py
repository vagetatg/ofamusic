#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import re
from pathlib import Path
from typing import Optional, Union

from pytdbot import types
from TgMusic.logger import LOGGER

from ._config import config
from ._downloader import MusicService
from ._httpx import HttpxClient
from ._spotify_dl_helper import SpotifyDownload
from ._dataclass import PlatformTracks, MusicTrack, TrackInfo


class ApiData(MusicService):
    """Handles music data from various streaming platforms through API integration."""

    URL_PATTERNS = {
        "apple_music": re.compile(
            r"^(https?://)?(music\.apple\.com/([a-z]{2}/)?(album|playlist|song)/[a-zA-Z0-9\-_]+/[0-9]+)(\?.*)?$",
            re.IGNORECASE,
        ),
        "spotify": re.compile(
            r"^(https?://)?(open\.spotify\.com/(track|playlist|album|artist)/[a-zA-Z0-9]+)(\?.*)?$",
            re.IGNORECASE,
        ),
        "soundcloud": re.compile(
            r"^(https?://)?(www\.)?soundcloud\.com/[a-zA-Z0-9_-]+(/(sets)?/[a-zA-Z0-9_-]+)?(\?.*)?$",
            re.IGNORECASE,
        ),
    }

    def __init__(self, query: Optional[str] = None) -> None:
        self.query = self._sanitize_query(query) if query else None
        self.api_url = config.API_URL.rstrip("/") if config.API_URL else None
        self.api_key = config.API_KEY
        self.client = HttpxClient()

    @staticmethod
    def _sanitize_query(query: str) -> str:
        return query.strip().split("?")[0].split("#")[0]

    def is_valid(self, url: Optional[str]) -> bool:
        if not url or not self.api_url or not self.api_key:
            return False
        return any(p.match(url) for p in self.URL_PATTERNS.values())

    async def _make_api_request(
        self, endpoint: str, params: Optional[dict] = None
    ) -> Optional[dict]:
        if not self.api_url or not self.api_key:
            LOGGER.warning("API configuration missing; get from @FallenAPIBot")
            return None

        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        return await self.client.make_request(url, params=params)

    async def get_info(self) -> Union[PlatformTracks, types.Error]:
        if not self.query or not self.is_valid(self.query):
            return types.Error(400, "Invalid URL provided for get info")

        data = await self._make_api_request("get_url", {"url": self.query})
        return self._parse_tracks_response(data) or types.Error(404, "Track not found")

    async def search(self) -> Union[PlatformTracks, types.Error]:
        if not self.query:
            return types.Error(400, "No query provided for search")

        if self.is_valid(self.query):
            return await self.get_info()

        data = await self._make_api_request("search_track", {"q": self.query})
        return self._parse_tracks_response(data) or types.Error(404, "Track not found")

    async def get_track(self) -> Union[TrackInfo, types.Error]:
        if not self.query:
            return types.Error(400, "No query provided for get track")

        data = await self._make_api_request("get_track", {"id": self.query})
        return TrackInfo(**data) if data else types.Error(404, "Track not found")

    async def download_track(
        self, track: TrackInfo, video: bool = False
    ) -> Union[Path, types.Error]:
        if not track:
            return types.Error(400, "Track not found")

        if track.platform.lower() == "spotify":
            return await SpotifyDownload(track).process()

        # if track.platform.lower() == "youtube":
        #     return await YouTubeData().download_track(track, video)

        if not track.cdnurl:
            msg = f"No download URL available for track: {track.tc}"
            LOGGER.error(msg)
            return types.Error(400, msg)

        download_path = config.DOWNLOADS_DIR / f"{track.tc}.mp3"
        result = await self.client.download_file(track.cdnurl, download_path)

        if not result.success:
            LOGGER.warning("Download failed for track %s", track.tc)
            return types.Error(500, result.error or f"Download failed for: {track.tc}")
        return result.file_path

    @staticmethod
    def _parse_tracks_response(
        data: Optional[dict],
    ) -> Union[PlatformTracks, types.Error]:
        if not data or "results" not in data:
            return types.Error(404, "No results found")

        tracks = [MusicTrack(**t) for t in data["results"] if isinstance(t, dict)]
        return (
            PlatformTracks(tracks=tracks)
            if tracks
            else types.Error(404, "Track not found")
        )
