"""Immich-specific configuration for WORKFLOW scripts."""

import os
from pathlib import Path

from pydantic import ConfigDict, Field

from common.config import BaseConfig


class ImmichConfig(BaseConfig):
    """Configuration for Immich API access in WORKFLOW."""

    immich_url: str = Field(default="", description="Immich API URL")
    immich_api_key: str = Field(default="", description="Immich API key")
    immich_library_root: str = Field(
        default="",
        description="Root path prefix used by Immich originalPath values",
    )

    model_config = ConfigDict(
        env_file=os.path.join(Path(__file__).resolve().parent.parent, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )
