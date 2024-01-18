import copy
import os
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .logging import setup_logger

logger = setup_logger()


class Authentication:
    def __init__(self) -> None:
        logger.info("Starting authentication process")
        self.auth_data = self._resolve_auth()
        if not self.auth_data:
            raise ValueError("Authentication data could not be resolved from environment variables.")
        logger.info(f"Authentication initialized with auth_data: {self._mask_auth_data()}")

    def _resolve_auth(self) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses should implement this!")

    def _mask_auth_data(self) -> Dict[str, Any]:
        # Mask sensitive data in auth_data for logger
        masked_auth_data = copy.deepcopy(self.auth_data)
        for service in masked_auth_data:
            for key in masked_auth_data[service]:
                if "token" in key or "key" in key:
                    masked_auth_data[service][key] = "****"
        return masked_auth_data


class PlexAuthentication(Authentication):
    def __init__(self) -> None:
        super().__init__()
        logger.info("PlexAuthentication initialized")

    def _resolve_auth(self) -> Dict[str, Any]:
        baseurl = os.getenv("PLEX_BASEURL")
        token = os.getenv("PLEX_TOKEN")
        if not baseurl:
            logger.error("PLEX_BASEURL environment variable is not set.")
        if not token:
            logger.error("PLEX_TOKEN environment variable is not set.")
        if not baseurl or not token:
            raise ValueError("PLEX_BASEURL and PLEX_TOKEN environment variables must be set.")
        return {
            "plex": {
                "baseurl": baseurl,
                "token": token,
            }
        }

    @property
    def baseurl(self) -> str:
        return self.auth_data["plex"]["baseurl"]

    @property
    def token(self) -> str:
        return self.auth_data["plex"]["token"]


class AWSCredentials(Authentication):
    def __init__(self) -> None:
        super().__init__()
        logger.info("AWSCredentials initialized")

    def _resolve_auth(self) -> Dict[str, Any]:
        access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        region_name = os.getenv("AWS_DEFAULT_REGION")
        if not access_key_id:
            logger.error("AWS_ACCESS_KEY_ID environment variable is not set.")
        if not secret_access_key:
            logger.error("AWS_SECRET_ACCESS_KEY environment variable is not set.")
        if not region_name:
            logger.error("AWS_DEFAULT_REGION environment variable is not set.")
        if not access_key_id or not secret_access_key or not region_name:
            raise ValueError(
                "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_DEFAULT_REGION environment variables must be set."
            )
        return {
            "aws": {
                "access_key_id": access_key_id,
                "secret_access_key": secret_access_key,
                "region_name": region_name,
            }
        }

    def verify_credentials(self):
        try:
            logger.info("Verifying AWS credentials")
            # Create a session using your credentials
            session = boto3.Session(
                aws_access_key_id=self.auth_data["aws"]["access_key_id"],
                aws_secret_access_key=self.auth_data["aws"]["secret_access_key"],
                region_name=self.auth_data["aws"]["region_name"],
            )

            # Create an EC2 resource object using the session
            ec2_resource = session.resource("ec2")

            # Use the EC2 resource object to make a request
            # This will throw an exception if the credentials are not valid
            ec2_resource.instances.all().limit(1)

            logger.info("AWS credentials are valid.")
            return True
        except (BotoCoreError, ClientError) as e:
            logger.error("AWS credentials are not valid.")
            logger.error("Error: %s", e)
            raise e
