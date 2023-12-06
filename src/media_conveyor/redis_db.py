from __future__ import annotations

from typing import TYPE_CHECKING

from redis import Redis

# Used for type-hinting
if TYPE_CHECKING:
    from .plex_data import PlexData


class RedisDB:
    def __init__(
        self: "RedisDB", host: str = "localhost", port: int = 6379, db: int = 0
    ) -> None:
        self.host = host
        self.port = port
        self.db = db
        self.redis = Redis(
            host=self.host, port=self.port, db=self.db, decode_responses=True
        )


class RedisPlexDB(RedisDB):
    # TODO Is there a need to refresh the database?  If so then I need to develop a
    # method for removing Plex entries that don't exist any longer
    def __init__(
        self: RedisDB,
        plex_db: dict,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
    ) -> None:
        super().__init__(host, port, db)
        self.plex_db = plex_db

    def make_db(self):
        with self.redis.pipeline() as pipe:
            for key_id, value_data in self.plex_db.items():
                pipe.hmset(key_id, value_data)
            pipe.execute()
        self.redis.bgsave()
