from __future__ import annotations

import json
import os
import re
from enum import Enum
from pathlib import Path

from plexapi.exceptions import BadRequest, NotFound
from plexapi.server import PlexServer

from .logging import setup_logger

logger = setup_logger()


class MediaType(Enum):
    MOVIE = "movie"
    ARTIST = "artist"
    SHOW = "show"


class PlexData(PlexServer):
    NON_ALPHANUMERIC = re.compile(r"[^a-zA-Z0-9]")

    def __init__(self, baseurl=None, token=None, session=None, timeout=None):
        self.local_media_path = os.getenv("PATHS_LOCAL_MEDIA")
        self._movies_db = None
        self._shows_db = None
        self._artists_db = None  # Add this line
        super().__init__(baseurl, token, session, timeout)
        self._movie_sections = self._get_sections(MediaType.MOVIE)
        self._shows_sections = self._get_sections(MediaType.SHOW)
        self._artist_sections = self._get_sections(MediaType.ARTIST)
        logger.info("PlexData initialized successfully")

    def handle_exceptions(func):  # noqa: N805
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except BadRequest as e:
                logger.error(f"Failed to execute {func.__name__} due to bad request: {e}")
                raise
            except NotFound as e:
                logger.error(f"Failed to execute {func.__name__} due to resource not found: {e}")
                raise
            except Exception as e:
                logger.critical(f"Failed to execute {func.__name__} due to unexpected error: {e}")
                raise

        return wrapper

    @handle_exceptions
    def _get_sections(self, section_type: MediaType):
        sections = [
            section for section in self.library.sections() if section.type == section_type.value
        ]
        return sections

    def _movies(self) -> list:
        movies = [movie for section in self._movie_sections for movie in section.all()]
        logger.info(f"Retrieved {len(movies)} movies")
        return movies

    def _shows(self) -> dict:
        shows_dict = {section.title: list(section.all()) for section in self._shows_sections}
        logger.info(f"Retrieved {sum(len(shows) for shows in shows_dict.values())} shows")
        return shows_dict

    def _artists(self) -> list:
        artists = [artist for section in self._artist_sections for artist in section.all()]
        logger.info(f"Retrieved {len(artists)} artists")
        return artists

    def _process_movie_data(self, data):
        year = data.year or "empty"
        files = json.dumps(self._get_file_data(data.media) if data.media else "empty")
        return year, files

    def _process_artist_data(self, data):
        # Assuming that the artist data does not have year and files information
        # Return "empty" for these values
        return ("empty", "empty")

    def _process_show_data(self, data):
        year = data.year or "empty"
        return (year,)

    def _process_data(self, data=None, media_type: MediaType = None) -> tuple:
        title = data.title or "empty"
        name = self.NON_ALPHANUMERIC.sub("", title).strip()
        thumb = data.thumb or "empty"

        process_data_functions = {
            MediaType.MOVIE: self._process_movie_data,
            MediaType.ARTIST: self._process_artist_data,
            MediaType.SHOW: self._process_show_data,
        }

        if media_type in process_data_functions:
            extra_data = process_data_functions[media_type](data)
            return title, thumb, name, *extra_data

        raise ValueError(f"Unknown media type: {media_type}")

    def _get_file_data(self, media):
        file_data = {}
        for m in media:
            parts = m.parts
            for part in parts:
                fixed_file_path = part.file.replace("/media", self.local_media_path, 1)
                file_data[fixed_file_path] = part.size
        return file_data

    @property
    def get_movies_db(self) -> dict:
        if self._movies_db is None:
            self._movies_db = {}
            for movie in self._movies():
                movie_title, movie_thumb, movie_name, movie_year, movie_paths = self._process_data(
                    movie,
                    media_type=MediaType.MOVIE,
                )
                db = {
                    "title": movie_title,
                    "year": movie_year,
                    "file_path": movie_paths,
                    "thumb_path": movie_thumb,
                }
                self._movies_db[f"movie:{movie_name}:{movie_year}"] = db
            logger.info("Generated movies database")
            return self._movies_db

    @property
    def get_shows_db(self) -> dict:
        if self._shows_db is None:
            self._shows_db = {}
            for section_title, shows in self._shows().items():
                section_name = section_title.lower().replace(" ", "_")
                for show in shows:
                    show_title, show_thumb, show_name, show_year = self._process_data(
                        show, media_type=MediaType.SHOW
                    )

                    episodes = self._get_episodes(show)
                    serialized_episodes = json.dumps(episodes)

                    db = {
                        "title": show_title,
                        "year": show_year,
                        "thumb_path": show_thumb,
                        "episodes": serialized_episodes,
                    }

                    self._shows_db[f"{section_name}:{show_name}:{show.year}"] = db
            logger.info("Generated Shows database")
            return self._shows_db

    @handle_exceptions
    def _get_episodes(self, show) -> dict:
        if show and show.seasons():
            episode_dict = {}
            for season in show.seasons():
                episode_dict[f"season:{season.seasonNumber}"] = {}
                for episode in season.episodes():
                    episode_media = episode.media or "empty"
                    try:
                        episode_files = json.dumps(self._get_file_data(episode_media))
                    except Exception as e:
                        logger.error(
                            f"Failed to get file data for episode {episode.episodeNumber} of season {season.seasonNumber} for show {show.title}: {e}"
                        )
                        continue
                    episode_dict[f"season:{season.seasonNumber}"][
                        f"episode:{episode.episodeNumber}"
                    ] = {
                        "episode_name": episode.title,
                        "episode_files": episode_files,
                    }
            return episode_dict
        else:
            return {}

    @property
    def get_artists_db(self) -> dict:
        if self._artists_db is None:
            self._artists_db = {}
            for artist in self._artists():
                artist_name, artist_thumb, artist_title, _, _ = self._process_data(
                    artist, media_type=MediaType.ARTIST
                )
                db = {
                    "artist": artist_title,
                    "thumb": artist_thumb,
                    "tracks": json.dumps(self._get_tracks(artist)),
                }
                self._artists_db[f"artist:{artist_name}"] = db
            logger.info("Generated artists database")
            logger.info(f"Size of database: {len(self._artists_db)}")
            return self._artists_db

    @handle_exceptions
    def _get_tracks(self, artist) -> dict:
        if artist and artist.albums():
            album_dict = {}
            for album in artist.albums():
                album_dict[f"album:{album.title}:{album.year}"] = {}
                for track in album.tracks():
                    track_number = track.trackNumber or "empty"
                    track_name = track.title or "empty"
                    try:
                        track_files = json.dumps(self._get_file_data(track.media))
                    except Exception as e:
                        logger.error(
                            f"Failed to get file data for track {track_number} of album {album.title} for artist {artist.title}: {e}"
                        )
                        continue
                    album_dict[f"album:{album.title}:{album.year}"][f"track:{track_number}"] = {
                        "track_name": track_name,
                        "track_files": track_files,
                    }
            return album_dict
        else:
            return {}

    def search(self, query, libtype=None, **kwargs):
        """
        Search for a specific item in the Plex library.

        Parameters:
        query (str): The search query.
        libtype (str, optional): The type of library to search in. Defaults to None.
        **kwargs: Additional keyword arguments for the search function.

        Returns:
        list: A list of matching items from the Plex library.
        """
        return self.library.search(query, libtype, **kwargs)

    def compile_libraries(
        self,
        movies=False,
        artists=False,
        shows=False,
        db_slice: slice = None,
        title_filter: str = "",
    ) -> dict:
        libraries_db = {}

        def add_to_library(media_type_db):
            if db_slice:
                libraries_db.update(
                    {
                        k: media_type_db[k]
                        for k in list(media_type_db.keys())[db_slice]
                        if title_filter in media_type_db[k]["title"]
                    }
                )
            else:
                libraries_db.update(
                    {k: v for k, v in media_type_db.items() if title_filter in v["title"]}
                )

        if movies:
            add_to_library(self.get_movies_db)
        if artists:
            add_to_library(self.get_artists_db)
        if shows:
            add_to_library(self.get_shows_db)

        logger.info("Libraries packaged")
        return libraries_db
