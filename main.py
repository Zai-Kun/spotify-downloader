import asyncio
import json
import os
import sys

from spotify_downloader import SpotifyDownloader

if not os.path.isfile(f"{os.path.realpath(os.path.dirname(__file__))}/config.json"):
    sys.exit("'config.json' not found! Please add it and try again.")
else:
    with open(f"{os.path.realpath(os.path.dirname(__file__))}/config.json") as file:
        config = json.load(file)

DOWNLOAD_PATH = config["download_path"]


def take_user_input() -> str:
    while True:
        user_input = input("Enter playlist link or song link: ")
        if not user_input.lower().startswith("https://open.spotify.com/"):
            print("Invalid link. Try again.")
            continue
        return user_input


def is_playlist(link: str) -> bool:
    return "playlist" in link


async def main():
    spotify_downloader = SpotifyDownloader()
    link = take_user_input()

    if is_playlist(link):
        sema = asyncio.BoundedSemaphore(2)
        tasks = []
        async for track in spotify_downloader.fetch_all_playlist_tracks(link):
            tasks.append(track.save_to(DOWNLOAD_PATH, sema))
        await asyncio.gather(*tasks)
        return

    track = await spotify_downloader.fetch_track(link)
    await track.save_to(DOWNLOAD_PATH)


if __name__ == "__main__":
    asyncio.run(main())
