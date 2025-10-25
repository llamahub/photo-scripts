"""Immich-specific configuration for EXIF scripts."""

import sys
from pathlib import Path
from pydantic import Field

# Dynamically add COMMON/src to sys.path for robust import
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "COMMON" / "src"))
    from common.config import BaseConfig
except ImportError:
    # Fallback: try relative import if running as part of a package
    from ...common.config import BaseConfig


class ImmichConfig(BaseConfig):
    immich_url: str = Field(default="", description="Immich API URL")
    immich_api_key: str = Field(default="", description="Immich API Key")
