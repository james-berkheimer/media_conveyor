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
from ..infrastructure import AWSResourceCreator

media_conveyor_root = Path.home() / ".media_conveyor"
project_root = Path(__file__).resolve().parent.parent.parent.parent
os.environ["MEDIA_CONVEYOR"] = str(project_root / "tests/.media_conveyor")
credentials = AWSCredentials()
credentials.load()


def aws_run():
    # Step 1: Configure logging to print to the console
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
    # print("Hello, world!")
    # ec2_client = boto3.client("ec2")
    # ec2_client.describe_regions()
    # response = ec2_client.describe_instances()
    # print(response.get("Reservations", []))

    aws_config = AWSConfigs()
    resource_configs = aws_config.resolve_state()
    # pprint(resource_configs)
    state_manager = AWSResourceCreator(resource_configs)
    state_manager.create_state()


def aws_stop():
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])

    aws_config = AWSConfigs()
    resource_configs = aws_config.resolve_state()
    state_manager = AWSResourceCreator(resource_configs)
    state_manager.terminate_state()


def aws_test():
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
    aws_config = AWSConfigs()
    resource_configs = aws_config.resolve_state()
    state_manager = AWSResourceCreator(resource_configs)
    # state_manager._terminate_ec2_instance()
    # state_manager._terminate_elasticache_cluster()
    # state_manager._delete_cache_subnet_group()
    state_manager._delete_vpc()

    # vpc_id = state_manager.current_state["VpcId"]
    # dependencies = state_manager._get_vpc_dependencies(vpc_id)
    # security_groups = dependencies["SecurityGroups"]
    # state_manager._delete_security_groups(security_groups)

    # sg_dependent = [sg for sg in security_groups if _is_dependent(sg)]
    # sg_independent = [sg for sg in security_groups if not _is_dependent(sg)]
    # for sg_list in [sg_dependent, sg_independent]:
    #     for sg in sg_list:
    #         sg_id = sg["GroupId"]
    #         sg_name = sg["GroupName"]
    #         print(sg_id, sg_name)

    # for sg in security_groups:
    #     sg_id = sg["GroupId"]
    #     sg_name = sg["GroupName"]
    #     if sg_name == "default":
    #         continue
    #     sg_tags = sg["Tags"]
    #     print(sg_id, sg_name, sg_tags[0]["Value"])
    # if sg_name == "MC_RedisSecurityGroup":
    # if sg_name == "MC_EC2SecurityGroup":
    #     state_manager.ec2_client.delete_security_group(GroupId=sg_id)

    #     response = state_manager.ec2_client.describe_network_interfaces(
    #         # Filters=[{"Name": "group-id", "Values": [sg_id]}]
    #     )
    #     pprint(response["NetworkInterfaces"])


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
