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

credentials = AWSCredentials()
credentials.load()

project_root = Path(__file__).resolve().parent.parent.parent.parent
os.environ["MEDIA_CONVEYOR"] = str(project_root / "tests")


def aws_run():
    # Step 1: Configure logging to print to the console
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])

    aws_config = AWSConfigs()
    resource_configs = aws_config.resolve_state()
    # pprint(resource_configs)
    state_manager = AWSResourceCreator(resource_configs)
    state_manager.create_state()


def aws_test():
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])

    # aws_config = AWSConfigs()
    # resource_configs = aws_config.resolve_state()
    # pprint(resource_configs)
    # state_manager = AWSResourceCreator(resource_configs)
    # print(state_manager.get_current_state())
    get_default_vpc()


def aws_stop():
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])

    aws_config = AWSConfigs()
    resource_configs = aws_config.resolve_state()
    state_manager = AWSResourceCreator(resource_configs)
    state_manager.terminate_state()


def get_default_vpc():
    # Create EC2 client
    ec2_client = boto3.client("ec2")

    # Describe the VPCs
    response = ec2_client.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])

    # Check if there is a default VPC
    if "Vpcs" in response and len(response["Vpcs"]) > 0:
        default_vpc_id = response["Vpcs"][0]["VpcId"]
        print(f"Default VPC ID: {default_vpc_id}")
    else:
        print("No default VPC found.")
