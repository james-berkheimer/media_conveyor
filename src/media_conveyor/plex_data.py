from __future__ import annotations

import logging
import re

import json5 as json
from plexapi.server import PlexServer

logger = logging.getLogger(__name__)


class PlexData(PlexServer):
    def __init__(self, baseurl=None, token=None, session=None, timeout=None):
        super().__init__(baseurl, token, session, timeout)
        self._movie_sections = []
        self._shows_sections = []
        self._music_sections = []
        self._movie_sections.extend(
            section for section in self.library.sections() if section.type == "movie"
        )
        self._shows_sections.extend(
            section for section in self.library.sections() if section.type == "show"
        )
        self._music_sections.extend(
            section for section in self.library.sections() if section.type == "artist"
        )
        logger.info("PlexData initialized successfully")

    @property
    def movies(self) -> list:
        movies = [movie for section in self._movie_sections for movie in section.all()]
        logger.info(f"Retrieved {len(movies)} movies")
        return movies

    @property
    def shows(self) -> list:
        shows = [show for section in self._shows_sections for show in section.all()]
        logger.info(f"Retrieved {len(shows)} shows")
        return shows

    @property
    def music(self) -> list:
        music = [music for section in self._music_sections for music in section.all()]
        logger.info(f"Retrieved {len(music)} music")
        return music

    @property
    def movies_db(self) -> dict:
        db = {}
        pattern = re.compile(r"[^a-zA-Z0-9]")
        for movie in self.movies:
            # Verify data exists.
            movie_title = movie.title or "NONE"
            movie_year = movie.year or "NONE"
            movie_thumb = movie.thumb or "NONE"
            movie_paths = movie.locations or "NONE"
            if movie_paths != "NONE":
                movie_paths = str(";".join(movie.locations))

            movie_name = pattern.sub("", movie.title).strip()
            db[f"movie:{movie_name}:{movie.year}"] = {
                "title": movie_title,
                "year": movie_year,
                "file_path": movie_paths,
                "thumb_path": movie_thumb,
            }
        logger.info("Generated movies database")
        return db

    @property
    def shows_db(self) -> dict:
        shows_db = {}
        pattern = re.compile(r"[^a-zA-Z0-9]")
        for show in self.shows:
            # Verify data exists.
            show_name = pattern.sub("", show.title).strip()
            show_title = show.title or "NONE"
            show_year = show.year or "NONE"
            show_thumb = show.thumb or "NONE"

            shows_db[f"show:{show_name}:{show.year}"] = {
                "title": show_title,
                "year": show_year,
                "thumb_path": show_thumb,
                "episodes": self._get_episodes(show),
            }
        logger.info("Generated TV shows database")
        return shows_db

    def _get_episodes(self, show) -> str:
        # Verify data exists.
        if show.seasons():
            episode_db = {}
            for season in show.seasons():
                for episode in season.episodes():
                    episode_db[f"season {season.seasonNumber}"] = {
                        "episode_number": episode.episodeNumber,
                        "episode_name": episode.title,
                        "episode_location": episode.locations,
                    }
            return json.dumps(episode_db)
        else:
            return "NONE"

    @property
    def music_db(self) -> dict:
        music_db = {}
        pattern = re.compile(r"[^a-zA-Z0-9]")
        for artist in self.music:
            # Verify data exists.
            artist_title = artist.title or "NONE"
            artist_thumb = artist.thumb or "NONE"
            artist_name = pattern.sub("", artist_title).strip()
            music_db[f"artist:{artist_name}"] = {
                "artist": artist_title,
                "thumb": artist_thumb,
                "tracks": self._get_tracks(artist),
            }
        logger.info("Generated music database")
        return music_db

    def _get_tracks(self, artist) -> str:
        if artist.albums():
            track_db = {}
            for album in artist.albums():
                for track in album.tracks():
                    # Verify data exists.
                    track_number = track.trackNumber or "NONE"
                    track_name = track.title or "NONE"
                    track_location = track.locations or "NONE"
                    track_db[f"{album.title}:{album.year}"] = {
                        "track_number": track_number,
                        "track_name": track_name,
                        "track_location": track_location,
                    }
            return json.dumps(track_db)
        else:
            return "NONE"

    def package_libraries(self, movies=False, shows=False, music=False) -> dict:
        libraries_db = {}
        if movies:
            libraries_db.update(self.movies_db)
        if shows:
            libraries_db.update(self.shows_db)
        if music:
            libraries_db.update(self.music)

        logger.info("Libraries packaged")
        return libraries_db
