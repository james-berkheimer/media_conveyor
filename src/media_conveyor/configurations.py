import os
from pathlib import Path

import json5 as json


class Configuration:
    def __init__(self) -> None:
        self.configs_path = Path(os.getenv("MEDIA_CONVEYOR"))

    def get_config_path(self, config_type: str):
        config_path = self.configs_path / f"configs/{config_type}"
        if not config_path.exists():
            raise FileNotFoundError(f"Config directory not found: {config_path}")
        return config_path


class AWSConfigs(Configuration):
    def __init__(self) -> None:
        super().__init__()

    def resolve_state(self):
        aws_configs_path = self.get_config_path("aws")
        aws_state_data = {}
        config_files = [
            entry
            for entry in aws_configs_path.iterdir()
            if entry.is_file() and entry.suffix == ".json"
        ]

        for config_file in config_files:
            try:
                with open(config_file, "r") as file:
                    config_data = json.load(file)
                    # Use the filename (without extension) as the key
                    key = config_file.stem
                    aws_state_data[key] = config_data
            except (json.JSONDecodeError, FileNotFoundError) as e:
                # Handle JSON decoding errors or missing files
                raise ValueError(f"Error processing {config_file}: {e}") from e

        return aws_state_data
