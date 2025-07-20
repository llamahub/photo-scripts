"""Common logging framework for all projects."""

import logging
import logging.config
from pathlib import Path
from typing import Optional, Any, Dict
from logging import Logger
from src.common.config import BaseConfig


class LoggingConfig:
    """Centralized logging configuration."""

    @staticmethod
    def setup_logging(
        config: BaseConfig, project_name: str = "common", log_dir: Optional[Path] = None
    ) -> Logger:
        """Setup logging for a project.

        Args:
            config: Configuration instance
            project_name: Name of the project
            log_dir: Directory for log files

        Returns:
            Configured logger instance
        """
        # Create logs directory if specified
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"{project_name}.log"
        else:
            log_file = config.log_file

        # Configure logging
        logging_config: Dict[str, Any] = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": config.log_format,
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "detailed": {
                    "format": (
                        "%(asctime)s - %(name)s - %(levelname)s - %(module)s - "
                        "%(funcName)s:%(lineno)d - %(message)s"
                    ),
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": config.log_level,
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": config.log_level,
                "handlers": ["console"],
            },
        }

        # Add file handler if log file is specified
        if log_file:
            logging_config["handlers"]["file"] = {
                "class": "logging.FileHandler",
                "level": config.log_level,
                "formatter": "detailed",
                "filename": str(log_file),
                "mode": "a",
            }
            logging_config["root"]["handlers"].append("file")

        logging.config.dictConfig(logging_config)
        logger = logging.getLogger(project_name)
        logger.info(
            f"Logging initialized for {project_name} (level: {config.log_level})"
        )
        return logger


def get_logger(name: str) -> Logger:
    """Get a logger instance.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
