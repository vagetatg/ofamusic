#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import re
from typing import Any, Optional

from py_yt import Playlist, VideosSearch, Video

from src.helpers import MusicTrack, PlatformTracks, TrackInfo
from src.logger import LOGGER
from ._dl_helper import YouTubeDownload
from ._downloader import MusicService
from ._httpx import HttpxClient
from ..config import PROXY_URL


class YouTubeData(MusicService):
    YOUTUBE_VIDEO_PATTERN = re.compile(
        r"^(?:https?://)?(?:www\.)?(?:youtube\.com|music\.youtube\.com|youtu\.be)/(?:watch\?v=|embed/|v/)?([\w-]+)",
        re.IGNORECASE,
    )
    YOUTUBE_PLAYLIST_PATTERN = re.compile(
        r"^(?:https?://)?(?:www\.)?(?:youtube\.com|music\.youtube\.com)/playlist\?[^#]*\blist=([\w-]+)",
        re.IGNORECASE,
    )

    def __init__(self, query: str = None) -> None:
        self.client = HttpxClient()
        self.query = query.split("&")[0] if query and "&" in query else query if query else None

    def is_valid(self, url: str) -> bool:
        """Check if the URL is a valid YouTube URL."""
        return bool(url and (self.YOUTUBE_VIDEO_PATTERN.match(url) or
                             self.YOUTUBE_PLAYLIST_PATTERN.match(url)))

    async def _fetch_data(self, url: str) -> Optional[dict[str, Any]]:
        """Fetch data based on URL type (video or playlist)."""
        if self.YOUTUBE_PLAYLIST_PATTERN.match(url):
            LOGGER.debug("Fetching data for YouTube playlist: %s", url)
            return await self._get_playlist(url)

        LOGGER.debug("Fetching data for YouTube video: %s", url)
        return await self._get_youtube_url(url)

    async def get_info(self) -> Optional[PlatformTracks]:
        """Get track information from YouTube URL."""
        if not self.is_valid(self.query):
            return None
        data = await self._fetch_data(self.query)
        return self._create_platform_tracks(data) if data else None

    async def search(self) -> Optional[PlatformTracks]:
        """Search for tracks on YouTube."""
        if not self.query:
            return None
        if self.is_valid(self.query):
            return await self.get_info()

        try:
            search = VideosSearch(self.query, limit=5)
            results = await search.next()
            data = {
                "results": [self._format_track(video) for video in results["result"]]} if "result" in results else None
        except Exception as e:
            LOGGER.error("Error searching: %s", e)
            data = None

        return self._create_platform_tracks(data) if data else None

    async def get_track(self) -> Optional[TrackInfo]:
        """Get detailed track information."""
        if not self.query:
            return None

        url = f"https://youtube.com/watch?v={self.query}"
        try:
            data = await self._get_youtube_url(url)
            return await self._get_track_info(data["results"][0]) if data and "results" in data else None
        except Exception as e:
            LOGGER.error("Error fetching track: %s", e)
            return None

    async def download_track(self, track: TrackInfo, video: bool = False) -> Optional[str]:
        """Download a YouTube track."""
        try:
            return await YouTubeDownload(track).process(video)
        except Exception as e:
            LOGGER.error("Error downloading track: %s", e)
            return None

    async def _get_youtube_url(self, url: str) -> Optional[dict[str, Any]]:
        """Get YouTube video data from the URL."""
        normalized_url = await self._normalize_youtube_url(url)
        if not normalized_url:
            return None
        return await self._fallback_search_youtube(normalized_url)

    async def _fallback_search_youtube(self, url: str) -> Optional[dict[str, Any]]:
        """Search for YouTube video with fallback methods."""
        if PROXY_URL:
            try:
                vid_id = url.split("v=")[1]
                result = await Video.get(vid_id)
                track_data = {
                    "id": result["id"],
                    "title": result["title"],
                    "duration": result.get("duration", {}).get("secondsText", "0"),
                    "channel": result.get("channel", {}),
                    "thumbnails": result.get("thumbnails", [{}]),
                }
                return {
                    "results": [self._format_track({
                        "id": track_data["id"],
                        "title": track_data["title"],
                        "duration": track_data["duration"],
                        "channel": track_data["channel"],
                        "thumbnails": track_data["thumbnails"],
                    })]
                }
            except Exception as e:
                LOGGER.error("Error searching with proxy: %s", e)
                # Fall through to non-proxy search if proxy fails
        try:
            search = VideosSearch(url, limit=1)
            results = await search.next()
            return {
                "results": [self._format_track(video) for video in results["result"]]} if "result" in results else None
        except Exception as e:
            LOGGER.error("Error searching: %s", e)
            return None

    @staticmethod
    async def _get_playlist(url: str) -> Optional[dict[str, Any]]:
        """Get YouTube playlist data."""
        try:
            playlist = await Playlist.getVideos(url)
            return {
                "results": [
                    YouTubeData._format_track(track)
                    for track in playlist.get("videos", [])
                ]
            } if playlist else None
        except Exception as e:
            LOGGER.error("Error getting playlist: %s", e)
            return None

    async def get_recommendations(self) -> Optional[PlatformTracks]:
        """Get recommended tracks (not implemented)."""
        return None

    @staticmethod
    def _duration_to_seconds(duration: str) -> int:
        """Convert duration string to seconds."""
        if not duration:
            return 0

        parts = list(map(int, duration.split(":")))
        if len(parts) == 3:  # H:MM:SS
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:  # MM:SS
            return parts[0] * 60 + parts[1]
        return 0

    @staticmethod
    async def _normalize_youtube_url(url: str) -> Optional[str]:
        """Normalize different YouTube URL formats."""
        if "youtu.be" in url:
            parts = url.split("youtu.be/")
            if len(parts) < 2:
                return None
            video_id = parts[1].partition("?")[0].partition("#")[0]
            return f"https://www.youtube.com/watch?v={video_id}"
        return url

    @staticmethod
    def _create_platform_tracks(data: dict) -> PlatformTracks:
        """Create PlatformTracks object from data."""
        tracks = [MusicTrack(**track) for track in data["results"]] if data and "results" in data else []
        return PlatformTracks(tracks=tracks)

    @staticmethod
    def _format_track(track_data: dict[str, Any]) -> dict[str, Any]:
        """Format track data into a consistent structure."""
        return {
            "id": track_data.get("id"),
            "name": track_data.get("title"),
            "duration": YouTubeData._duration_to_seconds(track_data.get("duration", "0:00")),
            "artist": track_data.get("channel", {}).get("name", "Unknown"),
            "cover": track_data.get("thumbnails", [{}])[-1].get("url", ""),
            "year": 0,
            "url": f"https://www.youtube.com/watch?v={track_data.get('id')}",
            "platform": "youtube",
        }

    @staticmethod
    async def _get_track_info(track_data: dict) -> TrackInfo:
        """Helper method to create TrackInfo from track data."""
        return TrackInfo(
            cdnurl="None",
            key="None",
            name=track_data["name"],
            artist=track_data["artist"],
            tc=track_data["id"],
            album="YouTube",
            cover=track_data["cover"],
            lyrics="None",
            duration=track_data["duration"],
            platform="youtube",
            url=f"https://youtube.com/watch?v={track_data['id']}",
            year=0,
        )
