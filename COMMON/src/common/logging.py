import logging
import sys

# Add custom AUDIT log level between DEBUG (10) and INFO (20)
AUDIT_LEVEL = 15
logging.addLevelName(AUDIT_LEVEL, "AUDIT")


def audit(self, message, *args, **kwargs):
    if self.isEnabledFor(AUDIT_LEVEL):
        self._log(AUDIT_LEVEL, message, args, **kwargs)


logging.Logger.audit = audit
logging.Logger.audit = audit
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
        config: Any, project_name: str = "common", log_dir: Optional[Path] = None
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
                    "format": config.log_format,  # Use format from config
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "file": {
                    "format": config.log_format,  # Use format from config
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
                "formatter": "file",
                "filename": str(log_file),
                "mode": "a",
            }
            logging_config["root"]["handlers"].append("file")

        logging.config.dictConfig(logging_config)
        logger = logging.getLogger(project_name)

        # Add header with log file info if file logging is enabled
        if log_file:
            logger.info("=" * 80)
            logger.info(f"LOG FILE: {log_file}")
            logger.info(f"PROJECT: {project_name}")
            logger.info(f"LOG LEVEL: {config.log_level}")
            logger.info("=" * 80)

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
        name: Optional[str] = None,
        log_dir: Optional[Path] = None,
        debug: bool = False,
        config: Optional[Any] = None,
        console_level: int = logging.INFO,
        file_level: int = logging.DEBUG,
    ) -> Logger:
        """Get a logger configured for standalone scripts.

        This provides a simple way to get a logger with both console and file
        output without needing to create a full BaseConfig instance.

        Args:
            name: Logger name (auto-generated from calling script if None)
            log_dir: Directory for log files (defaults to '.log' in current dir)
            debug: Enable debug level logging
            config: Optional BaseConfig instance (creates default if None)

        Returns:
            Configured logger instance
        """
        # Auto-generate name from calling script if not provided
        if name is None:
            import inspect
            from datetime import datetime

            # Get the calling frame (script that called this function)
            frame = inspect.currentframe()
            try:
                # Go up the call stack to find the calling script
                caller_frame = frame.f_back
                while caller_frame:
                    filename = caller_frame.f_code.co_filename
                    if filename != __file__ and not filename.endswith(
                        "common_tasks.py"
                    ):
                        # Found the calling script
                        script_name = Path(filename).stem
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        name = f"{script_name}_{timestamp}"
                        break
                    caller_frame = caller_frame.f_back

                # Fallback if we couldn't determine the script name
                if name is None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    name = f"script_{timestamp}"

            finally:
                del frame  # Prevent reference cycles

        # Default to project .log directory
        if log_dir is None:
            log_dir = Path(".log")

        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"{name}.log"

        # Create config if not provided
        if config is None:
            if BaseConfig:
                config = BaseConfig()
            else:
                # Fallback if BaseConfig is not available
                class FallbackConfig:
                    log_format = "%(asctime)s - %(levelname)s - %(message)s"

                config = FallbackConfig()

        # Create logger

        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # Clear any existing handlers to avoid duplicates
        logger.handlers.clear()

        # Create formatters using config format
        console_formatter = logging.Formatter(
            config.log_format, datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_formatter = logging.Formatter(
            config.log_format, datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Add custom AUDIT log level between DEBUG (10) and INFO (20)
        AUDIT_LEVEL = 15
        logging.addLevelName(AUDIT_LEVEL, "AUDIT")

        def audit(self, message, *args, **kwargs):
            if self.isEnabledFor(AUDIT_LEVEL):
                self._log(AUDIT_LEVEL, message, args, **kwargs)

        logging.Logger.audit = audit

        # Console handler (INFO and above)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_handler.addFilter(lambda record: record.levelno >= logging.INFO)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler (DEBUG and above, including AUDIT)
        file_handler = logging.FileHandler(log_file, mode="a")
        file_handler.setLevel(file_level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Usage:
        # - Use logger.audit("...") for single folder/file/image transactions (goes only to log file)
        # - Use logger.info("...") for summary/progress (goes to stdout and log file)

        # Add header with log file info
        logger.info("=" * 80)
        logger.info(f"LOG FILE: {log_file}")
        logger.info(f"SCRIPT: {name}")
        logger.info(f"DEBUG MODE: {debug}")
        logger.info("=" * 80)

        logger.info(f"Script logging initialized for {name} (debug: {debug})")
        return logger

        # Add header with log file info
        logger.info("=" * 80)
        logger.info(f"LOG FILE: {log_file}")
        logger.info(f"SCRIPT: {name}")
        logger.info(f"DEBUG MODE: {debug}")
        logger.info("=" * 80)

        logger.info(f"Script logging initialized for {name} (debug: {debug})")
        return logger
