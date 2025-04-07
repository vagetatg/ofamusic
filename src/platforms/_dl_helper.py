#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.


import asyncio
import os
import random
import subprocess
from pathlib import Path
from typing import Optional

import aiofiles
from Crypto.Cipher import AES
from Crypto.Util import Counter
from yt_dlp import YoutubeDL, utils

import config
from config import DOWNLOADS_DIR, PROXY_URL
from src.logger import LOGGER
from ._httpx import HttpxClient
from .dataclass import TrackInfo


class YouTubeDownload:
    def __init__(self, track: TrackInfo):
        """
        Initialize the YouTubeDownload class with a video ID.
        """
        self.track = track
        self.video_url = f"https://www.youtube.com/watch?v={self.track.tc}"
        self.client = HttpxClient(max_redirects=1)

    @staticmethod
    async def _get_cookie_file():
        cookie_dir = "cookies"
        try:
            if not os.path.exists(cookie_dir):
                LOGGER.warning(f"Cookie directory '{cookie_dir}' does not exist.")
                return None

            files = await asyncio.to_thread(os.listdir, cookie_dir)
            cookies_files = [f for f in files if f.endswith(".txt")]

            if not cookies_files:
                LOGGER.warning(f"No cookie files found in '{cookie_dir}'.")
                return None

            random_file = random.choice(cookies_files)
            return os.path.join(cookie_dir, random_file)
        except Exception as e:
            LOGGER.warning(f"Error accessing cookie directory: {e}")
            return None

    async def process(self) -> Optional[str]:
        """Download the audio from YouTube and return the path to the downloaded file."""
        try:
            existing_files = list(Path(DOWNLOADS_DIR).glob(f"{self.track.tc}.*"))
            if existing_files:
                return str(existing_files[0])

            if config.API_URL and config.API_KEY:
                if file_path := await self._download_with_api():
                    return file_path

            return await self._download_with_yt_dlp()
        except Exception as e:
            LOGGER.error(f"Unexpected error in download process: {e}", exc_info=True)
            return None

    async def _download_with_yt_dlp(self) -> Optional[str]:
        """Download audio using yt-dlp with proxy and cookie support."""
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "outtmpl": str(Path(DOWNLOADS_DIR) / f"{self.track.tc}.%(ext)s"),
            "geo_bypass": True,
            "nocheckcertificate": True,
            "quiet": True,
            "no_warnings": True,
        }

        if cookie_file := await self._get_cookie_file():
            ydl_opts["cookiefile"] = cookie_file

        if PROXY_URL:
            ydl_opts["proxy"] = PROXY_URL

        try:
            loop = asyncio.get_running_loop()
            with YoutubeDL(ydl_opts) as ydl:
                await loop.run_in_executor(None, ydl.download, [self.video_url])
            downloaded_files = list(Path(DOWNLOADS_DIR).glob(f"{self.track.tc}.*"))
            if downloaded_files:
                return str(downloaded_files[0])
            LOGGER.warning("❌ yt-dlp finished, but no file found.")
            return None
        except utils.DownloadError as e:
            LOGGER.error(f"❌ Download error for {self.video_url}: {e}")
            return None
        except Exception as e:
            LOGGER.error(f"❌ Unexpected error downloading {self.video_url}: {e}")
            return None

    async def _download_with_api(self) -> Optional[Path]:
        """Attempt to download from external API if available."""
        _api_url = f"{config.API_URL}/yt?id={self.track.tc}"
        data = await self.client.make_request(_api_url)
        if not data or "results" not in data:
            LOGGER.warning("❌ API response invalid or missing results.")
            return None

        results = data["results"]
        audios = results.get("audios")
        if not audios:
            LOGGER.warning("❌ No audio entries found in API response.")
            return None

        webm_audios = [a for a in audios if a.get("ext") == "webm"]
        best_audio = webm_audios[-1] if webm_audios else audios[-1]

        dl_url = best_audio.get("url")
        ext = best_audio.get("ext", "webm")

        if not dl_url:
            LOGGER.warning("❌ No download URL in API response.")
            return None

        self.output_file = Path(DOWNLOADS_DIR) / f"{self.track.tc}.{ext}"
        dl = await self.client.download_file(dl_url, self.output_file)
        if dl.success:
            LOGGER.info(f"✅ Downloaded via API: {self.output_file}")
            return dl.file_path
        else:
            LOGGER.warning(f"❌ API download failed for: {self.track.tc}")
            return None


async def rebuild_ogg(filename: str) -> None:
    """Fixes broken OGG headers."""
    if not os.path.exists(filename):
        LOGGER.error(f"❌ Error: {filename} not found.")
        return

    try:
        async with aiofiles.open(filename, "r+b") as ogg_file:
            ogg_s = b"OggS"
            zeroes = b"\x00" * 10
            vorbis_start = b"\x01\x1e\x01vorbis"
            channels = b"\x02"
            sample_rate = b"\x44\xac\x00\x00"
            bit_rate = b"\x00\xe2\x04\x00"
            packet_sizes = b"\xb8\x01"

            await ogg_file.seek(0)
            await ogg_file.write(ogg_s)
            await ogg_file.seek(6)
            await ogg_file.write(zeroes)
            await ogg_file.seek(26)
            await ogg_file.write(vorbis_start)
            await ogg_file.seek(39)
            await ogg_file.write(channels)
            await ogg_file.seek(40)
            await ogg_file.write(sample_rate)
            await ogg_file.seek(48)
            await ogg_file.write(bit_rate)
            await ogg_file.seek(56)
            await ogg_file.write(packet_sizes)
            await ogg_file.seek(58)
            await ogg_file.write(ogg_s)
            await ogg_file.seek(62)
            await ogg_file.write(zeroes)
    except Exception as e:
        LOGGER.error(f"Error rebuilding OGG file {filename}: {e}")


class SpotifyDownload:
    def __init__(self, track: TrackInfo):
        self.track = track
        self.client = HttpxClient()
        self.encrypted_file = os.path.join(DOWNLOADS_DIR, f"{track.tc}.encrypted.ogg")
        self.decrypted_file = os.path.join(DOWNLOADS_DIR, f"{track.tc}.decrypted.ogg")
        self.output_file = os.path.join(DOWNLOADS_DIR, f"{track.tc}.ogg")

    async def decrypt_audio(self) -> None:
        """Decrypt the downloaded audio file using a stream-based approach."""
        try:
            key = bytes.fromhex(self.track.key)
            iv = bytes.fromhex("72e067fbddcbcf77ebe8bc643f630d93")
            iv_int = int.from_bytes(iv, "big")
            cipher = AES.new(
                key, AES.MODE_CTR, counter=Counter.new(128, initial_value=iv_int)
            )

            chunk_size = 8192  # 8KB chunks
            async with aiofiles.open(self.encrypted_file, "rb") as fin, aiofiles.open(
                    self.decrypted_file, "wb"
            ) as fout:
                while chunk := await fin.read(chunk_size):
                    decrypted_chunk = cipher.decrypt(chunk)
                    await fout.write(decrypted_chunk)
        except Exception as e:
            LOGGER.error(f"Error decrypting audio file: {e}")
            raise

    async def fix_audio(self) -> None:
        """Fix the decrypted audio file using FFmpeg."""
        try:
            process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-i",
                self.decrypted_file,
                "-c",
                "copy",
                self.output_file,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                LOGGER.error(f"FFmpeg error: {stderr.decode().strip()}")
                raise subprocess.CalledProcessError(process.returncode, "ffmpeg")
        except Exception as e:
            LOGGER.error(f"Error fixing audio file: {e}")
            raise

    async def _cleanup(self) -> None:
        """Cleanup temporary files asynchronously."""
        for file in [self.encrypted_file, self.decrypted_file]:
            try:
                if os.path.exists(file):
                    os.remove(file)
            except Exception as e:
                LOGGER.warning(f"Error removing {file}: {e}")

    async def process(self) -> Optional[str]:
        """Main function to download, decrypt, and fix audio."""
        if os.path.exists(self.output_file):
            LOGGER.info(f"✅ Found existing file: {self.output_file}")
            return self.output_file

        _track_id = self.track.tc
        if not self.track.cdnurl or not self.track.key:
            LOGGER.warning(f"Missing CDN URL or key for track: {_track_id}")
            return None

        try:
            await self.client.download_file(self.track.cdnurl, self.encrypted_file)
            await self.decrypt_audio()
            await rebuild_ogg(self.decrypted_file)
            await self.fix_audio()
            await self._cleanup()
            LOGGER.info(f"✅ Successfully processed track: {self.output_file}")
            return self.output_file
        except Exception as e:
            LOGGER.error(f"Error processing track {_track_id}: {e}")
            await self._cleanup()
            return None
