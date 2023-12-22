from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict

from redis import Redis

if TYPE_CHECKING:
    from .plex_data import PlexData

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class RedisDB:
    def __init__(self: "RedisDB", host: str = "localhost", port: int = 6379, db: int = 0) -> None:
        self.host = host
        self.port = port
        self.db = db
        self.redis = Redis(host=self.host, port=self.port, db=self.db, decode_responses=True)
        logging.info("RedisDB instance created with host=%s, port=%d, db=%d", host, port, db)


class RedisPlexDB(RedisDB):
    def __init__(
        self: "RedisDB",
        plex_db: Dict[str, str],
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
    ) -> None:
        super().__init__(host, port, db)
        self.plex_db = plex_db
        logging.info(
            "RedisPlexDB instance created with plex_db=%s, host=%s, port=%d, db=%d",
            plex_db,
            host,
            port,
            db,
        )

    def make_db(self) -> None:
        try:
            with self.redis.pipeline() as pipe:
                for key_id, value_data in self.plex_db.items():
                    pipe.hset(key_id, value_data)
                pipe.execute()
            self.redis.bgsave()
            logging.info("Database created successfully")
        except Exception as e:
            logging.error("An error occurred: %s", e)
