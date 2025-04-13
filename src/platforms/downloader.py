#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.


from abc import ABC, abstractmethod
from typing import Optional

import config
from .dataclass import PlatformTracks, TrackInfo


class MusicService(ABC):
    @abstractmethod
    def is_valid(self, url: str) -> bool:
        pass

    @abstractmethod
    async def get_info(self) -> Optional[PlatformTracks]:
        pass

    @abstractmethod
    async def search(self) -> Optional[PlatformTracks]:
        pass

    @abstractmethod
    async def get_recommendations(self) -> Optional[PlatformTracks]:
        pass

    @abstractmethod
    async def get_track(self) -> Optional[TrackInfo]:
        pass

    @abstractmethod
    async def download_track(
        self, track_info: TrackInfo, video: bool = False
    ) -> Optional[str]:
        pass


class MusicServiceWrapper(MusicService):
    def __init__(self, query: str = ""):
        self.query = query
        self.service = self._get_service()

    def _get_service(self) -> MusicService:
        from ._api import ApiData
        from ._jiosaavn import JiosaavnData
        from ._youtube import YouTubeData

        query = self.query
        if YouTubeData().is_valid(query):
            return YouTubeData(query)
        elif JiosaavnData().is_valid(query):
            return JiosaavnData(query)
        elif ApiData().is_valid(query):
            return ApiData(query)
        elif config.DEFAULT_SERVICE == "spotify":
            return ApiData(query)
        elif config.DEFAULT_SERVICE == "youtube":
            return YouTubeData(query)
        elif config.DEFAULT_SERVICE == "jiosaavn":
            return JiosaavnData(query)
        else:
            return (
                ApiData(query)
                if config.API_URL and config.API_KEY
                else YouTubeData(query)
            )

    def is_valid(self, url: str) -> bool:
        return self.service.is_valid(url)

    async def get_info(self) -> Optional[PlatformTracks]:
        return await self.service.get_info()

    async def search(self) -> Optional[PlatformTracks]:
        return await self.service.search()

    async def get_recommendations(self) -> Optional[PlatformTracks]:
        return await self.service.get_recommendations()

    async def get_track(self) -> Optional[TrackInfo]:
        return await self.service.get_track()

    async def download_track(
        self, track_info: TrackInfo, video: bool = False
    ) -> Optional[str]:
        return await self.service.download_track(track_info)
