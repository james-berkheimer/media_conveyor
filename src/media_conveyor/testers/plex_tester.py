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
from ..logging import setup_logger
from ..plex_data import PlexData


def main():
    start_time = time.time()

    plex_auth = PlexAuthentication()
    plex_data = PlexData(plex_auth.baseurl, plex_auth.token)
    plex_db = plex_data.compile_libraries(movies=True, db_slice=slice(2430, 2470))
    # print(plex_data._shows_sections)
    # for section in plex_data._shows_sections:
    #     print(section.title)
    #     print(section.all())
    # shows = plex_data._shows()

    # shows_db = plex_data.get_shows_db
    # for show in shows_db:
    #     print(show)

    pprint(plex_db)

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Time taken: {elapsed_time} seconds")
