"""Logging setup."""
import logging
import os


def configure_logging() -> None:
    """Configure process-wide logging once."""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
