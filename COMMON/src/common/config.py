"""Common configuration management using Pydantic."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import Field
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


class BaseConfig(BaseSettings):
    """Base configuration class for all projects."""

    # Environment settings
    environment: str = Field(default="dev", description="Environment: dev, test, prod")
    debug: bool = Field(default=True, description="Enable debug mode")

    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(levelname)s - %(message)s",
        description="Log message format",
    )
    log_file: Optional[str] = Field(default=None, description="Log file path")

    # Database settings (example)
    database_url: Optional[str] = Field(default=None, description="Database URL")
    database_echo: bool = Field(default=False, description="Echo SQL queries")

    # API settings (example)
    api_host: str = Field(default="localhost", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_debug: bool = Field(default=True, description="API debug mode")

    model_config = ConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


def load_config(project_path: Optional[Path] = None, env: str = "dev") -> BaseConfig:
    """Load configuration for a project.

    Args:
        project_path: Path to the project directory
        env: Environment to load (dev, test, prod)

    Returns:
        Loaded configuration instance
    """
    if project_path is None:
        project_path = Path.cwd()

    # Load environment-specific .env file
    env_file = project_path / f".env.{env}"
    if env_file.exists():
        load_dotenv(env_file)
    else:
        # Fallback to default .env file
        default_env = project_path / ".env"
        if default_env.exists():
            load_dotenv(default_env)

    # Set environment variable
    os.environ["ENVIRONMENT"] = env

    return BaseConfig()


class ProjectConfig(BaseConfig):
    """Extended configuration for specific projects."""

    project_name: str = Field(..., description="Project name")
    project_version: str = Field(default="1.0.0", description="Project version")

    # Project-specific settings can be added here
    custom_settings: Dict[str, Any] = Field(default_factory=dict)
