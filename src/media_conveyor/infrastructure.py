from __future__ import annotations

import json
import logging
import os
from typing import Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AWSResourceCreator:
    def __init__(self, resource_configs: dict = None):
        if resource_configs is None:
            resource_configs = {}
        self.resource_configs = resource_configs
        self.aws_state_path = os.path.join(
            os.getenv("MEDIA_CONVEYOR"), "aws_state.json"
        )
        self.ec2_client = boto3.client("ec2")
        self.elasticache_client = boto3.client("elasticache")

    def _create_resource(self, client, method, params, resource_type):
        try:
            response = getattr(client, method)(**params)
            # logger.info(f"Response: {response}")  # Log the response
            logger.info(f"Resource Type: {resource_type}")  # Log the response
            if resource_type == "GroupId":
                resource_id = response[resource_type]
            elif resource_type == "Instances":
                resource_id = response[resource_type][0]["InstanceId"]
            elif resource_type == "CacheSubnetGroup":
                resource_id = response[resource_type]["CacheSubnetGroupName"]
            else:
                resource_id = response[resource_type][resource_type + "Id"]
            logger.info(
                f"{resource_type.capitalize()} created successfully. Id: {resource_id}"
            )
            return resource_id
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to create {resource_type}. Error: {str(e)}")
            return None

    def _create_vpc(self) -> str:
        return self._create_resource(
            self.ec2_client, "create_vpc", self.resource_configs.get("vpc", {}), "Vpc"
        )

    def _create_subnet(self, vpc_id) -> str:
        params = self.resource_configs.get("subnet", {})
        params["VpcId"] = vpc_id
        return self._create_resource(self.ec2_client, "create_subnet", params, "Subnet")

    def _create_ec2_security_group(self, vpc_id: str) -> str:
        params = self.resource_configs.get("security_group", {}).get("ec2", {})
        if not params:
            logger.error("Resource_type 'ec2' not found in security_group configs")
            return None
        params["VpcId"] = vpc_id
        ec2_security_group_id = self._create_resource(
            self.ec2_client, "create_security_group", params, "GroupId"
        )

        if ec2_security_group_id:
            # Authorize inbound traffic to the EC2 security group (example: allow SSH)
            ip_permissions = self.resource_configs.get("security_group", {}).get(
                "ec2_ip_permissions", []
            )
            self.ec2_client.authorize_security_group_ingress(
                GroupId=ec2_security_group_id, IpPermissions=ip_permissions
            )
            logger.info("Authorized inbound traffic to the EC2 security group")
        return ec2_security_group_id

    def _create_elasticache_security_group(
        self, ec2_security_group_id: str, vpc_id: str
    ) -> str:
        params = self.resource_configs.get("security_group", {}).get("elasticache", {})
        if not params:
            logger.error(
                "Resource_type 'elasticache' not found in security_group configs"
            )
            return None
        params["VpcId"] = vpc_id
        elasticache_security_group_id = self._create_resource(
            self.ec2_client, "create_security_group", params, "GroupId"
        )

        if elasticache_security_group_id:
            # Authorize ingress for Redis (example: allow access from your EC2 security group)
            ip_permissions = self.resource_configs.get("security_group", {}).get(
                "cache_ip_permissions", []
            )
            for permission in ip_permissions:
                permission["UserIdGroupPairs"] = [{"GroupId": ec2_security_group_id}]
            self.ec2_client.authorize_security_group_ingress(
                GroupId=elasticache_security_group_id,
                IpPermissions=ip_permissions,
            )
            logger.info("Authorized ingress for Redis")
        return elasticache_security_group_id

    def _create_ec2_instance(self, subnet_id, ec2_security_group_id) -> str:
        params = self.resource_configs.get("ec2", {})
        params["NetworkInterfaces"] = [
            {
                "DeviceIndex": 0,
                "SubnetId": subnet_id,
                "Groups": [ec2_security_group_id],
                "AssociatePublicIpAddress": True,
            }
        ]
        return self._create_resource(
            self.ec2_client, "run_instances", params, "Instances"
        )

    def _create_cache_subnet_group(self, subnet_id: str, vpc_id: str) -> str:
        cache_subnet_group_name = "mccachesubnetgroup"
        try:
            response = self.elasticache_client.describe_cache_subnet_groups(
                CacheSubnetGroupName=cache_subnet_group_name
            )
            if response["CacheSubnetGroups"]:
                existing_vpc_id = response["CacheSubnetGroups"][0]["VpcId"]
                if existing_vpc_id == vpc_id:
                    logger.info(
                        f"Cache subnet group {cache_subnet_group_name} already exists and is associated with the correct VPC."
                    )
                    return cache_subnet_group_name
                else:
                    logger.info(
                        f"Cache subnet group {cache_subnet_group_name} exists but is associated with a different VPC. Creating a new cache subnet group."
                    )
                    cache_subnet_group_name += "_new"
        except self.elasticache_client.exceptions.CacheSubnetGroupNotFoundFault:
            pass

        params = {
            "CacheSubnetGroupName": cache_subnet_group_name,
            "SubnetIds": [subnet_id],
            "CacheSubnetGroupDescription": "My cache subnet group",
        }
        resource_id = self._create_resource(
            self.elasticache_client,
            "create_cache_subnet_group",
            params,
            "CacheSubnetGroup",
        )
        return resource_id

    def _create_elasticache_cluster(
        self, subnet_id, vpc_id, cache_security_group_id
    ) -> Tuple[str, str]:
        params = self.resource_configs.get("elasticache", {})
        cache_subnet_group_name = self._create_cache_subnet_group(subnet_id, vpc_id)
        params["CacheSubnetGroupName"] = cache_subnet_group_name
        if params["CacheSubnetGroupName"] is None:
            return None
        params["SecurityGroupIds"] = [cache_security_group_id]
        cluster_id = self._create_resource(
            self.elasticache_client,
            "create_cache_cluster",
            params,
            "CacheCluster",
        )
        return cache_subnet_group_name, cluster_id

    def create_state(self):
        vpc_id = self._create_vpc()
        subnet_id = self._create_subnet(vpc_id)
        ec2_security_group_id = self._create_ec2_security_group(vpc_id)
        cache_security_group_id = self._create_elasticache_security_group(
            ec2_security_group_id, vpc_id
        )
        instance_id = self._create_ec2_instance(subnet_id, ec2_security_group_id)
        cache_subnet_group_name, cluster_id = self._create_elasticache_cluster(
            subnet_id, vpc_id, cache_security_group_id
        )

        # Write data to a file
        state_data = {
            "VpcId": vpc_id,
            "SubnetId": subnet_id,
            "GroupIds": [ec2_security_group_id, cache_security_group_id],
            "CacheSubnetGroupName": cache_subnet_group_name,
            "InstanceIds": [instance_id],
            "CacheCluster": cluster_id,
        }

        with open(self.aws_state_path, "w") as file:
            json.dump(state_data, file)
