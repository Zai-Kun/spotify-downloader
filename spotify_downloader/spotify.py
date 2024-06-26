import asyncio
import atexit
import json
import os
from typing import Any, AsyncGenerator

import aiohttp
import eyed3
from eyed3.id3.frames import ImageFrame
from pathvalidate import sanitize_filename

from .utils.logger import get_logger

SPOTIFY_API = "https://api.spotifydown.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Referer": "https://spotifydown.com/",
    "Origin": "https://spotifydown.com",
}

logger = get_logger(name="spotify")


class Utils:
    @staticmethod
    def extract_id_from_url(url: str) -> str:
        return url.split("/")[-1].split("?")[0]


class Track:
    def __init__(self, track: dict[str, Any], session: aiohttp.ClientSession) -> None:
        self.id = track["id"]
        self.title = track["title"]
        self.cover = track["cover"]
        self.album = track["album"]
        self.artists = (
            ", ".join(track["artists"])
            if isinstance(track["artists"], list)
            else track["artists"]
        )
        self.release_date = track["releaseDate"]
        self.download_url = f"{SPOTIFY_API}/download/{self.id}"

        self._session = session

    async def fetch_stream_url(self) -> str:
        async with self._session.get(self.download_url, headers=HEADERS) as resp:
            decoded_json = json.loads(await resp.text())
            if not decoded_json["success"]:
                raise RuntimeError(
                    f"An unexpected error occured. Server response:\n{decoded_json}"
                )

            return decoded_json["link"]

    async def download(self) -> AsyncGenerator[bytes, None]:
        download_link = await self.fetch_stream_url()
        async with self._session.get(download_link, headers=HEADERS) as resp:
            if resp.status == 200:
                async for chunk in resp.content.iter_any():
                    yield chunk
            else:
                RuntimeError(
                    f"An unexpected error occured. Server response:\n{await resp.text()}"
                )

    async def save_to(
        self, folder_path: str, sema: asyncio.BoundedSemaphore | None = None
    ):
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        file_path = os.path.join(folder_path, sanitize_filename(self.title + ".mp3"))

        if os.path.exists(file_path):
            logger.warning(f"{self.title} already exists, skipping")
            return

        async def _save_to_file():
            logger.info(f"Downloading: {self.title}")
            image_task = asyncio.create_task(self.fetch_covor_image())

            with open(file_path, "wb") as f:
                async for chunk in self.download():
                    f.write(chunk)
                image = await image_task
                self.embed_track_info_to_mp3(file_path, image)

        if sema is None:
            await _save_to_file()
        else:
            async with sema:
                await _save_to_file()
        logger.info(f"Done downloading: {self.title}")

    async def fetch_covor_image(self) -> bytes:
        async with self._session.get(self.cover, headers=HEADERS) as resp:
            return await resp.read()

    def embed_track_info_to_mp3(self, mp3_path: str, image: bytes):
        audiofile = eyed3.load(mp3_path)
        if audiofile is None:
            raise RuntimeError("Failed to load mp3 file.")

        if audiofile.tag is None:
            audiofile.initTag()
        if audiofile.tag is None:
            raise RuntimeError("tag is None somehow")

        audiofile.tag.images.set(ImageFrame.FRONT_COVER, image, "image/jpeg")
        audiofile.tag.artist = self.artists
        audiofile.tag.album = self.album
        audiofile.tag.title = self.title
        audiofile.tag.save()


class Playlist:
    def __init__(
        self, playlist_metadata: dict[str, Any], session: aiohttp.ClientSession
    ) -> None:
        self.id = playlist_metadata["id"]
        self.title = playlist_metadata["title"]
        self.artists = (
            ", ".join(playlist_metadata["artists"])
            if isinstance(playlist_metadata["artists"], list)
            else playlist_metadata["artists"]
        )
        self.cover = playlist_metadata["cover"]

        self._session = session

    async def fetch_all_tracks(self) -> AsyncGenerator[Track, None]:
        offset = 0

        while True:
            async with self._session.get(
                f"{SPOTIFY_API}/trackList/playlist/{self.id}?offset={offset}",
                headers=HEADERS,
            ) as resp:
                decoded_json = json.loads(await resp.text())
                if not decoded_json["success"]:
                    raise RuntimeError(
                        f"An unexpected error occured. Server response:\n{decoded_json}"
                    )
                for track in decoded_json["trackList"]:
                    yield Track(track, self._session)

                if decoded_json["nextOffset"] is None:
                    break

                offset = decoded_json["nextOffset"]


class SpotifyDownloader:
    def __init__(self) -> None:
        self._session = aiohttp.ClientSession()
        atexit.register(self.close_session)

    async def fetch_track(self, track_url: str) -> Track:
        track_id = Utils.extract_id_from_url(track_url)
        async with self._session.get(
            f"{SPOTIFY_API}/metadata/track/{track_id}",
            headers=HEADERS,
        ) as resp:
            decoded_json = json.loads(await resp.text())
            if not decoded_json["success"]:
                raise RuntimeError(
                    f"An unexpected error occured. Server response:\n{decoded_json}"
                )
            return Track(decoded_json, self._session)

    async def fetch_playlist(self, playlist_url: str) -> Playlist:
        playlist_id = Utils.extract_id_from_url(playlist_url)
        async with self._session.get(
            f"{SPOTIFY_API}/metadata/playlist/{playlist_id}",
            headers=HEADERS,
        ) as resp:
            decoded_json = json.loads(await resp.text())
            if not decoded_json["success"]:
                raise RuntimeError(
                    f"An unexpected error occured. Server response:\n{decoded_json}"
                )
            decoded_json["id"] = playlist_id
            return Playlist(decoded_json, self._session)

    def close_session(self):
        if self._session is not None:
            asyncio.run(self._session.close())
