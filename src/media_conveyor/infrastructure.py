from __future__ import annotations

import json
import logging
import os
import time
from pprint import pprint

import boto3
from botocore.exceptions import BotoCoreError, ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AWSState:
    EC2_SERVICE_NAME = "ec2"
    ELASTICACHE_SERVICE_NAME = "elasticache"
    MAX_ATTEMPTS = 30
    DELAY_SECONDS = 10

    def __init__(self, resource_configs: dict):
        self.resource_configs = resource_configs
        self.aws_state_path = os.path.join(
            os.getenv("MEDIA_CONVEYOR"), "aws_state.json"
        )
        self.ec2_client = boto3.client(self.EC2_SERVICE_NAME)
        self.elasticache_client = boto3.client(self.ELASTICACHE_SERVICE_NAME)
        self.ec2_instance = None
        self.elasticache_cluster = None
        self.subnet_id = None
        self.vpc_id = None

    def create_state(self):
        if os.path.exists(self.aws_state_path):
            self.terminate_state()

        def create_resource(client, params: dict, key: str, id_key: str):
            logger.info(f"Creating {key}...")

            # Use the appropriate create method based on the resource type
            if key == "Vpc":
                create_method = client.create_vpc
            elif key == "Subnet":
                create_method = client.create_subnet
            elif key == "Instances":
                create_method = client.run_instances
            elif key == "CacheCluster":
                create_method = client.create_cache_cluster
            else:
                raise ValueError(f"Unsupported resource type: {key}")

            try:
                response = create_method(**params)
                if key == "Instances":
                    resource_id = response[key][0][id_key]
                else:
                    resource_id = response[key][id_key]
                logger.info(
                    f"{key.capitalize()} created successfully. {id_key.capitalize()}: {resource_id}"
                )
                return resource_id
            except (BotoCoreError, ClientError) as e:
                logger.error(f"Error creating {key}: {e}")
                return None

        # Create VPC and Subnet
        vpc_id = create_resource(
            self.ec2_client, self.resource_configs["vpc"], "Vpc", "VpcId"
        )
        self.resource_configs["subnet"]["VpcId"] = vpc_id
        subnet_id = create_resource(
            self.ec2_client, self.resource_configs["subnet"], "Subnet", "SubnetId"
        )

        # Create EC2 Instance using the subnet_id
        ec2_params = self.resource_configs["ec2"]
        ec2_params["SubnetId"] = subnet_id
        ec2_instance_id = create_resource(
            self.ec2_client, ec2_params, "Instances", "InstanceId"
        )

        # Create ElastiCache Cluster using the vpc_id
        elasticache_params = self.resource_configs["elasticache"]
        elasticache_params["SecurityGroupIds"] = list(vpc_id)
        elasticache_cluster_id = create_resource(
            self.elasticache_client,
            elasticache_params,
            "CacheCluster",
            "CacheClusterId",
        )

        # Write data to a file
        state_data = {
            "vpc_id": vpc_id,
            "subnet_id": subnet_id,
            "ec2_instance_id": ec2_instance_id,
            "elasticache_cluster_id": elasticache_cluster_id,
        }

        with open(self.aws_state_path, "w") as file:
            json.dump(state_data, file)

    def terminate_state(self):
        if os.path.exists(self.aws_state_path):
            with open(self.aws_state_path, "r") as file:
                state_data = json.load(file)

            resources_to_terminate = [
                (
                    "elasticache_cluster_id",
                    self.elasticache_client.delete_cache_cluster,
                ),
                ("ec2_instance_id", self.ec2_client.terminate_instances),
                ("subnet_id", self.ec2_client.delete_subnet),
                ("vpc_id", self.ec2_client.delete_vpc),
            ]

            for resource_key, terminate_function in resources_to_terminate:
                resource_id = state_data.get(resource_key)
                if resource_id:
                    try:
                        terminate_function(ResourceIds=[resource_id])
                        self.wait_for_termination(
                            describe_function=getattr(
                                self.ec2_client, f"describe_{resource_key}s"
                            ),
                            resource_id=resource_id,
                        )
                    except (BotoCoreError, ClientError) as e:
                        logger.error(f"Error terminating resource {resource_key}: {e}")

            # Remove the aws_state.json file after termination
            os.remove(self.aws_state_path)

    def wait_for_termination(
        self,
        describe_function,
        resource_id,
        max_attempts=MAX_ATTEMPTS,
        delay_seconds=DELAY_SECONDS,
    ):
        """
        Wait for the termination of a resource by polling its status.
        """
        for _ in range(max_attempts):
            try:
                resource_info = describe_function(ResourceIds=[resource_id])
                if not resource_info["ResponseMetadata"]["HTTPStatusCode"] == 200:
                    logger.warning(
                        f"Failed to get status for resource {resource_id}. Retrying..."
                    )
                    time.sleep(delay_seconds)
                    continue

                resource_status = resource_info["Status"]
                if resource_status.lower() == "terminated":
                    logger.info(f"Resource {resource_id} terminated successfully.")
                    return True
            except (BotoCoreError, ClientError) as e:
                logger.warning(
                    f"Error checking status for resource {resource_id}: {e}. Retrying..."
                )
            time.sleep(delay_seconds)

        logger.warning(f"Timeout waiting for resource {resource_id} to terminate.")
        return False
