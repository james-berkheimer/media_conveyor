import os
import random
from pathlib import Path
from pprint import pprint

import json5 as json
import redis
from plexapi.server import PlexServer

from .authentication import PlexAuthentication
from .plex_data import PlexData
from .redis_db import RedisPlexDB

# TODO Temporarily setting the environment variable here for dev purposes
os.environ["MEDIA_CONVEYOR"] = f"{Path.home()}/.media_conveyor"

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


def test(plex_data):
    # movies = plex_data.movies_db
    movies = plex_data.package_libraries(movies=True)
    # pprint(movies.keys())
    # print(len(movies.keys()))

    with r.pipeline() as pipe:
        for movie_key, movie_dict in list(movies.items())[3413:3416]:
            # for movie_key, movie_dict in movies.items():
            print(movie_key)
            pprint(movie_dict)
            pipe.hmset(movie_key, movie_dict)
        pipe.execute()
    r.bgsave()


def main():
    plex_auth = PlexAuthentication()
    plex_data = PlexData(plex_auth.baseurl, plex_auth.token)
    redis_db = RedisPlexDB(plex_data.package_libraries(movies=True))
    redis_db.make_db()

    # test(plex_data)


def test_db():
    print(r.keys())
    # pprint(r.hgetall("movie:346317923"))
    # pprint(r.hget)
