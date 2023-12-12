import os
from pathlib import Path

import json5 as json


class Configuration:
    def __init__(self) -> None:
        self.configs_path = Path(os.getenv("MEDIA_CONVEYOR"))


class AWSConfigs(Configuration):
    def __init__(self) -> None:
        super().__init__()

    def resolve_state(self):
        aws_configs_path = self.configs_path / "configs/aws"

        if not aws_configs_path.exists():
            raise FileNotFoundError(f"Config directory not found: {aws_configs_path}")

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
                raise ValueError(f"Error processing {config_file}: {e}")

        return aws_state_data
