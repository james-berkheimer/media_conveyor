from __future__ import annotations

import json
import logging
import os
from typing import Tuple

import boto3
import botocore
from botocore.exceptions import BotoCoreError, ClientError

from media_conveyor.exceptions import TerminationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AWSResourceCreator:
    def __init__(self, resource_configs: dict = None):
        if resource_configs is None:
            resource_configs = {}
        self.resource_configs = resource_configs
        media_conveyor_path = os.getenv("MEDIA_CONVEYOR")
        if media_conveyor_path is None:
            raise EnvironmentError("The MC_AWS_STATE environment variable is not set.")
        self.aws_state_path = os.path.join(media_conveyor_path, "aws_state.json")
        self.ec2_client = boto3.client("ec2")
        self.elasticache_client = boto3.client("elasticache")
        # self._check_aws_credentials()

    @property
    def current_state(self):
        logger.info("Accessing current_state property")
        try:
            with open(self.aws_state_path, "r") as file:
                state_data = json.load(file)
                return state_data
        except FileNotFoundError:
            logger.error("AWS state file not found. Please create a new state.")
            return None
        except IOError:
            logger.error("Failed to open the AWS state file. Check your file permissions.")
            return None

    @current_state.setter
    def current_state(self, state_data):
        logger.info("Setting current_state property with data: %s", state_data)
        try:
            with open(self.aws_state_path, "w") as file:
                json.dump(state_data, file, indent=4)
        except IOError:
            logger.error("Failed to write to the AWS state file. Check your file permissions.")

    def create_state(self):
        logger.info("Creating new AWS state")
        vpc_id = self._create_vpc()
        subnet_id = self._create_subnet(vpc_id)
        ec2_security_group_id = self._create_ec2_security_group(vpc_id)
        cache_security_group_id = self._create_elasticache_security_group(ec2_security_group_id, vpc_id)
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
            "CacheClusterId": cluster_id,
        }

        self.current_state = state_data

    def get_current_state(self):
        logger.info("Getting current AWS state")
        return self.current_state

    def terminate_state(self):
        logger.info("Terminating AWS state")
        if self.current_state is None:
            return
        try:
            self._terminate_ec2_instance()
            self._terminate_elasticache_cluster()
            self._delete_cache_subnet_group()
            self._delete_vpc()

            # Delete aws_state.json file after successful termination
            if os.path.exists("aws_state.json"):
                os.remove("aws_state.json")
                logger.info("aws_state.json removed successfully")
            else:
                logger.info("aws_state.json does not exist")

        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to terminate state. Error: {str(e)}")
            raise TerminationError(str(e)) from e

    def _create_vpc(self) -> str:
        logger.info("Creating VPC")
        return self._create_resource(self.ec2_client, "create_vpc", self.resource_configs.get("vpc", {}), "Vpc")

    def _create_subnet(self, vpc_id) -> str:
        logger.info("Creating subnet for VPC: %s", vpc_id)
        params = self.resource_configs.get("subnet", {})
        params["VpcId"] = vpc_id
        return self._create_resource(self.ec2_client, "create_subnet", params, "Subnet")

    def _create_ec2_security_group(self, vpc_id: str) -> str:
        logger.info("Creating EC2 security group for VPC: %s", vpc_id)
        params = self.resource_configs.get("security_group", {}).get("ec2", {})
        if not params:
            logger.error("Resource_type 'ec2' not found in security_group configs")
            return None
        params["VpcId"] = vpc_id
        ec2_security_group_id = self._create_resource(self.ec2_client, "create_security_group", params, "GroupId")

        if ec2_security_group_id:
            # Authorize inbound traffic to the EC2 security group (example: allow SSH)
            ip_permissions = self.resource_configs.get("security_group", {}).get("ec2_ip_permissions", [])
            self.ec2_client.authorize_security_group_ingress(
                GroupId=ec2_security_group_id, IpPermissions=ip_permissions
            )
            logger.info("Authorized inbound traffic to the EC2 security group")
        return ec2_security_group_id

    def _create_elasticache_security_group(self, ec2_security_group_id: str, vpc_id: str) -> str:
        logger.info("Creating ElastiCache security group for VPC: %s", vpc_id)
        params = self.resource_configs.get("security_group", {}).get("elasticache", {})
        if not params:
            logger.error("Resource_type 'elasticache' not found in security_group configs")
            return None
        params["VpcId"] = vpc_id
        elasticache_security_group_id = self._create_resource(
            self.ec2_client, "create_security_group", params, "GroupId"
        )

        if elasticache_security_group_id:
            # Authorize ingress for Redis (example: allow access from your EC2 security group)
            ip_permissions = self.resource_configs.get("security_group", {}).get("cache_ip_permissions", [])
            for permission in ip_permissions:
                permission["UserIdGroupPairs"] = [{"GroupId": ec2_security_group_id}]
            self.ec2_client.authorize_security_group_ingress(
                GroupId=elasticache_security_group_id,
                IpPermissions=ip_permissions,
            )
            logger.info("Authorized ingress for Redis")
        return elasticache_security_group_id

    def _create_ec2_instance(self, subnet_id, ec2_security_group_id) -> str:
        logger.info(
            "Creating EC2 instance for subnet: %s and security group: %s",
            subnet_id,
            ec2_security_group_id,
        )
        params = self.resource_configs.get("ec2", {})
        params["NetworkInterfaces"] = [
            {
                "DeviceIndex": 0,
                "SubnetId": subnet_id,
                "Groups": [ec2_security_group_id],
                "AssociatePublicIpAddress": True,
            }
        ]
        return self._create_resource(self.ec2_client, "run_instances", params, "Instances")

    def _create_cache_subnet_group(self, subnet_id: str, vpc_id: str) -> str:
        logger.info("Creating cache subnet group for subnet: %s and VPC: %s", subnet_id, vpc_id)

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

    def _create_elasticache_cluster(self, subnet_id, vpc_id, cache_security_group_id) -> Tuple[str, str]:
        logger.info(
            "Creating ElastiCache cluster for subnet: %s, VPC: %s and security group: %s",
            subnet_id,
            vpc_id,
            cache_security_group_id,
        )

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

    # self.ec2_client, "create_security_group", params, "GroupId"
    def _create_resource(self, client, method, params, resource_type):
        logger.info("Creating resource of type: %s with params: %s", resource_type, params)
        try:
            response = getattr(client, method)(**params)
            logger.info(f"Resource Type: {resource_type}")  # Log the response
            if resource_type == "GroupId":
                resource_id = response[resource_type]
            elif resource_type == "Instances":
                resource_id = response[resource_type][0]["InstanceId"]
            elif resource_type == "CacheSubnetGroup":
                resource_id = response[resource_type]["CacheSubnetGroupName"]
            else:
                resource_id = response[resource_type][resource_type + "Id"]
            logger.info(f"{resource_type.capitalize()} created successfully. Id: {resource_id}")
            return resource_id
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to create {resource_type}. Error: {str(e)}")
            return None

    def _terminate_ec2_instance(self):
        logger.info("Terminating EC2 instance")
        instance_ids = self.current_state["InstanceIds"]

        # Check if instances exist
        response = self.ec2_client.describe_instances(InstanceIds=instance_ids)
        reservations = response["Reservations"]
        if not reservations:
            logger.info("Instances do not exist.")
            return

        # If instances exist, proceed to terminate them
        response = self.ec2_client.terminate_instances(InstanceIds=instance_ids)
        terminating_instances = response["TerminatingInstances"]

        for instance in terminating_instances:
            instance_id = instance["InstanceId"]
            current_state = instance["CurrentState"]["Name"]
            previous_state = instance["PreviousState"]["Name"]

            logger.info(f"Instance {instance_id} transitioning from '{previous_state}' to '{current_state}'")

            waiter = self.ec2_client.get_waiter("instance_terminated")
            waiter.wait(InstanceIds=[instance_id])
            logger.info(f"Instance {instance_id} has been terminated.")

    def _terminate_elasticache_cluster(self):
        # TODO: Let's remove the cluster from the VPC first.
        # That way we can delete the VPC without having to wait for the cluster to delete.
        logger.info("Terminating ElastiCache cluster")
        cluster_id = self.current_state["CacheClusterId"]
        try:
            self.elasticache_client.describe_cache_clusters(CacheClusterId=cluster_id)
        except self.elasticache_client.exceptions.CacheClusterNotFoundFault:
            logger.info(f"ElastiCache cluster {cluster_id} does not exist.")
            return
        self.elasticache_client.delete_cache_cluster(CacheClusterId=cluster_id)

        waiter = self.elasticache_client.get_waiter("cache_cluster_deleted")
        waiter.wait(CacheClusterId=cluster_id)
        logger.info(f"ElastiCache cluster {cluster_id} has been terminated.")

    def _delete_cache_subnet_group(self):
        logger.info("Deleting cache subnet group")
        cache_subnet_group_name = self.current_state["CacheSubnetGroupName"]
        try:
            self.elasticache_client.describe_cache_subnet_groups(CacheSubnetGroupName=cache_subnet_group_name)
        except self.elasticache_client.exceptions.CacheSubnetGroupNotFoundFault:
            logger.info(f"Cache subnet group {cache_subnet_group_name} does not exist.")
            return
        self.elasticache_client.delete_cache_subnet_group(CacheSubnetGroupName=cache_subnet_group_name)
        logger.info(f"Cache subnet group {cache_subnet_group_name} has been terminated.")

    def _delete_vpc(self):
        logger.info("Deleting VPC dependencies")
        vpc_id = self.current_state["VpcId"]

        try:
            self.ec2_client.describe_vpcs(VpcIds=[vpc_id])
        except self.ec2_client.exceptions.VpcIdNotFound:
            logger.info(f"VPC {vpc_id} does not exist.")
            return

        # Get VPC dependencies
        dependencies = self._get_vpc_dependencies(vpc_id)

        # Check if there are no dependencies
        if not any(dependencies.values()):
            logger.info(f"VPC {vpc_id} has no dependencies.")
            self.ec2_client.delete_vpc(VpcId=vpc_id)
            logger.info(f"VPC {vpc_id} has been deleted.")
            return

        # Delete dependencies in the correct order
        self._delete_subnets(dependencies["Subnets"])
        self._delete_security_groups(dependencies["SecurityGroups"])
        # Add other delete methods as needed

        self.ec2_client.delete_vpc(VpcId=vpc_id)
        logger.info(f"VPC {vpc_id} has been deleted.")

    def _delete_subnets(self, subnets):
        for subnet in subnets:
            subnet_id = subnet["SubnetId"]
            # Skip default subnets
            if subnet["DefaultForAz"]:
                continue
            try:
                self.ec2_client.delete_subnet(SubnetId=subnet_id)
                logger.info(f"Subnet {subnet_id} has been deleted.")
            except self.ec2_client.exceptions.ClientError as e:
                logger.error(f"Failed to delete subnet {subnet_id}: {e}")

    def _delete_security_groups(self, security_groups):
        for sg in security_groups:
            sg_id = sg["GroupId"]
            if sg.get("GroupName") == "default":
                logger.info(f"Skipping default Security Group {sg_id}.")
                continue
            try:
                # Disassociate the security group from all instances
                instances = self.ec2_client.describe_instances(
                    Filters=[{"Name": "instance.group-id", "Values": [sg_id]}]
                )["Reservations"]
                for instance in instances:
                    self.ec2_client.modify_instance_attribute(InstanceId=instance["InstanceId"], Groups=[])

                # Delete the security group
                self.ec2_client.delete_security_group(GroupId=sg_id)
                logger.info(f"Security Group {sg_id} has been deleted.")
            except self.ec2_client.exceptions.ClientError as e:
                logger.error(f"Failed to delete Security Group {sg_id}: {e}")

    def _get_vpc_dependencies(self, vpc_id):
        # Get subnets
        subnets = self.ec2_client.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])["Subnets"]

        # Get security groups
        security_groups = self.ec2_client.describe_security_groups(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])[
            "SecurityGroups"
        ]

        return {
            "Subnets": subnets,
            "SecurityGroups": security_groups,
            # Add other resources as needed
        }

    def _check_aws_credentials(self):
        logger.info("Checking AWS credentials")
        try:
            self.ec2_client.describe_regions()
        except botocore.exceptions.NoCredentialsError as err:
            raise EnvironmentError("AWS credentials are not properly configured.") from err
