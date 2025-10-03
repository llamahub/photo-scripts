"""Common logging framework for all projects."""

import logging
import logging.config
from pathlib import Path
from typing import Optional, Any, Dict
from logging import Logger

try:
    from src.common.config import BaseConfig
except ImportError:
    # Try alternative import path
    try:
        from common.config import BaseConfig
    except ImportError:
        # If neither works, we'll define a minimal BaseConfig later
        BaseConfig = None


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


class ScriptLogging:
    """Simplified logging setup for standalone scripts."""
    
    @staticmethod
    def get_script_logger(
        name: str, 
        log_dir: Optional[Path] = None, 
        debug: bool = False
    ) -> Logger:
        """Get a logger configured for standalone scripts.
        
        This provides a simple way to get a logger with both console and file
        output without needing to create a full BaseConfig instance.
        
        Args:
            name: Logger name (typically script name with timestamp)
            log_dir: Directory for log files (defaults to '.log' in current dir)
            debug: Enable debug level logging
            
        Returns:
            Configured logger instance
        """
        if log_dir is None:
            log_dir = Path('.log')
        
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"{name}.log"
        
        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG if debug else logging.INFO)
        
        # Clear any existing handlers to avoid duplicates
        logger.handlers.clear()
        
        # Create formatters matching COMMON patterns
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        logger.info(f"Script logging initialized for {name} (debug: {debug})")
        return logger
