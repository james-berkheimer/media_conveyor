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


def aws_run():
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    # print(project_root / "tests")
    os.environ["MEDIA_CONVEYOR"] = str(project_root / "tests")
    # Step 1: Configure logging to print to the console
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])

    aws_config = AWSConfigs()
    resource_configs = aws_config.resolve_state()
    # pprint(resource_configs)
    state_manager = AWSResourceCreator(resource_configs)
    state_manager.create_state()


def aws_test():
    # Replace 'your-instance-id' with the actual ID of your EC2 instance
    instance_id = "i-05a6aac79c1351c6c"
    vpc_id = "vpc-0712201d8f67243ff"  # Replace with the actual ID of your VPC

    ec2_client = boto3.client("ec2")

    try:
        # Check if instance exists
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        instances = response["Reservations"]

        if not instances:
            print(f"Instance {instance_id} does not exist.")
            return  # Exit the method

        # Terminate EC2 instance
        response = ec2_client.terminate_instances(InstanceIds=[instance_id])
        terminating_instances = response["TerminatingInstances"]

        for instance in terminating_instances:
            instance_id = instance["InstanceId"]
            current_state = instance["CurrentState"]["Name"]
            previous_state = instance["PreviousState"]["Name"]

            print(
                f"Instance {instance_id} transitioning from '{previous_state}' to '{current_state}'"
            )

            # Wait until the specific instance is terminated with a progress bar
            waiter = ec2_client.get_waiter("instance_terminated")
            waiter.wait(InstanceIds=[instance_id])
            print(f"Instance {instance_id} has been terminated.")

        # Check if VPC has dependencies
        response = ec2_client.describe_vpc_attribute(VpcId=vpc_id)
        dependencies = response["Dependencies"]

        if dependencies:
            print(f"VPC {vpc_id} has dependencies and cannot be deleted directly.")
            print("Deleting subnets before deleting the VPC...")

            # Delete subnets
            response = ec2_client.describe_subnets(
                Filters=[{"Name": "vpc-id", "Values": [vpc_id]}]
            )
            subnets = response["Subnets"]

            for subnet in subnets:
                subnet_id = subnet["SubnetId"]
                print(f"Deleting subnet {subnet_id}...")
                ec2_client.delete_subnet(SubnetId=subnet_id)
                print(f"Subnet {subnet_id} has been deleted.")

            # Retry deleting VPC
            response = ec2_client.delete_vpc(VpcId=vpc_id)
            print(f"VPC {vpc_id} has been terminated.")

        else:
            # Terminate VPC resource
            response = ec2_client.delete_vpc(VpcId=vpc_id)
            print(f"VPC {vpc_id} has been terminated.")

    except ec2_client.exceptions.ClientError as e:
        print(f"Error terminating EC2 instance or VPC: {e}")
    except ParamValidationError as e:
        print(f"Parameter validation error: {e}")


def aws_stop():
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])

    # aws_config = AWSConfigs()
    # resource_configs = aws_config.resolve_state()
    # pprint(resource_configs)
    state_manager = AWSResourceCreator()
    state_manager.terminate_state()
