import datetime
import json
import logging
import os
import time
from pathlib import Path
from pprint import pprint

import boto3
import redis

from ..authentication import AWSCredentials, PlexAuthentication
from ..infrastructure import AWSStateData
from ..plex_data import PlexData
from ..redis_db import RedisDB, RedisPlexDB

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)


media_conveyor_root = Path.home() / ".media_conveyor"
project_root = Path(__file__).resolve().parent.parent.parent.parent
os.environ["MEDIA_CONVEYOR"] = str(project_root / "tests/.media_conveyor")
credentials = AWSCredentials()
credentials.load()


def upload():
    start_time = time.time()
    plex_auth = PlexAuthentication()
    plex_data = PlexData(plex_auth.baseurl, plex_auth.token)
    plex_db = plex_data.compile_libraries(movies=True, shows=True)
    end_time = time.time()
    print(f"Execution time: {end_time - start_time} seconds")

    start_time = time.time()
    aws_state = AWSStateData()
    redis_db = RedisPlexDB(plex_db, **aws_state.redis_params(db_number=0))
    redis_db.make_db(db_slice=slice(100, 105))
    end_time = time.time()
    print(f"Execution time: {end_time - start_time} seconds")


def ping():
    # pprint(get_redis_cluster_endpoint(cluster_id="mcrediscachecluster"))
    # cluster_endpoint, cluster_port = get_redis_cluster_endpoint(cluster_id="mcrediscachecluster")
    cluster_endpoint = "<ENDPOINTHERE>"
    cluster_port = 6379
    redis_client = redis.StrictRedis(host=cluster_endpoint, port=cluster_port, decode_responses=True)
    print(redis_client.client_id())
    redis_client.ping()

    # redis_client.set("key", "value")
    # result = redis_client.get("key")
    # print(result)

    # aws_state = AWSStateData()
    # redis_db = RedisDB()
    # redis_db.verify_connection()

    # r.set("key", "value")
    # result = r.get("key")
    # print(result)


# def get_redis_cluster_endpoint(cluster_id, region="us-west-1"):
#     # Create an ElastiCache client using the AWS SDK for Python (Boto3)
#     client = boto3.client("elasticache", region_name=region)

#     # Describe the cache cluster
#     response = client.describe_cache_clusters(CacheClusterId=cluster_id, ShowCacheNodeInfo=True)

#     # Extract the endpoint information
#     # endpoint = response["CacheClusters"][0]["Endpoint"]
#     # return endpoint["Address"], endpoint["Port"]
#     return response


def get_redis_cluster_endpoint(cluster_id, region="us-west-1"):
    # Create an ElastiCache client using the AWS SDK for Python (Boto3)
    client = boto3.client("elasticache", region_name=region)

    # Describe the cache cluster with ShowCacheNodeInfo set to True
    response = client.describe_cache_clusters(CacheClusterId=cluster_id, ShowCacheNodeInfo=True)
    pprint(response)
    # Print the full response for debugging
    # print(json.dumps(response, indent=2, cls=DateTimeEncoder))

    # Extract the endpoint information
    cluster_info = response.get("CacheClusters", [])
    print(cluster_info)
    if cluster_info:
        # Try accessing "Endpoint" first, if not found, try "ConfigurationEndpoint"
        endpoint = cluster_info[0].get("Endpoint") or cluster_info[0].get("ConfigurationEndpoint", {})
        return endpoint.get("Address"), endpoint.get("Port")

    return None, None
