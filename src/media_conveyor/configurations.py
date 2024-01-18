import json
import os
from pathlib import Path
from typing import Any, Dict

from .logging import setup_logger

logger = setup_logger()


class Configuration:
    def __init__(self) -> None:
        media_conveyor = os.getenv("MEDIA_CONVEYOR")
        if media_conveyor is None or not (Path(media_conveyor) / "configurations.json").exists():
            project_root = Path(__file__).resolve().parents[2]
            media_conveyor = str(project_root / "tests/.media_conveyor")
            os.environ["MEDIA_CONVEYOR"] = media_conveyor
            logger.info(
                f"MEDIA_CONVEYOR environment variable is not set or configurations.json not found. Defaulting to {media_conveyor}"
            )

        self.environment_path = Path(media_conveyor)
        logger.info(f"Configuration path set to {self.environment_path}")

        self.configs_path = self.environment_path / "configurations.json"
        self.infrastructure_configs_path = self.environment_path / "infrastructure_configs"
        self.state_path = self.environment_path / "state"

    def load_configs(self):
        logger.info(f"Loading configurations from {self.configs_path}")
        try:
            with open(self.configs_path, "r") as file:
                config_data = json.load(file)
                credentials = config_data.get("credentials", {})
                paths = config_data.get("paths", {})

                # Set AWS credentials as environment variables
                aws_credentials = credentials.get("aws", {})
                for key, value in aws_credentials.items():
                    os.environ[f"aws_{key}".upper()] = value

                # Set Plex credentials as environment variables
                plex_credentials = credentials.get("plex", {})
                for key, value in plex_credentials.items():
                    os.environ[f"plex_{key}".upper()] = value

                # Set paths as environment variables
                for key, value in paths.items():
                    os.environ[f"paths_{key}".upper()] = value

        except FileNotFoundError:
            logger.error(f"Configuration file not found at {self.configs_path}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from {self.configs_path}")
            raise


class AWSConfigs(Configuration):
    def __init__(self) -> None:
        super().__init__()

    def get_state_path(self, resource_type: str) -> Path:
        environment_path = self.infrastructure_configs_path / resource_type
        if not environment_path.exists():
            logger.error(f"Config directory not found: {environment_path}")
            raise FileNotFoundError(f"Config directory not found: {environment_path}")
        logger.info(f"Resolved state path for {resource_type}: {environment_path}")
        return environment_path

    def resolve_state(self) -> Dict[str, Any]:
        aws_states_path = self.get_state_path("aws")
        aws_state_data = {}
        state_files = [entry for entry in aws_states_path.iterdir() if entry.is_file() and entry.suffix == ".json"]

        for config_file in state_files:
            try:
                with open(config_file, "r") as file:
                    config_data = json.load(file)
                    # Use the filename (without extension) as the key
                    key = config_file.stem
                    aws_state_data[key] = config_data
                    logger.info(f"Loaded configuration from {config_file}")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                # Handle JSON decoding errors or missing files
                logger.error(f"Error processing {config_file}: {e}")
                raise ValueError(f"Error processing {config_file}: {e}") from e

        logger.info(f"Resolved AWS state: {aws_state_data}")
        return aws_state_data
