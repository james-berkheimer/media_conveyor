import os
import random
import time
from pathlib import Path
from pprint import pprint

import json5 as json
import redis
from plexapi.server import PlexServer

from .authentication import PlexAuthentication
from .plex_data import PlexData
from .redis_db import RedisPlexDB
from .utils import setup_logger

# TODO Temporarily setting the environment variable here for dev purposes
# os.environ["MEDIA_CONVEYOR"] = f"{Path.home()}/.media_conveyor"


def test_db():
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    plex_auth = PlexAuthentication()
    plex_data = PlexData(plex_auth.baseurl, plex_auth.token)
    # movies = plex_data.movies_db

    # shows = plex_data._shows()
    # for show in shows[100:105]:
    #     print(show.title)
    #     for season in show.seasons():
    #         print(f"   Season: {season.seasonNumber}")
    #         for episode in season.episodes():
    #             print(f"      Episode: {episode.title}")
    #             file_path = Path(episode.locations[0])
    #             print(f"      Location: {file_path.stem}")
    #             print(f"      Media: {episode.media[0].parts[0].file}\n")

    # print(f"      File: {episode.media[0].parts[0].file}\n")
    # print(f"      File: {episode.media[0].parts[0].file}\n")

    start_time = time.time()
    # db = plex_data.compile_libraries(movies=True)
    # db = plex_data.compile_libraries(shows=True)
    db = plex_data.compile_libraries(movies=True, shows=True, music=True)
    start_time = time.time()
    with r.pipeline() as pipe:
        # for key, value in db.items():
        for key, value in list(db.items())[100:105]:
            print(key)
            pprint(value)
            pipe.hmset(key, value)
            pipe.execute()
        r.bgsave()
    end_time = time.time()
    print(f"Execution time: {end_time - start_time} seconds")


def main():
    setup_logger(level="INFO")
    plex_auth = PlexAuthentication()
    plex_data = PlexData(plex_auth.baseurl, plex_auth.token)
    plex_db = json.dumps(plex_data.compile_libraries(movies=True))
    # pprint(plex_db)
    # redis_params = {"host": "localhost", "port": 6379, "db": 0}
    # redis_db = RedisPlexDB(plex_db, **redis_params)
    # redis_db.make_db()

    # test(plex_data)


def check_db():
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    print(r.keys())
    # pprint(r.hgetall("movie:346317923"))
    # pprint(r.hget)
