import datetime
import os
import random
import time
import timeit
from pathlib import Path
from pprint import pprint

import json5 as json
from plexapi.server import PlexServer

from ..authentication import PlexAuthentication
from ..plex_data import PlexData

# from .plex_data import PlexMovies

# TODO Temporarily setting the environment variable here for dev purposes
# os.environ["MEDIA_CONVEYOR"] = f"{Path.home()}/.media_conveyor"

cwd = os.getcwd()

# logger = logging.getLogger(__name__)

print(os.getenv("MEDIA_CONVEYOR"))
plex_auth = PlexAuthentication()
plex_data = PlexData(plex_auth.baseurl, plex_auth.token)

random.seed(444)
hats = {
    f"hat:{random.getrandbits(32)}": i
    for i in (
        {
            "color": "black",
            "price": 49.99,
            "style": "fitted",
            "quantity": 1000,
            "npurchased": 0,
        },
        {
            "color": "maroon",
            "price": 59.99,
            "style": "hipster",
            "quantity": 500,
            "npurchased": 0,
        },
        {
            "color": "green",
            "price": 99.99,
            "style": "baseball",
            "quantity": 200,
            "npurchased": 0,
        },
    )
}


def get_db():
    # movies = plex_data.movies_db()
    # shows = plex_data.shows_db()
    # music = plex_data.music_db()
    print("Finished")


def main():
    plex_auth = PlexAuthentication()
    PlexData(plex_auth.baseurl, plex_auth.token)

    # db = plex_data.package_libraries(shows=False, music=False)
    # db = plex_data.package_libraries(movies=True)
    # for key, movie_dict in movies.items():
    for key, movie_dict in list(hats.items())[:5]:
        print(type(key), type(movie_dict))
        print(key)
        pprint(movie_dict)

    # json_object = json.dumps(db, indent=4)

    # print(json_object)

    # pprint(db)
    # for key_id, value_data in db.items():
    #     print(f"{key_id}")
    #     pprint(value_data)
    #     print("\n")

    # excecution_time = timeit.timeit(get_db(), number=1)
    # print(f"Execution Time: {excecution_time}")

    # plex_data.movies_db()
    # shows = plex_data.shows_db()
    # music = plex_data.music_db()
    # for key, value in music.items():
    #     print(key, value)

    # for section in plex_server.library.sections():
    #     if section.type == "artist":
    #         # print(section)
    #         # artist = section.all()
    #         # print(type(movies))
    #         for music in section.all():
    #             # print(movie)
    #             print(music.title)
    #             for album in music.albums():
    #                 print(f"  {album.title} {album.year}")
    #                 for track in album.tracks():
    #                     print(f"    {track.trackNumber}. {track.title}")
    # print(type(plex.library.section("Movies").all()))
    # for movie in plex.library.section("Movies").all():
    #     print(type(movie))

    # def get_episodes(show):
    #     episode_db = {}
    #     for season in show.seasons():
    #         for episode in season.episodes():
    #             episode_db[f"season {season.seasonNumber}"] = {
    #                 "episode_number": episode.episodeNumber,
    #                 "episode_name": episode.title,
    #                 "episode_location": episode.locations,
    #             }
    #     return episode_db

    # for tv_show in plex.library.section("TV Shows").all():
    #     if tv_show.title == "Mad Men":
    # print(f"Title: {tv_show.title}\nYear: {tv_show.year}")
    # for season in tv_show.seasons():
    #     for episode in season.episodes():
    #         print(
    #             f"   S{season.seasonNumber}E{episode.episodeNumber} - {episode.title}\n{episode.locations}"
    #         )
    # print("\n")

    # converted = json.dumps(get_episodes(tv_show))
    # print(converted)
    # print(type(converted))
    # reconverted = json.loads(converted)
    # print(reconverted)
    # print(type(reconverted))

    # Specify the file path

    # file_path = Path(cwd, "data.json")
    # print(file_path)

    # # Write data to the JSON file
    # with open(file_path, "w") as json_file:
    #     json.dump(db, json_file, indent=4)
