import logging
import os
import sys
from pprint import pprint

import boto3

from ..authentication import AWSCredentials
from ..configurations import AWSConfigs
from ..infrastructure import AWSState

credentials = AWSCredentials()
credentials.load()


def aws_run():
    # Step 1: Configure logging to print to the console
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])

    aws_config = AWSConfigs()
    aws_state = aws_config.resolve_state()
    # pprint(aws_state)
    state_manager = AWSState(aws_state)
    state_manager.create_state()


def aws_test():
    instance_id = sys.argv[1]
    # You can also describe the instance to get more information
    ec2 = boto3.client("ec2")
    instance_description = ec2.describe_instances(InstanceIds=[instance_id])
    pprint(instance_description)


def aws_stop():
    instance_id = sys.argv[1]
    terminate = sys.argv[2]
    ec2 = boto3.client("ec2")
    if terminate:
        ec2.terminate_instances(InstanceIds=[instance_id])
        print(f"Instance {instance_id} is terminating.")
    else:
        ec2.stop_instances(InstanceIds=[instance_id])
        print(f"Instance {instance_id} is stopping.")
