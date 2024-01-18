import json
import logging
import os
import sys
import time
from pathlib import Path
from pprint import pprint

import boto3

from ..authentication import AWSCredentials
from ..configurations import AWSConfigs
from ..infrastructure import AWSResourceCreator, AWSStateData
from ..logging import setup_logger

setup_logger(level="INFO")
aws_config = AWSConfigs()

media_conveyor_root = Path.home() / ".media_conveyor"
project_root = Path(__file__).resolve().parent.parent.parent.parent
os.environ["MEDIA_CONVEYOR"] = str(project_root / "tests/.media_conveyor")
credentials = AWSCredentials()
credentials.verify_credentials()


def aws_run():
    # aws_config = AWSConfigs()
    resource_configs = aws_config.resolve_state()
    # pprint(resource_configs)
    state_manager = AWSResourceCreator(resource_configs=resource_configs)
    state_manager.create_state()


def aws_stop():
    # logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])

    # aws_config = AWSConfigs()
    resource_configs = aws_config.resolve_state()
    state_manager = AWSResourceCreator(resource_configs=resource_configs)
    state_manager.terminate_state()


def aws_test():
    # aws_config = AWSConfigs()
    # resource_configs = aws_config.resolve_state()

    # state_data = AWSStateData()
    # cluster_id, cluster_port = state_data.get_elasticache_endpoint_and_port()
    # print(cluster_id, cluster_port)

    state_manager = AWSResourceCreator()
    # state_manager._create_key_pair()
    state_manager._delete_key_pair()

    pass


def aws_state():
    with open("/home/james/code/media_conveyor/tests/.media_conveyor/aws_state.json", "r") as file:
        aws_state = json.load(file)

    ec2 = boto3.resource("ec2")
    elasticache = boto3.client("elasticache")

    # Check the status of EC2 instances
    for instance_id in aws_state["InstanceIds"]:
        instance = ec2.Instance(id=instance_id)
        print(f'EC2 Instance {instance_id}: {instance.state["Name"]}')

    # Check the status of the cache cluster
    cache_cluster_id = aws_state["CacheClusterId"]
    response = elasticache.describe_cache_clusters(CacheClusterId=cache_cluster_id)
    cache_cluster = response["CacheClusters"][0]
    print(f'Cache Cluster {cache_cluster_id}: {cache_cluster["CacheClusterStatus"]}')
