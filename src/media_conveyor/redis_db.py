from __future__ import annotations

import logging
from typing import Dict

from redis import ConnectionError, RedisError, StrictRedis, TimeoutError

from .logging import setup_logger

logger = setup_logger()


class RedisPlexDB(StrictRedis):
    plex_db: Dict[str, str]

    def __init__(
        self, plex_db: Dict[str, str] = None, host: str = "localhost", port: int = 9000, decode_responses: bool = True
    ) -> None:
        if not host:
            raise ValueError("Host must be provided")
        if not isinstance(port, int) or port <= 0:
            raise ValueError("Port must be a positive integer")
        if plex_db is not None and (not isinstance(plex_db, dict) or not plex_db):
            raise ValueError("plex_db must be a non-empty dictionary")

        super().__init__(host=host, port=port, decode_responses=decode_responses)
        self.plex_db = plex_db if plex_db is not None else {}

    def make_db(self) -> None:
        try:
            with self.pipeline() as pipe:
                for key_id, value_data in self.plex_db.items():
                    pipe.hset(key_id, mapping=value_data)
                pipe.execute()
            logger.info("Database created successfully")
        except ConnectionError:
            logger.error("Could not connect to Redis server")
            raise
        except TimeoutError:
            logger.error("Redis command timed out")
            raise
        except RedisError as e:
            logger.error("An unexpected Redis error occurred: %s", e)
            raise

    def delete_db(self) -> None:
        try:
            self.flushdb()
            logger.info("Database deleted successfully")
        except ConnectionError:
            logger.error("Could not connect to Redis server")
            raise
        except TimeoutError:
            logger.error("Redis command timed out")
            raise
        except RedisError as e:
            logger.error("An unexpected Redis error occurred: %s", e)
            raise
