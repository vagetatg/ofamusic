# Copyright (c) 2025 AshokShau.
# TgMusicBot is an open-source Telegram music bot licensed under AGPL-3.0.
# All rights reserved where applicable.
#
#

import asyncio
from pathlib import Path
from typing import Optional, Any, Union
from dataclasses import dataclass

import aiofiles
import httpx

import config
from config import API_KEY
from src.logger import LOGGER


@dataclass
class DownloadResult:
    success: bool
    file_path: Optional[Path] = None
    error: Optional[str] = None


class HttpxClient:
    DEFAULT_TIMEOUT = 10
    DEFAULT_DOWNLOAD_TIMEOUT = 60
    CHUNK_SIZE = 8192  # 8KB chunks for streaming downloads
    MAX_RETRIES = 3
    BACKOFF_FACTOR = 1.0

    def __init__(
            self,
            timeout: int = DEFAULT_TIMEOUT,
            download_timeout: int = DEFAULT_DOWNLOAD_TIMEOUT,
            max_redirects: int = 0
    ) -> None:
        """
        Initialize the HTTP client with configurable settings.

        Args:
            timeout: Timeout for general HTTP requests in seconds
            download_timeout: Timeout for file downloads in seconds
            max_redirects: Maximum number of redirects to follow (0 to disable)
        """
        self._timeout = timeout
        self._download_timeout = download_timeout
        self._max_redirects = max_redirects
        self._session = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=max_redirects > 0,
            max_redirects=max_redirects,
        )

    async def close(self) -> None:
        """Close the HTTP session gracefully."""
        try:
            await self._session.aclose()
        except Exception as e:
            LOGGER.error(f"Error closing HTTP session: {str(e)}")

    async def download_file(
            self,
            url: str,
            file_path: Union[str, Path],
            overwrite: bool = False
    ) -> DownloadResult:
        """
        Download a file asynchronously with proper error handling.

        Args:
            url: URL of the file to download
            file_path: Path to save the downloaded file
            overwrite: Whether to overwrite existing file

        Returns:
            DownloadResult: Contains success status and file path or error message
        """
        if not url:
            return DownloadResult(success=False, error="Empty URL provided")

        path = Path(file_path) if isinstance(file_path, str) else file_path
        if path.exists() and not overwrite:
            return DownloadResult(success=True, file_path=path)

        try:
            async with self._session.stream(
                    "GET",
                    url,
                    timeout=self._download_timeout
            ) as response:
                response.raise_for_status()

                # Ensure parent directory exists
                path.parent.mkdir(parents=True, exist_ok=True)

                async with aiofiles.open(path, "wb") as f:
                    async for chunk in response.aiter_bytes(self.CHUNK_SIZE):
                        await f.write(chunk)

                LOGGER.debug(f"Successfully downloaded file to {path}")
                return DownloadResult(success=True, file_path=path)

        except httpx.TooManyRedirects:
            error_msg = f"Too many redirects while downloading {url}"
            LOGGER.error(error_msg)
            return DownloadResult(success=False, error=error_msg)
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error {e.response.status_code} for {url}"
            LOGGER.error(error_msg)
            return DownloadResult(success=False, error=error_msg)
        except httpx.RequestError as e:
            error_msg = f"Request failed for {url}: {str(e)}"
            LOGGER.error(error_msg)
            return DownloadResult(success=False, error=error_msg)
        except Exception as e:
            error_msg = f"Unexpected error downloading {url}: {str(e)}"
            LOGGER.error(error_msg)
            return DownloadResult(success=False, error=error_msg)

    async def make_request(
            self,
            url: str,
            max_retries: int = MAX_RETRIES,
            backoff_factor: float = BACKOFF_FACTOR,
            **kwargs: Any
    ) -> Optional[dict[str, Any]]:
        """
        Make an HTTP GET request with retries and exponential backoff.

        Args:
            url: URL to request
            max_retries: Maximum number of retry attempts
            backoff_factor: Base delay for exponential backoff
            kwargs: Additional arguments to pass to httpx

        Returns:
            Parsed JSON response as dict if successful, None otherwise
        """
        if not url:
            LOGGER.warning("Empty URL provided")
            return None

        headers = kwargs.pop('headers', {})
        if config.API_URL and url.startswith(config.API_URL):
            headers["X-API-Key"] = API_KEY

        for attempt in range(max_retries):
            try:
                response = await self._session.get(
                    url,
                    headers=headers,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()

            except httpx.TooManyRedirects:
                error_msg = f"Redirect loop for {url}"
                if attempt == max_retries - 1:
                    LOGGER.error(error_msg)
                    return None
                LOGGER.warning(error_msg)

            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP error {e.response.status_code} for {url}"
                if attempt == max_retries - 1:
                    LOGGER.error(error_msg)
                    return None
                LOGGER.warning(error_msg)

            except httpx.RequestError as e:
                error_msg = f"Request failed for {url}: {str(e)}"
                if attempt == max_retries - 1:
                    LOGGER.error(error_msg)
                    return None
                LOGGER.warning(error_msg)

            except ValueError as e:
                LOGGER.error(f"Invalid JSON response from {url}: {str(e)}")
                return None

            except Exception as e:
                LOGGER.error(f"Unexpected error for {url}: {str(e)}")
                return None

            # Exponential backoff
            await asyncio.sleep(backoff_factor * (2 ** attempt))

        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
