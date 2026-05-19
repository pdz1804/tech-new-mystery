"""Logging configuration for the application.

This module configures comprehensive logging for the entire application,
including file rotation, console output, and structured logging for debugging.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from app.config import settings


def configure_logging() -> None:
    """Configure application logging with file and console handlers.

    Sets up:
    - Console handler for INFO+ level with detailed formatting
    - File handler for DEBUG+ level with rotation
    - Separate loggers for key components
    - Debug logging only in development environment
    """
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    log_level = logging.DEBUG if settings.debug else logging.INFO

    detailed_format = (
        "%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - "
        "[%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s"
    )
    simple_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Console handler - INFO level
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(simple_format, datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler - DEBUG level with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(detailed_format, datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # API logger
    api_logger = logging.getLogger("app.api")
    api_file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "api.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
    )
    api_file_handler.setLevel(logging.DEBUG)
    api_file_handler.setFormatter(file_formatter)
    api_logger.addHandler(api_file_handler)

    # Services logger
    services_logger = logging.getLogger("app.services")
    services_file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "services.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
    )
    services_file_handler.setLevel(logging.DEBUG)
    services_file_handler.setFormatter(file_formatter)
    services_logger.addHandler(services_file_handler)

    # Database logger
    db_logger = logging.getLogger("app.repositories")
    db_file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "database.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
    )
    db_file_handler.setLevel(logging.DEBUG)
    db_file_handler.setFormatter(file_formatter)
    db_logger.addHandler(db_file_handler)

    # Integrations logger
    integrations_logger = logging.getLogger("app.integrations")
    integrations_file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / "integrations.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=10,
    )
    integrations_file_handler.setLevel(logging.DEBUG)
    integrations_file_handler.setFormatter(file_formatter)
    integrations_logger.addHandler(integrations_file_handler)

    root_logger.info(f"Logging configured - Level: {logging.getLevelName(log_level)}, Debug: {settings.debug}")
