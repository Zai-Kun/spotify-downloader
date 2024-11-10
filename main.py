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
    while True:
        await SpotifyDownloader()  # Awaiting initialization if it's an async function

if __name__ == "__main__":
    asyncio.run(main())