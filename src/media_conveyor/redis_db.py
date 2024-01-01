from __future__ import annotations

import logging
from typing import Dict

from redis import Redis, RedisError

# Configure logging
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
from .utils import setup_logger

logger = setup_logger()


class RedisDB:
    def __init__(self: "RedisDB", host: str, port: int, db: int) -> None:
        self.host = host
        self.port = port
        self.db = db
        self.redis = Redis(host=self.host, port=self.port, db=self.db, decode_responses=True)
        logging.info("RedisDB instance created with host=%s, port=%d, db=%d", host, port, db)

    def verify_connection(self: "RedisDB") -> None:
        try:
            self.redis.ping()
            logging.info("Connection to Redis server successful")
        except RedisError as e:
            logging.error("An error occurred: %s", e)


class RedisPlexDB(RedisDB):
    def __init__(
        self: "RedisDB",
        plex_db: Dict[str, str],
        host: str,
        port: int,
        db: int,
    ) -> None:
        if not host:
            raise ValueError("Host must be provided")
        if not isinstance(port, int) or port <= 0:
            raise ValueError("Port must be a positive integer")
        if not isinstance(db, int) or db < 0:
            raise ValueError("DB must be a non-negative integer")
        if not isinstance(plex_db, dict) or not plex_db:
            raise ValueError("plex_db must be a non-empty dictionary")

        super().__init__(host, port, db)
        self.plex_db = plex_db

    def make_db(self, db_slice: slice = None) -> None:
        try:
            with self.redis.pipeline() as pipe:
                if db_slice:
                    logging.info(f"Creating database with provided slice: {db_slice}.")
                    for key_id, value_data in list(self.plex_db.items())[db_slice]:
                        pipe.hset(key_id, value_data)
                else:
                    for key_id, value_data in self.plex_db.items():
                        pipe.hset(key_id, value_data)
                    pipe.execute()
            self.redis.bgsave()
            logging.info("Database created successfully")
        except RedisError as e:
            logging.error("An error occurred: %s", e)
