from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Tuple

import boto3
import botocore
from botocore.exceptions import BotoCoreError, ClientError

from .exceptions import TerminationError
from .utils import generate_password, set_file_permissions, setup_logger

logger = setup_logger()


class AWSBase:
    def __init__(self, aws_state_path: str = None, resource_configs: dict = None):
        if resource_configs is None:
            resource_configs = {}
        self.resource_configs = resource_configs
        self.media_conveyor_path = Path(os.getenv("MEDIA_CONVEYOR"))

        if aws_state_path is None:
            if self.media_conveyor_path is None:
                raise EnvironmentError("The MEDIA_CONVEYOR environment variable is not set.")
            self.aws_state_path = self.media_conveyor_path / "aws_state.json"
        else:
            self.aws_state_path = aws_state_path

        self.ec2_client = boto3.client("ec2")
        self.elasticache_client = boto3.client("elasticache")

    @property
    def current_state(self):
        # logger.info("Accessing current_state property")
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
            set_file_permissions(self.aws_state_path)
        except IOError:
            logger.error("Failed to write to the AWS state file. Check your file permissions.")

    def get_current_state(self):
        logger.info("Getting current AWS state")
        return self.current_state

    def _check_aws_credentials(self):
        logger.info("Checking AWS credentials")
        try:
            self.ec2_client.describe_regions()
        except botocore.exceptions.NoCredentialsError as err:
            raise EnvironmentError("AWS credentials are not properly configured.") from err


class AWSStateData(AWSBase):
    def get_elasticache_endpoint_and_port(self):
        replication_group_id = self.current_state.get("ReplicationGroupId", None)
        if replication_group_id is None:
            logger.error("Replication group ID not found in current state.")
            return None

        try:
            response = self.elasticache_client.describe_replication_groups(ReplicationGroupId=replication_group_id)
        except Exception as e:
            logger.error(f"Failed to describe replication groups: {e}")
            return None

        # Assuming the replication group exists and has nodes
        replication_group = response["ReplicationGroups"][0]
        node_group = replication_group["NodeGroups"][0]
        node_group_member = node_group["NodeGroupMembers"][0]

        endpoint = node_group_member["ReadEndpoint"]["Address"]
        port = node_group_member["ReadEndpoint"]["Port"]

        logger.info(f"Retrieved endpoint: {endpoint} and port: {port} for replication group: {replication_group_id}")

        return endpoint, port

    def redis_params(self, db_number: int = 0) -> dict:
        logger.info("Accessing redis_params property")
        endpoint, port = self.get_elasticache_endpoint_and_port()
        return {"host": endpoint, "port": port, "db": db_number}


class AWSResourceCreator(AWSBase):
    def create_state(self):
        logger.info(">------------ Creating new AWS state ------------<")
        vpc_id = self._create_vpc()
        subnet_id = self._create_subnet(vpc_id)
        internet_gateway_id = self._create_internet_gateway(vpc_id)
        route_table_id = self._modify_route_table(vpc_id, internet_gateway_id)
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
            "SecurityGroupIds": [ec2_security_group_id, cache_security_group_id],
            "CacheSubnetGroupName": cache_subnet_group_name,
            "InstanceIds": [instance_id],
            "CacheClusterId": cluster_id,
            "InternetGatewayId": internet_gateway_id,
            "RouteTableId": route_table_id,
        }

        self.current_state = state_data

    def terminate_state(self):
        logger.info("<------------ Terminating AWS state ------------>")
        if self.current_state is None:
            return
        try:
            self._terminate_ec2_instance()
            self._terminate_elasticache_cluster()
            self._delete_cache_subnet_group()
            self._delete_subnets()
            self._delete_security_groups()
            self._delete_internet_gateways()
            self._delete_route_tables()
            self._delete_vpc()

            # Clean up files after successful termination
            if os.path.exists(self.aws_state_path):
                try:
                    os.remove(self.aws_state_path)
                    logger.info("aws_state.json removed successfully")
                except Exception as e:
                    logger.error(f"Failed to remove aws_state.json. Error: {str(e)}")
            else:
                logger.info("aws_state.json does not exist")

            key_pair_path = self.media_conveyor_path / "mc_key_pair.pem"
            if key_pair_path.exists():
                try:
                    os.remove(key_pair_path)
                    logger.info(f"{key_pair_path} removed successfully")
                except Exception as e:
                    logger.error(f"Failed to remove {key_pair_path}. Error: {str(e)}")
            else:
                logger.info(f"{key_pair_path} does not exist")
            self._delete_key_pair()

        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to terminate state. Error: {str(e)}")
            raise TerminationError(str(e)) from e

    def _delete_key_pair(self):
        try:
            response = self.ec2_client.delete_key_pair(KeyName="mc_key_pair")
            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                logger.info("Key pair 'mc_key_pair' deleted successfully")
            else:
                logger.error("Failed to delete key pair 'mc_key_pair'")
        except Exception as e:
            logger.error(f"Failed to delete key pair 'mc_key_pair'. Error: {str(e)}")

    def _create_vpc(self) -> str:
        logger.info("Creating VPC")
        vpc_id = self._create_resource(self.ec2_client, "create_vpc", self.resource_configs.get("vpc", {}), "Vpc")
        logger.info("Enabling DNS hostnames")
        self.ec2_client.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={"Value": True})
        return vpc_id

    def _create_subnet(self, vpc_id) -> str:
        logger.info("Creating subnet for VPC: %s", vpc_id)
        params = self.resource_configs.get("subnet", {})
        params["VpcId"] = vpc_id
        return self._create_resource(self.ec2_client, "create_subnet", params, "Subnet")

    def _create_internet_gateway(self, vpc_id: str) -> str:
        logger.info("Creating Internet Gateway")
        igw_id = self._create_resource(self.ec2_client, "create_internet_gateway", {}, "InternetGateway")

        logger.info("Attaching Internet Gateway to VPC")
        self.ec2_client.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)

        return igw_id

    def _modify_route_table(self, vpc_id: str, igw_id: str):
        logger.info("Modifying Route Table")
        route_tables = self.ec2_client.describe_route_tables(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])[
            "RouteTables"
        ]
        if route_tables:
            route_table_id = route_tables[0]["RouteTableId"]
            self.ec2_client.create_route(
                RouteTableId=route_table_id, DestinationCidrBlock="0.0.0.0/0", GatewayId=igw_id
            )
        return route_table_id

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

    def _create_key_pair(self):
        key_pair_name = "mc_key_pair"
        try:
            print(f"Creating key pair {key_pair_name}")
            key_pair = self.ec2_client.create_key_pair(KeyName=key_pair_name)
            private_key = key_pair["KeyMaterial"]
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Error creating key pair: {e}")
            return None

        key_pair_file = f"{key_pair_name}.pem"
        key_pair_path = self.media_conveyor_path / key_pair_file

        try:
            with open(f"{key_pair_path}", "w") as file:
                file.write(private_key)
        except IOError as e:
            logger.error(f"Error writing to key pair file: {e}")
            return None

        set_file_permissions(key_pair_path)

        logger.info(f"Key pair {key_pair_file} created and stored in {self.media_conveyor_path}")
        return key_pair_name

    def _create_ec2_instance(self, subnet_id, ec2_security_group_id) -> str:
        logger.info(
            "Creating EC2 instance for subnet: %s and security group: %s",
            subnet_id,
            ec2_security_group_id,
        )
        key_pair_name = self._create_key_pair()
        params = self.resource_configs.get("ec2", {})
        params["NetworkInterfaces"] = [
            {
                "DeviceIndex": 0,
                "SubnetId": subnet_id,
                "Groups": [ec2_security_group_id],
                "AssociatePublicIpAddress": True,
            }
        ]
        params["KeyName"] = key_pair_name
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

    def _create_elasticache_replication_group(self, subnet_id, vpc_id, cache_security_group_id) -> Tuple[str, str]:
        logger.info(
            "Creating ElastiCache replication group for subnet: %s, VPC: %s and security group: %s",
            subnet_id,
            vpc_id,
            cache_security_group_id,
        )

        params = self.resource_configs.get("elasticache_replication_group", {})
        cache_subnet_group_name = self._create_cache_subnet_group(subnet_id, vpc_id)
        params["CacheSubnetGroupName"] = cache_subnet_group_name
        if params["CacheSubnetGroupName"] is None:
            return None
        params["SecurityGroupIds"] = [cache_security_group_id]
        auth_token = generate_password()
        params["AuthToken"] = auth_token
        replication_group_id = self._create_resource(
            self.elasticache_client,
            "create_replication_group",
            params,
            "ReplicationGroup",
        )
        return cache_subnet_group_name, replication_group_id, auth_token

    def _create_elasticache_cluster(self, subnet_id, vpc_id, cache_security_group_id) -> Tuple[str, str]:
        logger.info(
            "Creating ElastiCache cluster for subnet: %s, VPC: %s and security group: %s",
            subnet_id,
            vpc_id,
            cache_security_group_id,
        )

        params = self.resource_configs.get("elasticache_cluster", {})
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
            elif resource_type == "ReplicationGroup":
                resource_id = response[resource_type][resource_type + "Id"]
            else:
                resource_id = response[resource_type][resource_type + "Id"]
            logger.info(f"{resource_type.capitalize()} created successfully. Id: {resource_id}")
            return resource_id
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to create {resource_type}. Error: {str(e)}")
            return None

    def _terminate_ec2_instance(self):
        logger.info("Terminating EC2 instance")
        instance_ids = self.current_state.get("InstanceIds", [])
        if not instance_ids:
            logger.warning("InstanceIds key not found.")
            return

        instance_ids = self.current_state["InstanceIds"]
        if instance_ids == [None]:
            logger.warning("No instance ids.")
            return

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
        logger.info("Terminating ElastiCache cluster")
        cluster_id = self.current_state.get("CacheClusterId", [])
        if not cluster_id:
            logger.warning("CacheClusterId key not found.")
            return

        if cluster_id is None:
            logger.warning("No cluster group id.")
            return

        try:
            response = self.elasticache_client.describe_cache_clusters(CacheClusterId=cluster_id)
        except self.elasticache_client.exceptions.CacheClusterNotFoundFault:
            logger.info(f"ElastiCache cluster {cluster_id} does not exist.")
            return

        cluster_status = response["CacheClusters"][0]["CacheClusterStatus"]
        if cluster_status != "available":
            logger.info(f"ElastiCache cluster {cluster_id} is not in 'available' state.")
            return

        self.elasticache_client.delete_cache_cluster(CacheClusterId=cluster_id)

        waiter = self.elasticache_client.get_waiter("cache_cluster_deleted")
        waiter.wait(CacheClusterId=cluster_id)
        logger.info(f"ElastiCache cluster {cluster_id} has been terminated.")

    def _terminate_elasticache_replication_group(self):
        logger.info("Terminating ElastiCache replication group")
        replication_group_id = self.current_state.get("ReplicationGroupId", [])
        if not replication_group_id:
            logger.warning("ReplicationGroupId key not found.")
            return

        if replication_group_id is None:
            logger.warning("No replication group id.")
            return
        try:
            response = self.elasticache_client.describe_replication_groups(ReplicationGroupId=replication_group_id)
        except self.elasticache_client.exceptions.ReplicationGroupNotFoundFault:
            logger.info(f"ElastiCache replication group {replication_group_id} does not exist.")
            return

        replication_group_status = response["ReplicationGroups"][0]["Status"]
        if replication_group_status != "available":
            logger.info(f"ElastiCache replication group {replication_group_id} is not in 'available' state.")
            return

        self.elasticache_client.delete_replication_group(ReplicationGroupId=replication_group_id)

        waiter = self.elasticache_client.get_waiter("replication_group_deleted")
        waiter.wait(ReplicationGroupId=replication_group_id)
        logger.info(f"ElastiCache replication group {replication_group_id} has been terminated.")

    def _delete_cache_subnet_group(self):
        logger.info("Deleting cache subnet group")
        cache_subnet_group_name = self.current_state.get("CacheSubnetGroupName", [])
        if not cache_subnet_group_name:
            logger.warning("CacheSubnetGroupName key not found.")
            return

        try:
            self.elasticache_client.describe_cache_subnet_groups(CacheSubnetGroupName=cache_subnet_group_name)
        except self.elasticache_client.exceptions.CacheSubnetGroupNotFoundFault:
            logger.warning(f"Cache subnet group {cache_subnet_group_name} does not exist.")
            return

        self.elasticache_client.delete_cache_subnet_group(CacheSubnetGroupName=cache_subnet_group_name)
        logger.info(f"Cache subnet group {cache_subnet_group_name} has been terminated.")

    def _delete_subnets(self):
        logger.info("Deleting Subnet")
        subnet_id = self.current_state.get("SubnetId", [])
        if not subnet_id:
            logger.warning("SubnetId key not found.")
            return

        try:
            # Check if the subnet exists
            self.ec2_client.describe_subnets(SubnetIds=[subnet_id])
        except self.ec2_client.exceptions.ClientError as e:
            if "InvalidSubnetID.NotFound" in str(e):
                logger.warning(f"Subnet {subnet_id} does not exist.")
                return
            else:
                raise

        try:
            self.ec2_client.delete_subnet(SubnetId=subnet_id)
            logger.info(f"Subnet {subnet_id} has been deleted.")
        except self.ec2_client.exceptions.ClientError as e:
            logger.error(f"Failed to delete subnet {subnet_id}: {e}")

    def _delete_security_groups(self):
        logger.info("Starting the deletion of Security Groups")
        security_group_ids = self.current_state.get("SecurityGroupIds", [])
        if not security_group_ids:
            logger.warning("No SecurityGroupIds found in the current state.")
            return

        # Get the descriptions of the security groups
        security_groups = self.ec2_client.describe_security_groups(GroupIds=security_group_ids)["SecurityGroups"]

        # Separate MC_RedisSecurityGroup from the other security groups
        sg_redis = [sg for sg in security_groups if sg["GroupName"] == "MC_RedisSecurityGroup"]
        other_sgs = [sg for sg in security_groups if sg["GroupName"] != "MC_RedisSecurityGroup"]

        logger.info(f"Found {len(sg_redis)} MC_RedisSecurityGroup and {len(other_sgs)} other Security Groups.")

        # Delete MC_RedisSecurityGroup first, then the other security groups
        for sg_list in [sg_redis, other_sgs]:
            for sg in sg_list:
                sg_id = sg["GroupId"]
                sg_name = sg["GroupName"]
                if sg.get("GroupName") == "default":
                    logger.info(f"Skipping default Security Group {sg_id}.")
                    continue
                try:
                    # Disassociate the security group from all instances
                    instances = self.ec2_client.describe_instances(
                        Filters=[{"Name": "instance.group-id", "Values": [sg_id]}]
                    )["Reservations"]
                    logger.debug(
                        f"Found {len(instances)} instances associated with Security Group {sg_id}. Disassociating..."
                    )

                    for instance in instances:
                        self.ec2_client.modify_instance_attribute(InstanceId=instance["InstanceId"], Groups=[])
                        logger.debug(f"Disassociated Security Group {sg_id} from instance {instance['InstanceId']}.")

                    # Delete the security group
                    self.ec2_client.delete_security_group(GroupId=sg_id)
                    logger.info(f"Successfully deleted Security Group {sg_name}:{sg_id}.")
                except self.ec2_client.exceptions.ClientError as e:
                    logger.error(f"Failed to delete Security Group {sg_id} due to: {e}")
        logger.info("Finished deleting Security Groups.")

    def _delete_internet_gateways(self):
        logger.info("Deleting Internet Gateway")
        internet_gateway_id = self.current_state.get("InternetGatewayId", [])
        vpc_id = self.current_state.get("VpcId", [])
        if not internet_gateway_id or not vpc_id:
            logger.warning("InternetGatewayId key not found.")
            return

        try:
            self.ec2_client.detach_internet_gateway(InternetGatewayId=internet_gateway_id, VpcId=vpc_id)
            self.ec2_client.delete_internet_gateway(InternetGatewayId=internet_gateway_id)
            logger.info(f"Internet Gateway {internet_gateway_id} has been deleted.")
        except self.ec2_client.exceptions.ClientError as e:
            logger.error(f"Failed to delete Internet Gateway {internet_gateway_id} due to: {e}")

    def _delete_route_tables(self):
        logger.info("Deleting Route Table")
        route_table_id = self.current_state.get("RouteTableId", [])
        if not route_table_id:
            logger.warning("RouteTableId key not found.")
            return

        try:
            route_table = self.ec2_client.describe_route_tables(RouteTableIds=[route_table_id])["RouteTables"][0]
            if route_table.get("Associations", [{}])[0].get("Main", False):
                logger.info(f"Route Table {route_table_id} is a main route table and cannot be deleted.")
            else:
                self.ec2_client.delete_route_table(RouteTableId=route_table_id)
                logger.info(f"Route Table {route_table_id} has been deleted.")
        except self.ec2_client.exceptions.ClientError as e:
            logger.error(f"Failed to delete Route Table {route_table_id} due to: {e}")

    def _delete_vpc(self):
        logger.info("Deleting VPC")
        vpc_id = self.current_state.get("VpcId", [])
        if not vpc_id:
            logger.warning("VpcId key not found.")
            return

        try:
            self.ec2_client.delete_vpc(VpcId=vpc_id)
            logger.info(f"VPC {vpc_id} has been deleted.")
        except self.ec2_client.exceptions.ClientError as e:
            logger.error(f"Failed to delete VPC {vpc_id} due to: {e}")
