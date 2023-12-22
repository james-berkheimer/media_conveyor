import logging
import os
from pathlib import Path
from typing import Any, Dict

import json5 as json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Configuration:
    def __init__(self, config_path: str = None) -> None:
        if config_path:
            self.configs_path = Path(config_path)
            logger.info(f"Configuration path set to {config_path}")
        else:
            media_conveyor = os.getenv("MEDIA_CONVEYOR")
            if media_conveyor is None:
                logger.error("No configuration path provided and MEDIA_CONVEYOR environment variable is not set.")
                raise ValueError("No configuration path provided and MEDIA_CONVEYOR environment variable is not set.")
            self.configs_path = Path(media_conveyor) / "configs"
            logger.info(f"Configuration path set to {self.configs_path}")

    def get_config_path(self, config_type: str) -> Path:
        config_path = self.configs_path / config_type
        if not config_path.exists():
            logger.error(f"Config directory not found: {config_path}")
            raise FileNotFoundError(f"Config directory not found: {config_path}")
        return config_path


class AWSConfigs(Configuration):
    def __init__(self) -> None:
        super().__init__()

    def resolve_state(self) -> Dict[str, Any]:
        aws_configs_path = self.get_config_path("aws")
        aws_state_data = {}
        config_files = [entry for entry in aws_configs_path.iterdir() if entry.is_file() and entry.suffix == ".json"]

        for config_file in config_files:
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

        return aws_state_data
