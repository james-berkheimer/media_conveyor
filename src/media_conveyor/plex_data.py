from __future__ import annotations

# import json5 as json
import json
import logging
import re
from pathlib import Path

from plexapi.exceptions import BadRequest, NotFound
from plexapi.server import PlexServer

from .logging import setup_logger

logger = setup_logger()


class PlexData(PlexServer):
    NON_ALPHANUMERIC = re.compile(r"[^a-zA-Z0-9]")

    def __init__(self, baseurl=None, token=None, session=None, timeout=None):
        self._movies_db = None
        self._shows_db = None
        self._music_db = None
        try:
            super().__init__(baseurl, token, session, timeout)
            self._movie_sections = self._get_sections("movie")
            self._shows_sections = self._get_sections("show")
            self._music_sections = self._get_sections("artist")
            logger.info("PlexData initialized successfully")
        except BadRequest as e:
            logger.error(f"Failed to initialize PlexData due to bad request: {e}")
            raise
        except NotFound as e:
            logger.error(f"Failed to initialize PlexData due to resource not found: {e}")
            raise
        except Exception as e:
            logger.critical(f"Failed to initialize PlexData due to unexpected error: {e}")
            raise

    def _get_sections(self, section_type):
        try:
            sections = [section for section in self.library.sections() if section.type == section_type]
            logger.debug(f"Retrieved {len(sections)} {section_type} sections")
            return sections
        except BadRequest as e:
            logger.error(f"Failed to get sections of type {section_type} due to bad request: {e}")
            raise
        except NotFound as e:
            logger.error(f"Failed to get sections of type {section_type} due to resource not found: {e}")
            raise
        except Exception as e:
            logger.critical(f"Failed to get sections of type {section_type} due to unexpected error: {e}")
            raise

    def _movies(self) -> list:
        movies = [movie for section in self._movie_sections for movie in section.all()]
        logger.info(f"Retrieved {len(movies)} movies")
        return movies

    def _shows(self) -> list:
        shows = [show for section in self._shows_sections for show in section.all()]
        logger.info(f"Retrieved {len(shows)} shows")
        return shows

    def _music(self) -> list:
        music = [music for section in self._music_sections for music in section.all()]
        logger.info(f"Retrieved {len(music)} music")
        return music

    @property
    def get_movies_db(self) -> dict:
        if self._movies_db is None:
            self._movies_db = {}
            for movie in self._movies():
                movie_title = movie.title or "empty"
                movie_year = movie.year or "empty"
                movie_thumb = movie.thumb or "empty"
                movie_paths = movie.locations or "empty"
                if movie_paths:
                    movie_paths = str(";".join(movie.locations))

                movie_name = self.NON_ALPHANUMERIC.sub("", movie.title).strip()
                db = {
                    "title": movie_title,
                    "year": movie_year,
                    "file_path": movie_paths,
                    "thumb_path": movie_thumb,
                }
                self._movies_db[f"movie:{movie_name}:{movie.year}"] = db
                logger.debug(f"Added movie {movie_title} to the database")
            logger.info("Generated movies database")
        return self._movies_db

    @property
    def get_shows_db(self) -> dict:
        if self._shows_db is None:
            self._shows_db = {}
            for show in self._shows():
                show_name = self.NON_ALPHANUMERIC.sub("", show.title).strip()
                show_title = show.title or "empty"
                show_year = show.year or "empty"
                show_thumb = show.thumb or "empty"

                db = {
                    "title": show_title,
                    "year": show_year,
                    "thumb_path": show_thumb,
                    "show_location": show.locations[0],
                    # _get_episodes returns a dict.  Redis will not take a dict as a
                    # value and so the dict needs to be serialized.
                    "episodes": json.dumps(self._get_episodes(show)),
                }

                self._shows_db[f"movie:{show_name}:{show.year}"] = db
                logger.debug(f"Added show {show_title} to the database")
        logger.info("Generated TV shows database")
        return self._shows_db

    def _get_episodes(self, show) -> dict:
        if show.seasons():
            episode_dict = {}
            for season in show.seasons():
                episode_dict[f"season:{season.seasonNumber}"] = {}
                for episode in season.episodes():
                    episode_dict[f"season:{season.seasonNumber}"][f"episode:{episode.episodeNumber}"] = {
                        "episode_name": episode.title,
                        "episode_filename": Path(episode.locations[0]).stem,
                    }
            return episode_dict
        else:
            return {}

    @property
    def get_music_db(self) -> dict:
        if self._music_db is None:
            self._music_db = {}
            for artist in self._music():
                artist_title = artist.title or "empty"
                artist_thumb = artist.thumb or "empty"
                artist_name = self.NON_ALPHANUMERIC.sub("", artist_title).strip()
                db = {
                    "artist": artist_title,
                    "thumb": artist_thumb,
                    # _get_tracks returns a dict.  Redis will not take a dict as a
                    # value and so the dict needs to be serialized.
                    "tracks": json.dumps(self._get_tracks(artist)),
                }
                self._music_db[f"artist:{artist_name}"] = db
                logger.debug(f"Added artist {artist_title} to the database")
        logger.info("Generated music database")
        return self._music_db

    def _get_tracks(self, artist) -> dict:
        if artist.albums():
            track_db = {}
            for album in artist.albums():
                for track in album.tracks():
                    track_number = track.trackNumber or "empty"
                    track_name = track.title or "empty"
                    track_location = track.locations or "empty"
                    track_db[f"{album.title}:{album.year}"] = {
                        "track_number": track_number,
                        "track_name": track_name,
                        "track_location": track_location,
                    }
            return track_db
        else:
            return {}

    def compile_libraries(self, movies=False, shows=False, music=False, db_slice: slice = None) -> dict:
        libraries_db = {}
        try:
            if movies:
                if db_slice:
                    libraries_db.update({k: self.get_movies_db[k] for k in list(self.get_movies_db.keys())[db_slice]})
                    logger.debug(f"Added movies to libraries with slice: {db_slice}")
                else:
                    libraries_db.update(self.get_movies_db)
                    logger.debug("Added movies to libraries")
            if shows:
                if db_slice:
                    libraries_db.update({k: self.get_shows_db[k] for k in list(self.get_shows_db.keys())[db_slice]})
                    logger.debug(f"Added shows to libraries with slice: {db_slice}")
                else:
                    libraries_db.update(self.get_shows_db)
                    logger.debug("Added shows to libraries")
            if music:
                if db_slice:
                    libraries_db.update({k: self.get_music_db[k] for k in list(self.get_music_db.keys())[db_slice]})
                    logger.debug(f"Added music to libraries with slice: {db_slice}")
                else:
                    libraries_db.update(self.get_music_db)
                    logger.debug("Added music to libraries")

            logger.info("Libraries packaged")
            return libraries_db
        except BadRequest as e:
            logger.error(f"Failed to package libraries due to bad request: {e}")
            raise
        except NotFound as e:
            logger.error(f"Failed to package libraries due to resource not found: {e}")
            raise
        except Exception as e:
            logger.critical(f"Failed to package libraries due to unexpected error: {e}")
            raise
