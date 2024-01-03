import logging

import colorlog


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
