import os

import json5 as json


class Authentication:
    def __init__(self) -> None:
        self.auth_file_path = f"{os.getenv('MEDIA_CONVEYOR')}/credentials.json"
        print(self.auth_file_path)
        self.auth_data = self._resolve_auth()

    def _resolve_auth(self):
        if not os.path.exists(self.auth_file_path):
            raise ValueError(f"Credentials file not found: {self.auth_file_path}")

        with open(self.auth_file_path) as auth_file:
            return json.load(auth_file)


class PlexAuthentication(Authentication):
    @property
    def baseurl(self) -> str:
        return self.auth_data["plex"]["baseurl"]

    @property
    def token(self) -> str:
        return self.auth_data["plex"]["token"]


class AWSCredentials(Authentication):
    def __init__(self) -> None:
        super().__init__()

    def load(self):
        os.environ["AWS_ACCESS_KEY_ID"] = self.auth_data["aws"]["access_key_id"]
        os.environ["AWS_SECRET_ACCESS_KEY"] = self.auth_data["aws"]["secret_access_key"]
        os.environ["AWS_DEFAULT_REGION"] = self.auth_data["aws"]["region_name"]
