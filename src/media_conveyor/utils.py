import logging
import os
import secrets
import string

import colorlog


def generate_password(length: int = 16):
    if length < 16 or length > 128:
        print("Password length should be between 16 and 128")
        return

    characters = string.ascii_letters + string.digits + "!&#$^<>-"
    while True:
        password = "".join(secrets.choice(characters) for _ in range(length))
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in "!&#$^<>-" for c in password)
        ):
            break

    return password


def setup_logger(name=None, level=logging.INFO):
    """Return a logger with a default ColoredFormatter."""
    formatter = colorlog.ColoredFormatter(
        # "%(log_color)s%(levelname)-6s%(reset)s %(blue)s%(message)s",
        "%(log_color)s%(levelname)s:%(reset)s %(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        secondary_log_colors={},
        style="%",
    )

    if name:
        logger = colorlog.getLogger(name)
    else:
        logger = logging.getLogger()

    # Check if the logger already has handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(level)

    return logger


def set_file_permissions(file_path):
    try:
        # Set the permissions of the file to chmod 400
        os.chmod(file_path, 0o400)
    except OSError as e:
        logging.error(f"Error setting permissions on file: {e}")
        return False
    return True
