"""Immich-specific configuration for IMMICH scripts."""

import sys
from pathlib import Path
from pydantic import Field

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
    """Configuration for Immich API connection."""
    
    immich_url: str = Field(default="", description="Immich API URL")
    immich_api_key: str = Field(default="", description="Immich API Key")
