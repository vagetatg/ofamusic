#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
import re
import time
import uuid
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import unquote

import aiofiles
import aiohttp

from src.config import DOWNLOADS_DIR, API_KEY, API_URL
from src.logger import LOGGER


class DownloadResult:
    def __init__(
        self,
        success: bool,
        file_path: Optional[Path] = None,
        error: Optional[str] = None,
    ):
        self.success = success
        self.file_path = file_path
        self.error = error


class AioHttpClient:
    DEFAULT_TIMEOUT = 120
    DEFAULT_DOWNLOAD_TIMEOUT = 120
    CHUNK_SIZE = 8192
    MAX_RETRIES = 2
    BACKOFF_FACTOR = 1.0

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        download_timeout: int = DEFAULT_DOWNLOAD_TIMEOUT,
        max_redirects: int = 0,
    ) -> None:
        self._timeout = timeout
        self._download_timeout = download_timeout
        self._max_redirects = max_redirects

        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(
                total=timeout, connect=timeout, sock_connect=timeout, sock_read=timeout
            )
        )

    async def close(self) -> None:
        try:
            await self._session.close()
        except Exception as e:
            LOGGER.error("Error closing HTTP session: %s", repr(e))

    @staticmethod
    def _get_headers(url: str, base_headers: dict[str, str]) -> dict[str, str]:
        headers = base_headers.copy()
        if API_URL and url.startswith(API_URL):
            headers["X-API-Key"] = API_KEY
        return headers

    async def download_file(
        self,
        url: str,
        file_path: Optional[Union[str, Path]] = None,
        overwrite: bool = False,
        **kwargs: Any,
    ) -> DownloadResult:
        if not url:
            return DownloadResult(success=False, error="Empty URL provided")

        headers = self._get_headers(url, kwargs.pop("headers", {}))

        try:
            async with self._session.get(
                url, headers=headers, timeout=self._download_timeout
            ) as response:
                if response.status != 200:
                    error_msg = (
                        f"Download failed for {url} with status code {response.status}"
                    )
                    LOGGER.error(error_msg)
                    return DownloadResult(success=False, error=error_msg)

                if file_path is None:
                    cd = response.headers.get("Content-Disposition", "")
                    match = re.search(r'filename="?([^"]+)"?', cd)
                    filename = (
                        unquote(match[1])
                        if match
                        else (Path(url).name or uuid.uuid4().hex)
                    )
                    path = Path(DOWNLOADS_DIR) / filename
                else:
                    path = Path(file_path) if isinstance(file_path, str) else file_path

                if path.exists() and not overwrite:
                    return DownloadResult(success=True, file_path=path)

                path.parent.mkdir(parents=True, exist_ok=True)
                async with aiofiles.open(path, "wb") as f:
                    async for chunk in response.content.iter_chunked(self.CHUNK_SIZE):
                        await f.write(chunk)

                LOGGER.debug("Successfully downloaded file to %s", path)
                return DownloadResult(success=True, file_path=path)

        except Exception as e:
            error_msg = f"Failed to download {url}: {repr(e)}"
            LOGGER.error(error_msg)
            return DownloadResult(success=False, error=error_msg)

    async def make_request(
        self,
        url: str,
        max_retries: int = MAX_RETRIES,
        backoff_factor: float = BACKOFF_FACTOR,
        **kwargs: Any,
    ) -> Optional[dict[str, Any]]:
        if not url:
            LOGGER.warning("Empty URL provided")
            return None

        headers = self._get_headers(url, kwargs.pop("headers", {}))

        for attempt in range(max_retries):
            try:
                start = time.monotonic()
                async with self._session.get(
                    url, headers=headers, **kwargs
                ) as response:
                    text = await response.text()
                    if response.status != 200:
                        LOGGER.warning(
                            "HTTP %d for %s. Body: %s", response.status, url, text
                        )
                        continue

                    duration = time.monotonic() - start
                    LOGGER.debug("Request to %s succeeded in %.2fs", url, duration)
                    return await response.json()

            except aiohttp.ClientError as e:
                LOGGER.warning("Request failed for %s: %s", url, repr(e))
            except asyncio.TimeoutError:
                LOGGER.warning("Timeout while requesting %s", url)
            except Exception as e:
                LOGGER.error("Unexpected error for %s: %s", url, repr(e))
                return None

            await asyncio.sleep(backoff_factor * (2**attempt))

        LOGGER.error("All retries failed for URL: %s", url)
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    def __del__(self):
        try:
            if self._session and not self._session.closed:
                asyncio.create_task(self.close())
        except RuntimeError:
            pass
