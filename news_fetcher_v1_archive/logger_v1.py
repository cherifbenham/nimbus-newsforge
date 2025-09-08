import logging
from logging import getLogger
import os
import google.cloud.logging


def get_logger():
    """Returns a singleton logger instance."""

    logger = logging.getLogger('my_app')

    if logger.handlers:  # Logger already configured
        return logger

    logger.setLevel(logging.DEBUG)

    # Choose handler based on environment
    if os.environ.get('K_SERVICE'):
        handler = google.cloud.logging.Client().get_default_handler()
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'))

    logger.addHandler(handler)
    return logger
