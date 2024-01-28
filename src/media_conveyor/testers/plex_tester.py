import datetime
import json
import os
import random
import time
import timeit
from pathlib import Path
from pprint import pprint

from plexapi.server import PlexServer

from ..authentication import PlexAuthentication
from ..logging import setup_logger
from ..plex_data import PlexData


def main():
    start_time = time.time()

    plex_auth = PlexAuthentication()
    plex_data = PlexData(plex_auth.baseurl, plex_auth.token)
    plex_db = plex_data.compile_libraries(shows=True, title_filter="Light and Dark")
    # plex_db = plex_data.compile_libraries(shows=True, title_filter="Cunk on Britain")
    # plex_db = plex_data.compile_libraries(movies=True, title_filter="The Matrix")
    # plex_db = plex_data.compile_libraries(movies=True, db_slice=slice(2447, 2449))
    # plex_db = plex_data.compile_libraries(shows=True, db_slice=slice(1050, 1051))
    # plex_db = plex_data.compile_libraries(movies=True, db_slice=slice(2050, 2051))
    # plex_db = plex_data.compile_libraries(artists=True, db_slice=slice(456, 457))
    # print(plex_data._shows_sections)
    # for section in plex_data._shows_sections:
    #     print(section.title)
    #     print(section.all())
    # shows = plex_data._shows()

    # shows_db = plex_data.get_shows_db
    # for show in shows_db:
    #     print(show)

    print(plex_db)

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Time taken: {elapsed_time} seconds")


def plex_test():
    plex_auth = PlexAuthentication()
    plex = PlexServer(baseurl=plex_auth.baseurl, token=plex_auth.token)
    shows = plex.library.section("TV Shows").search(title="Game of Thrones")
    # shows = plex.library.section("TV Shows").search(resolution="4k", limit=5, maxresults=5)
    # shows = plex.library.search(resolution="4k", limit=5)
    for show in shows:
        print(show.title)
        for season in show.seasons():
            print(season.title)
            for episode in season.episodes():
                print(episode.title)
