import logging
import os
import sys
import time
from pathlib import Path
from pprint import pprint

import boto3
from botocore.exceptions import ParamValidationError

from ..authentication import AWSCredentials
from ..configurations import AWSConfigs
from ..infrastructure import AWSResourceCreator, AWSStateData
from ..utils import setup_logger

setup_logger(level="INFO")

media_conveyor_root = Path.home() / ".media_conveyor"
project_root = Path(__file__).resolve().parent.parent.parent.parent
os.environ["MEDIA_CONVEYOR"] = str(project_root / "tests/.media_conveyor")
credentials = AWSCredentials()
credentials.load()


def aws_run():
    # Step 1: Configure logging to print to the console
    # logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
    # print("Hello, world!")
    # ec2_client = boto3.client("ec2")
    # ec2_client.describe_regions()
    # response = ec2_client.describe_instances()
    # print(response.get("Reservations", []))

    aws_config = AWSConfigs()
    resource_configs = aws_config.resolve_state()
    # pprint(resource_configs)
    state_manager = AWSResourceCreator(resource_configs=resource_configs)
    state_manager.create_state()


def aws_stop():
    # logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])

    aws_config = AWSConfigs()
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


def _is_dependent(sg):
    ec2_client = boto3.client("ec2")
    sg_id = sg["GroupId"]

    # Get the inbound rules
    inbound_rules = ec2_client.describe_security_group_rules(Filters=[{"Name": "group-id", "Values": [sg_id]}])[
        "SecurityGroupRules"
    ]

    # Check if any inbound rule references another security group
    for rule in inbound_rules:
        if "ReferencedGroupId" in rule:
            return True

    # Get the security group details
    sg_details = ec2_client.describe_security_groups(GroupIds=[sg_id])["SecurityGroups"][0]

    # Get the outbound rules
    outbound_rules = sg_details["IpPermissionsEgress"]

    # Check if any outbound rule references another security group
    for rule in outbound_rules:
        if "UserIdGroupPairs" in rule:
            for pair in rule["UserIdGroupPairs"]:
                if "GroupId" in pair:
                    return True

    # If no inbound or outbound rule references another security group, then the security group is not dependent
    return False


def verify_credentials(aws_access_key_id, aws_secret_access_key, region_name):
    try:
        # Create a session using your credentials
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=region_name
        )

        # Create an EC2 resource object using the session
        ec2_resource = session.resource("ec2")

        # Use the EC2 resource object to make a request
        # This will throw an exception if the credentials are not valid
        ec2_resource.instances.all().limit(1)

        print("Credentials are valid.")
    except Exception as e:
        print("Credentials are not valid.")
        print("Error:", e)
