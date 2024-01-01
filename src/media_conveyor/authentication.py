import copy
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import boto3
import json5
from botocore.exceptions import BotoCoreError, ClientError

# logging.basicConfig(level=logging.INFO)
from .utils import setup_logger

logger = setup_logger()


class Authentication:
    def __init__(self, auth_data: Optional[Dict[str, Any]] = None) -> None:
        media_conveyor = os.getenv("MEDIA_CONVEYOR")
        if not media_conveyor:
            raise ValueError("MEDIA_CONVEYOR environment variable not set")

        media_conveyor_path = Path(media_conveyor)
        if not media_conveyor_path.exists():
            raise ValueError(f"Credentials file not found: {media_conveyor_path}")

        self.auth_file_path = media_conveyor_path / "credentials.json"
        self.auth_data = auth_data if auth_data is not None else self._resolve_auth()
        logging.info(f"Authentication initialized with auth_data: {self._mask_auth_data()}")

    def _resolve_auth(self) -> Dict[str, Any]:
        if not os.path.exists(self.auth_file_path):
            logging.error(f"Credentials file not found: {self.auth_file_path}")
            raise ValueError(f"Credentials file not found: {self.auth_file_path}")

        with open(self.auth_file_path) as auth_file:
            return json5.load(auth_file)

    def _mask_auth_data(self) -> Dict[str, Any]:
        # Mask sensitive data in auth_data for logging
        masked_auth_data = copy.deepcopy(self.auth_data)
        for service in masked_auth_data:
            for key in masked_auth_data[service]:
                if "token" in key or "key" in key:
                    masked_auth_data[service][key] = "****"
        return masked_auth_data


class PlexAuthentication(Authentication):
    def __init__(self, baseurl: Optional[str] = None, token: Optional[str] = None) -> None:
        if baseurl and token:
            auth_data = {"plex": {"baseurl": baseurl, "token": token}}
        else:
            auth_data = None
            logging.warning("No auth data provided for PlexAuthentication, falling back to credentials.json")

        super().__init__(auth_data=auth_data)
        logging.info("PlexAuthentication initialized")

    @property
    def baseurl(self) -> str:
        return self.auth_data["plex"]["baseurl"]

    @property
    def token(self) -> str:
        return self.auth_data["plex"]["token"]


class AWSCredentials(Authentication):
    def __init__(
        self,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        region_name: Optional[str] = None,
    ) -> None:
        if access_key_id and secret_access_key and region_name:
            auth_data = {
                "aws": {
                    "access_key_id": access_key_id,
                    "secret_access_key": secret_access_key,
                    "region_name": region_name,
                }
            }
        else:
            auth_data = None
            logging.info("No auth data provided for AWSCredentials, falling back to credentials.json")

        super().__init__(auth_data=auth_data)
        logging.info("AWSCredentials initialized")

    def load(self) -> None:
        os.environ["AWS_ACCESS_KEY_ID"] = self.auth_data["aws"]["access_key_id"]
        os.environ["AWS_SECRET_ACCESS_KEY"] = self.auth_data["aws"]["secret_access_key"]
        os.environ["AWS_DEFAULT_REGION"] = self.auth_data["aws"]["region_name"]
        logging.info("AWS credentials loaded")
        self.verify_credentials()

    def verify_credentials(self, aws_access_key_id=None, aws_secret_access_key=None, region_name=None):
        # If no arguments are provided, use the instance's auth_data
        if aws_access_key_id is None:
            aws_access_key_id = self.auth_data["aws"]["access_key_id"]
        if aws_secret_access_key is None:
            aws_secret_access_key = self.auth_data["aws"]["secret_access_key"]
        if region_name is None:
            region_name = self.auth_data["aws"]["region_name"]

        try:
            logging.info("Verifying AWS credentials")
            # Create a session using your credentials
            session = boto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name,
            )

            # Create an EC2 resource object using the session
            ec2_resource = session.resource("ec2")

            # Use the EC2 resource object to make a request
            # This will throw an exception if the credentials are not valid
            ec2_resource.instances.all().limit(1)

            logging.info("AWS credentials are valid.")
            return True
        except (BotoCoreError, ClientError) as e:
            logging.error("AWS credentials are not valid.")
            logging.error("Error: %s", e)
            return False
