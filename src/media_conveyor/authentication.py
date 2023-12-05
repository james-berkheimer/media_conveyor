import os

import json5 as json


class Authentication:
    """
    A class representing a generic authentication mechanism.

    This class is designed to handle the loading of authentication data from a JSON file.

    Attributes:
        auth_file_path (str): The file path to the JSON file containing authentication data.
        auth_data (dict): A dictionary containing authentication data loaded from the JSON file.

    Methods:
        _resolve_auth(): Internal method to read and parse the authentication data from the specified file.

    """

    def __init__(self) -> None:
        """
        Initialize an Authentication object.

        Sets the file path for authentication data and loads the data using the internal _resolve_auth() method.
        """
        self.auth_file_path = f"{os.getenv('MEDIA_CONVEYOR')}/credentials.json"
        self.auth_data = self._resolve_auth()

    def _resolve_auth(self):
        """
        Internal method to read and parse the authentication data from the specified file.

        Returns:
            dict: A dictionary containing authentication data.
        """
        with open(self.auth_file_path) as auth_file:
            return json.load(auth_file)


class PlexAuthentication(Authentication):
    """
    A subclass of Authentication specifically tailored for Plex server authentication.

    This class extends the generic Authentication class to provide properties for accessing Plex server base URL
    and authentication token.

    Properties:
        baseurl (str): Retrieve the base URL of the Plex server from the authentication data.
        token (str): Retrieve the authentication token for accessing the Plex server API from the authentication data.
    """

    @property
    def baseurl(self) -> str:
        """
        Retrieve the base URL of the Plex server from the authentication data.

        Returns:
            str: The base URL of the Plex server.
        """
        return self.auth_data["plex"]["baseurl"]

    @property
    def token(self) -> str:
        """
        Retrieve the authentication token for accessing the Plex server API from the authentication data.

        Returns:
            str: The authentication token.
        """
        return self.auth_data["plex"]["token"]
