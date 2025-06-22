#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import re
from pathlib import Path
from typing import Optional, Union

from pytdbot import types

from src import config
from src.logger import LOGGER
from ._dataclass import MusicTrack, PlatformTracks, TrackInfo
from ._downloader import MusicService
from ._httpx import HttpxClient
from ._spotify_dl_helper import SpotifyDownload


class ApiData(MusicService):
    """Handles music data from various streaming platforms through API integration."""
    URL_PATTERNS = {
        # "apple_music": re.compile(
        #     r"^(https?://)?(music\.apple\.com/([a-z]{2}/)?(album|playlist|song)/[a-zA-Z0-9\-_]+/[0-9]+)(\?.*)?$",
        #     re.IGNORECASE,
        # ),
        "spotify": re.compile(
            r"^(https?://)?(open\.spotify\.com/(track|playlist|album|artist)/[a-zA-Z0-9]+)(\?.*)?$",
            re.IGNORECASE,
        ),
        "soundcloud": re.compile(
            r"^(https?://)?(www\.)?soundcloud\.com/[a-zA-Z0-9_-]+(/(sets)?/[a-zA-Z0-9_-]+)?(\?.*)?$",
            re.IGNORECASE,
        ),
    }

    def __init__(self, query: Union[str, None] = None) -> None:
        self.query = self._sanitize_query(query) if query else None
        self.api_url = config.API_URL.rstrip("/") if config.API_URL else None
        self.api_key = config.API_KEY
        self.client = HttpxClient()

    @staticmethod
    def _sanitize_query(query: str) -> str:
        """Clean and normalize the input query."""
        return query.strip().split("?")[0].split("#")[0]

    def is_valid(self, url: Union[str, None]) -> bool:
        if not url or not self.api_url or not self.api_key:
            return False

        return any(pattern.match(url) for pattern in self.URL_PATTERNS.values())

    async def _make_api_request(
        self, endpoint: str, params: Optional[dict] = None
    ) -> Union[dict, None]:
        if not self.api_url or not self.api_key:
            LOGGER.error("API configuration missing")
            return None

        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        return await self.client.make_request(url, params=params)

    async def get_recommendations(self, limit: int = 4) -> Optional[PlatformTracks]:
        """
        Get recommended tracks.

        Args:
            limit: Number of recommendations to fetch

        Returns:
            PlatformTracks: Contains recommended tracks or None if failed
        """
        data = await self._make_api_request("recommend_songs", {"lim": limit})
        return self._parse_tracks_response(data) if data else None

    async def get_info(self) -> Optional[PlatformTracks]:
        if not self.query or not self.is_valid(self.query):
            return None

        data = await self._make_api_request("get_url", {"url": self.query})
        return self._parse_tracks_response(data) if data else None

    async def search(self) -> Union[PlatformTracks, None]:
        if not self.query:
            return None

        # If query is a URL, get info instead of searching
        if self.is_valid(self.query):
            return await self.get_info()

        data = await self._make_api_request("search_track", {"q": self.query})
        return self._parse_tracks_response(data) if data else None

    async def get_track(self) -> Union[TrackInfo, None]:
        if not self.query:
            return None

        data = await self._make_api_request("get_track", {"id": self.query})
        return TrackInfo(**data) if data else None

    async def download_track(
        self, track: TrackInfo, video: bool = False
    ) -> Union[Path, types.Error]:
        if not track:
            return types.Error(code=400, message="Track not found")

        if track.platform.lower() == "spotify":
            return await SpotifyDownload(track).process()

        if not track.cdnurl:
            LOGGER.error("No download URL available for track %s", track.tc)
            return types.Error(
                code=400, message=f"No download URL available for track: {track.tc}"
            )

        download_path = config.DOWNLOADS_DIR / f"{track.tc}.mp3"
        result = await self.client.download_file(track.cdnurl, download_path)
        if not result.success:
            LOGGER.error("Download failed for track %s", track.tc)
            return types.Error(
                code=500, message=result.error or f"Download failed for track: {track.tc}"
            )
        return result.file_path

    @staticmethod
    def _parse_tracks_response(data: dict) -> Union[PlatformTracks, None]:
        if not data or not isinstance(data, dict) or "results" not in data:
            return None

        valid_tracks = [
            MusicTrack(**track)
            for track in data["results"]
            if track and isinstance(track, dict)
        ]
        return PlatformTracks(tracks=valid_tracks) if valid_tracks else None
