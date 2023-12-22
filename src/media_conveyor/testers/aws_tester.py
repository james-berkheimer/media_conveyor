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

    verify_credentials(
        aws_access_key_id="AKIASD2LQCWVVVAUJ74A",
        aws_secret_access_key="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",
        region_name="us-east-1",
    )


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
