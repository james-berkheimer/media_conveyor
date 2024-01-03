import os
from pathlib import Path
from pprint import pprint

from ..authentication import AWSCredentials, PlexAuthentication
from ..connections import SSHTunnel, TunnelConfig
from ..infrastructure import AWSStateData
from ..logging import setup_logger
from ..plex_data import PlexData
from ..redis_db import RedisPlexDB

logger = setup_logger()
setup_logger(level="INFO")

media_conveyor_root = Path.home() / ".media_conveyor"
project_root = Path(__file__).resolve().parent.parent.parent.parent
os.environ["MEDIA_CONVEYOR"] = str(project_root / "tests/.media_conveyor")
credentials = AWSCredentials()
credentials.load()


def ping():
    aws_state = AWSStateData()
    config = TunnelConfig(**aws_state.connection_params())
    with SSHTunnel(config) as _:
        redis_client = RedisPlexDB()
        redis_client.ping()


def write():
    aws_state = AWSStateData()
    plex_auth = PlexAuthentication()
    plex_data = PlexData(plex_auth.baseurl, plex_auth.token)
    plex_db = plex_data.compile_libraries(movies=True, db_slice=slice(100, 105))
    config = TunnelConfig(**aws_state.connection_params())
    with SSHTunnel(config) as _:
        redis_client = RedisPlexDB(plex_db=plex_db)
        redis_client.make_db()


def read():
    aws_state = AWSStateData()
    config = TunnelConfig(**aws_state.connection_params())
    with SSHTunnel(config) as _:
        redis_client = RedisPlexDB()
        keys = redis_client.keys()
        for key in keys:
            print(key)
            print(redis_client.hgetall(key))


def delete_db():
    aws_state = AWSStateData()
    config = TunnelConfig(**aws_state.connection_params())
    with SSHTunnel(config) as _:
        redis_client = RedisPlexDB()
        redis_client.delete_db()
