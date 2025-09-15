import logging
import sys
from typing import Any
from core.config import settings


def setup_logging() -> None:
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f"{settings.storage_path}/app.log")
        ]
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name)


# Setup logging on import
setup_logging()
