from .configurations import Configuration
from .logging import setup_logger

configs = Configuration()
configs.load_configs()
