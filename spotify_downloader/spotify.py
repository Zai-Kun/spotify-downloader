import asyncio
import json
import os
from typing import Any

import aiohttp
import eyed3
from eyed3.id3.frames import ImageFrame
from pathvalidate import sanitize_filename

SPOTIFY_API = "https://api.fabdl.com"

with open("config.json") as config_file:
    config = json.load(config_file)
DOWNLOAD_DIR = config.get("download_path", "./downloads")


class Utils:
    @staticmethod
    def extract_id_from_url(url: str) -> str:
        return url.split("/")[-1].split("?")[0]


async def fetch_playlist_data():
    user_input = input("Enter your Spotify playlist or track link: ")
    
    if "/track/" in user_input:
        # Handle single track
        song_id = Utils.extract_id_from_url(user_input)
        await download_single_track(song_id)
    elif "/playlist/" in user_input:
        # Handle playlist
        playlist_url = f"{SPOTIFY_API}/spotify/get?url={user_input}"
        async with aiohttp.ClientSession() as session:
            async with session.get(playlist_url) as response:
                data = await response.json()

                for track in data["result"]["tracks"]:
                    song_id = track['id']
                    song_name = track['name']
                    artist_name = track['artists']
                    await get_gid(session, song_id, song_name, artist_name)
    else:
        print("Invalid Spotify link. Please provide a valid track or playlist URL.")


async def download_single_track(song_id: str):
    async with aiohttp.ClientSession() as session:
        track_url = f"{SPOTIFY_API}/spotify/get?url=https://open.spotify.com/track/{song_id}"
        async with session.get(track_url) as response:
            data = await response.json()
            if 'result' not in data:
                print("Error: Could not retrieve track information.")
                return

            song_name = data['result'].get('name', 'Unknown Song')
            artist_name = data['result'].get('artists', 'Unknown Artist')
            gid = data['result'].get('gid')
            cover_url = data['result'].get('cover_url')

            if gid:
                await get_download_link(session, gid, song_id, song_name, artist_name, cover_url)


async def get_gid(session: aiohttp.ClientSession, song_id: str, song_name: str, artist_name: str) -> None:
    url = f"{SPOTIFY_API}/spotify/get?url=https://open.spotify.com/track/{song_id}"

    try:
        async with session.get(url) as response:
            data = await response.json()

            if 'result' not in data or 'gid' not in data['result']:
                print(f"Missing necessary data for {song_name} by {artist_name}, skipping.")
                return

            gid = data['result']['gid']
            cover_url = data['result'].get('cover_url')
            await get_download_link(session, gid, song_id, song_name, artist_name, cover_url)

    except aiohttp.ClientError as e:
        print(f"Error retrieving data for {song_name} by {artist_name}: {e}")

    except Exception as e:
        print(f"Unexpected error for {song_name} by {artist_name}: {e}")


async def get_download_link(session: aiohttp.ClientSession, gid: str, track_id: str, song_name: str, artist_name: str, cover_url: str) -> None:
    url = f"{SPOTIFY_API}/spotify/mp3-convert-task/{gid}/{track_id}"

    try:
        async with session.get(url) as response:
            data: dict[str, Any] = await response.json()

            if 'result' not in data or 'download_url' not in data['result']:
                print(f"Missing 'download_url' for {song_name} by {artist_name}, skipping.")
                return

            download_url = f"{SPOTIFY_API}{data['result']['download_url']}/"
            await download_song(session, download_url, song_name, artist_name, cover_url)

    except aiohttp.ClientError as e:
        print(f"Error retrieving download link for {song_name} by {artist_name}: {e}")

    except Exception as e:
        print(f"Unexpected error for {song_name} by {artist_name}: {e}")


async def download_song(session: aiohttp.ClientSession, url: str, song_name: str, artist_name: str, cover_url: str) -> None:
    try:
        async with session.get(url) as response:
            if response.status == 200:
                filename = f"{song_name} - {artist_name}.mp3"
                
                if not os.path.exists(DOWNLOAD_DIR):
                    os.makedirs(DOWNLOAD_DIR)

                file_path = os.path.join(DOWNLOAD_DIR, sanitize_filename(filename))

                if os.path.exists(file_path):
                    print(f"{filename} already exists, skipping.")
                    return

                with open(file_path, 'wb') as f:
                    async for chunk in response.content.iter_any():
                        f.write(chunk)

                await embed_metadata(file_path, song_name, artist_name, cover_url, session)

            else:
                print(f"Failed to download {song_name} by {artist_name}: Status {response.status}")

    except aiohttp.ClientError as e:
        print(f"Failed to download {song_name} by {artist_name}: {e}")

    except Exception as e:
        print(f"Unexpected error downloading {song_name} by {artist_name}: {e}")


async def embed_metadata(mp3_path: str, song_name: str, artist_name: str, cover_url: str, session: aiohttp.ClientSession) -> None:
    try:
        audiofile = eyed3.load(mp3_path)
        if audiofile is None:
            raise RuntimeError("Failed to load mp3 file.")

        if audiofile.tag is None:
            audiofile.initTag()

        audiofile.tag.artist = artist_name
        audiofile.tag.title = song_name

        if cover_url:
            async with session.get(cover_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    audiofile.tag.images.set(
                        ImageFrame.FRONT_COVER, image_data, "image/jpeg"
                    )

        audiofile.tag.save()

        print(f"Metadata saved for {song_name} by {artist_name}")

    except Exception as e:
        print(f"Error embedding metadata for {song_name} by {artist_name}: {e}")


async def SpotifyDownloader():
    await fetch_playlist_data()


if __name__ == "__main__":
    asyncio.run(SpotifyDownloader())