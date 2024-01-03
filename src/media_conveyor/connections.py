from pydantic import BaseModel
from sshtunnel import BaseSSHTunnelForwarderError, SSHTunnelForwarder

from .logging import setup_logger

logger = setup_logger()


class TunnelConfig(BaseModel):
    ssh_hostname: str
    ssh_username: str
    ssh_key_filepath: str
    remote_hostname: str
    remote_port: int
    local_port: int


class SSHTunnel:
    def __init__(self, config: TunnelConfig):
        self.config = config
        try:
            self.server: SSHTunnelForwarder = SSHTunnelForwarder(
                (self.config.ssh_hostname, 22),
                ssh_username=self.config.ssh_username,
                ssh_pkey=self.config.ssh_key_filepath,
                remote_bind_address=(self.config.remote_hostname, self.config.remote_port),
                local_bind_address=("localhost", self.config.local_port),
            )
        except BaseSSHTunnelForwarderError as e:
            logger.error(f"Error setting up SSH tunnel: {e}")
            raise

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self) -> None:
        try:
            self.server.start()
            logger.info("SSH tunnel started successfully")
        except BaseSSHTunnelForwarderError as e:
            logger.error(f"Error starting SSH tunnel: {e}")
            raise

    def stop(self) -> None:
        try:
            self.server.stop()
            logger.info("SSH tunnel stopped successfully")
        except BaseSSHTunnelForwarderError as e:
            logger.error(f"Error stopping SSH tunnel: {e}")
            raise
