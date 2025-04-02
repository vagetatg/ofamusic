# Copyright (c) 2025 AshokShau.
# TgMusicBot is an open-source Telegram music bot licensed under AGPL-3.0.
# All rights reserved where applicable.
#
#

import asyncio
import re
from pathlib import Path
from typing import Optional, Any
import yt_dlp

import config
from src.logger import LOGGER
from ._httpx import HttpxClient, DownloadResult
from .dataclass import PlatformTracks, TrackInfo, MusicTrack
from .downloader import MusicService


class JiosaavnData(MusicService):
    JIOSAAVN_SONG_PATTERN = re.compile(
        r"^(https?://)?(www\.)?jiosaavn\.com/song/[\w-]+/[a-zA-Z0-9_-]+",
        re.IGNORECASE
    )
    JIOSAAVN_PLAYLIST_PATTERN = re.compile(
        r"^(https?://)?(www\.)?jiosaavn\.com/featured/[\w-]+/[a-zA-Z0-9_-]+$",
        re.IGNORECASE
    )
    API_SEARCH_URL = "https://www.jiosaavn.com/api.php?__call=autocomplete.get&query={query}&_format=json&_marker=0&ctx=wap6dot0"

    def __init__(self, query: str = None) -> None:
        self.query = query
        self.client = HttpxClient(max_redirects=1)
        self._ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "socket_timeout": 10,
        }

    def is_valid(self, url: str) -> bool:
        """Check if the URL is a valid JioSaavn song or playlist URL."""
        if not url:
            return False
        return bool(
            self.JIOSAAVN_SONG_PATTERN.match(url) or
            self.JIOSAAVN_PLAYLIST_PATTERN.match(url)
        )

    async def _fetch_data(self, url: str) -> Optional[dict[str, Any]]:
        """Fetch data based on URL type (song or playlist)."""
        try:
            if self.JIOSAAVN_SONG_PATTERN.match(url):
                return await self.get_track_data(url)
            return await self.get_playlist_data(url)
        except Exception as e:
            LOGGER.error(f"Error fetching data from {url}: {str(e)}")
            return None

    async def search(self) -> Optional[PlatformTracks]:
        """Search for tracks. Falls back to JioSaavn API if not a direct URL."""
        if not self.query:
            return None

        if self.is_valid(self.query):
            data = await self._fetch_data(self.query)
        else:
            try:
                url = self.API_SEARCH_URL.format(query=self.query)
                response = await self.client.make_request(url)
                data = self._parse_search_response(response)
            except Exception as e:
                LOGGER.error(f"Error searching for {self.query}: {str(e)}")
                data = None

        return self._create_platform_tracks(data) if data else None

    def _parse_search_response(self, response: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Parse the search API response into standardized format."""
        if not response or "songs" not in response or "data" not in response["songs"]:
            return None
        return {
            "results": [
                self._format_track(track)
                for track in response["songs"]["data"]
                if track
            ]
        }

    async def get_recommendations(self) -> Optional[PlatformTracks]:
        """Placeholder for recommendations functionality."""
        # TODO: Implement recommendations using JioSaavn API
        return None

    async def get_info(self) -> Optional[PlatformTracks]:
        """Get track or playlist info."""
        if not self.query or not self.is_valid(self.query):
            return None
        data = await self._fetch_data(self.query)
        return self._create_platform_tracks(data) if data else None

    async def get_track(self) -> Optional[TrackInfo]:
        """Get detailed track information."""
        if not self.query:
            return None

        url = self.query if self.is_valid(self.query) else self.format_jiosaavn_url(self.query)
        data = await self.get_track_data(url)
        if not data or not data.get("results"):
            return None

        return self._create_track_info(data["results"][0])

    async def get_track_data(self, url: str) -> Optional[dict[str, Any]]:
        """Get track data using yt-dlp."""
        try:
            with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                return {"results": [self._format_track(info)]} if info else None
        except Exception as e:
            LOGGER.error(f"Error getting track data from {url}: {str(e)}")
            return None

    async def get_playlist_data(self, url: str) -> Optional[dict[str, Any]]:
        """Get playlist data using yt-dlp."""
        try:
            with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                if not info or not info.get("entries"):
                    LOGGER.warning(f"No entries found in playlist: {url}")
                    return None
                return {
                    "results": [
                        self._format_track(track)
                        for track in info["entries"]
                        if track
                    ]
                }
        except Exception as e:
            LOGGER.error(f"Error getting playlist data from {url}: {str(e)}")
            return None

    async def download_track(self, track: TrackInfo) -> Optional[Path]:
        """Download a track to local storage."""
        if not track or not track.cdnurl:
            return None

        download_path = Path(config.DOWNLOADS_DIR) / f"{track.tc}.m4a"
        dl: DownloadResult = await self.client.download_file(track.cdnurl, download_path)
        return dl.file_path if dl.success else None

    @staticmethod
    def format_jiosaavn_url(name_and_id: str) -> str:
        """Format a JioSaavn URL from name and ID."""
        if not name_and_id:
            return ""

        try:
            title, song_id = name_and_id.rsplit("/", 1)
            title = re.sub(r'[\(\)"\',]', "", title.lower())
            title = re.sub(r'\s+', "-", title.strip())
            return f"https://www.jiosaavn.com/song/{title}/{song_id}"
        except ValueError:
            return ""

    @staticmethod
    def _format_track(track_data: dict[str, Any]) -> dict[str, Any]:
        """Format track data into a standardized format."""
        if not track_data:
            return {}

        formats = track_data.get("formats", [])
        best_format = max(
            formats,
            key=lambda x: x.get("abr", 0),
            default={}
        )
        download_url = best_format.get("url", "")
        artists = track_data.get("artists", [])
        artist = track_data.get("artist", artists[0] if artists else "Unknown")
        title = track_data.get("title", "")
        display_id = f"{title}/{track_data.get('url', '').split('/')[-1]}"

        return {
            "id": track_data.get("display_id", display_id),
            "tc": track_data.get("display_id", display_id),
            "name": title,
            "album": track_data.get("album", ""),
            "duration": track_data.get("duration", 0),
            "artist": artist,
            "cover": track_data.get("thumbnail", ""),
            "year": track_data.get("release_year", 0),
            "platform": "jiosaavn",
            "url": track_data.get("webpage_url", ""),
            "cdnurl": track_data.get("url", download_url),
        }

    @staticmethod
    def _create_track_info(track_data: dict[str, Any]) -> TrackInfo:
        """Create TrackInfo object from raw track data."""
        return TrackInfo(
            cdnurl=track_data.get("cdnurl", ""),
            key="nil",
            name=track_data.get("name", ""),
            artist=track_data.get("artist", "Unknown"),
            tc=track_data.get("id", ""),
            album=track_data.get("album", ""),
            cover=track_data.get("cover", ""),
            lyrics="None",
            duration=track_data.get("duration", 0),
            year=track_data.get("year", 0),
            url=track_data.get("url", ""),
            platform="jiosaavn",
        )

    @staticmethod
    def _create_platform_tracks(data: dict[str, Any]) -> Optional[PlatformTracks]:
        """Create PlatformTracks object from formatted data."""
        if not data or not data.get("results"):
            return None

        return PlatformTracks(
            tracks=[
                MusicTrack(**track)
                for track in data["results"]
                if track
            ]
        )
