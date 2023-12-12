import boto3


def aws_run():
    # Create an EC2 client
    ec2 = boto3.client("ec2")

    # Create an ElastiCache client
    elasticache = boto3.client("elasticache")

    # Specify the VPC parameters
    vpc_params = {
        "CidrBlock": "10.0.0.0/16",  # Replace with your desired CIDR block
        "InstanceTenancy": "default",
    }

    # Create the VPC
    vpc = ec2.create_vpc(**vpc_params)
    vpc_id = vpc["Vpc"]["VpcId"]
    print(f"VPC {vpc_id} created.")

    # Specify the parameters for the subnet
    subnet_params = {
        "CidrBlock": "10.0.0.0/24",  # Replace with your desired CIDR block for the subnet
        "VpcId": vpc_id,
        "AvailabilityZone": "us-east-1a",  # Replace with your desired availability zone
    }

    # Create the subnet
    subnet = ec2.create_subnet(**subnet_params)
    subnet_id = subnet["Subnet"]["SubnetId"]
    print(f"Subnet {subnet_id} created.")

    # Specify the parameters for the instance
    instance_params = {
        "ImageId": "ami-0da7657fe73215c0c",  # AMI ID for your desired operating system
        "InstanceType": "t2.micro",  # Free tier eligible instance type
        "MinCount": 1,
        "MaxCount": 1,
        "SubnetID": subnet_id,
    }

    # Launch the instance
    response = ec2.run_instances(**instance_params)

    # Retrieve the instance ID
    instance_id = response["Instances"][0]["InstanceId"]

    print(f"Instance {instance_id} is launching.")

    # Add a wait to check if the instance has started
    ec2.get_waiter("instance_running").wait(InstanceIds=[instance_id])

    print(f"Instance {instance_id} is running.")

    # Specify the parameters for the ElastiCache cluster
    elasticache_params = {
        "CacheClusterId": "my-cache-cluster",
        "CacheNodeType": "cache.t2.micro",
        "Engine": "redis",
        "NumCacheNodes": 1,
        "VpcSecurityGroupIds": [
            vpc_id
        ],  # Attach the VPC security group to the ElastiCache cluster
    }

    # Create the ElastiCache cluster
    elasticache.create_cache_cluster(**elasticache_params)
    print(f'ElastiCache cluster {elasticache_params["CacheClusterId"]} created.')
