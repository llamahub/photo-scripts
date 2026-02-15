"""Immich-specific configuration for IMMICH scripts."""

import os
import sys
from pathlib import Path
from pydantic import Field, ConfigDict

# Add COMMON/src to sys.path for robust import
try:
    common_src = Path(__file__).resolve().parents[2] / "COMMON" / "src"
    if str(common_src) not in sys.path:
        sys.path.insert(0, str(common_src))
    from common.config import BaseConfig
except ImportError:
    # Fallback: try relative import if running as part of a package
    from common.config import BaseConfig


class ImmichConfig(BaseConfig):
    """Configuration for Immich API connection and database access."""
    
    immich_url: str = Field(default="", description="Immich API URL")
    immich_api_key: str = Field(default="", description="Immich API Key")
    
    # SSH configuration for database operations
    immich_ssh_host: str = Field(default="", description="SSH hostname for Immich server")
    immich_ssh_user: str = Field(default="root", description="SSH username")
    immich_ssh_port: int = Field(default=22, description="SSH port")
    
    # Database configuration
    immich_db_container: str = Field(default="immich_postgres", description="Docker container name")
    immich_db_user: str = Field(default="postgres", description="Database username")
    immich_db_name: str = Field(default="immich", description="Database name")
    immich_db_container: str = Field(default="immich_postgres", description="PostgreSQL container name")
    immich_db_user: str = Field(default="postgres", description="PostgreSQL username")
    immich_db_name: str = Field(default="immich", description="PostgreSQL database name")
    
    model_config = ConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )
