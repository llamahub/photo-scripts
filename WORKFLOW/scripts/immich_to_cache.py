#!/usr/bin/env python3
"""
================================================================================
=== [Immich To Cache] - Extract Immich metadata into WORKFLOW cache
================================================================================

Extract metadata from Immich into a WORKFLOW cache JSON file.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add project src and COMMON src to path.
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT.parent / "COMMON" / "src"))

from common.argument_parser import ScriptArgumentParser, create_standard_arguments, merge_arguments
from immich_config import ImmichConfig
from cache_store import CacheStore
from immich_client import ImmichClient
from immich_to_cache_service import ImmichToCacheService


SCRIPT_INFO = {
    "name": "Immich To Cache",
    "description": "Extract metadata from Immich into WORKFLOW cache",
    "examples": [
        "--cache .cache/cache_2026-03-20.json",
        "--before 2026-03-01T00:00:00Z --after 2026-02-01T00:00:00Z",
        "--album-name Favorites --albums --people",
        "--all",
    ],
}

SCRIPT_ARGUMENTS = {
    "cache": {
        "flag": "--cache",
        "help": "Path to cache JSON file (default: .cache/cache_YYYY-MM-DD.json)",
    },
    "album_name": {
        "flag": "--album-name",
        "help": "Only extract assets for this album name",
    },
    "before": {
        "flag": "--before",
        "help": "Only extract assets modified before ISO date/time",
    },
    "after": {
        "flag": "--after",
        "help": "Only extract assets modified after ISO date/time",
    },
    "albums": {
        "flag": "--albums",
        "action": "store_true",
        "help": "Include album names for each extracted asset",
    },
    "people": {
        "flag": "--people",
        "action": "store_true",
        "help": "Include people for each extracted asset",
    },
    "all": {
        "flag": "--all",
        "action": "store_true",
        "help": "Include both album names and people for each extracted asset",
    },
}

ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


def validate_iso8601_date(value: str, arg_name: str, parser: ScriptArgumentParser) -> None:
    """Fail with parser error when date value is not full ISO 8601."""
    if not value:
        return

    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$")
    if not pattern.match(value):
        parser.error(
            f"Invalid value for {arg_name}: '{value}'. "
            "Expected full ISO 8601 datetime such as 2026-03-01T00:00:00Z"
        )

    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parser.error(f"Invalid value for {arg_name}: '{value}'. Datetime is not valid.")


def default_cache_path() -> str:
    """Return default day-based cache path."""
    return f".cache/cache_{datetime.now().strftime('%Y-%m-%d')}.json"


def build_runtime_options(resolved_args: Dict[str, Any], immich_library_root: str) -> Dict[str, Any]:
    """Build normalized runtime options passed to service layer."""
    cache_path = resolved_args.get("cache") or default_cache_path()
    return {
        "cache": cache_path,
        "album_name": resolved_args.get("album_name"),
        "before": resolved_args.get("before"),
        "after": resolved_args.get("after"),
        "albums": resolved_args.get("albums", False),
        "people": resolved_args.get("people", False),
        "all": resolved_args.get("all", False),
        "immich_library_root": immich_library_root,
    }


def load_immich_credentials() -> tuple[str, str, str]:
    """Load Immich URL, API key, and library root from WORKFLOW .env."""
    config = ImmichConfig(
        _env_file=PROJECT_ROOT / ".env",
        _env_file_encoding="utf-8",
    )

    immich_url = config.immich_url
    immich_api_key = config.immich_api_key
    immich_library_root = config.immich_library_root
    return immich_url, immich_api_key, immich_library_root


def main() -> int:
    """CLI entry point."""
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    parser.print_header()

    args = parser.parse_args()
    resolved_args = vars(args)

    validate_iso8601_date(resolved_args.get("before"), "--before", parser)
    validate_iso8601_date(resolved_args.get("after"), "--after", parser)

    immich_url, immich_api_key, immich_library_root = load_immich_credentials()
    if not immich_url or not immich_api_key or not immich_library_root:
        parser.error(
            "IMMICH_URL, IMMICH_API_KEY, and IMMICH_LIBRARY_ROOT must be set in WORKFLOW/.env for immich_to_cache"
        )

    options = build_runtime_options(resolved_args, immich_library_root)
    logger = parser.setup_logging(resolved_args, "immich_to_cache")

    logger.info("Starting Immich metadata extraction")
    logger.info("Cache file: %s", options["cache"])

    client = ImmichClient(immich_url, immich_api_key, logger)
    if not client.validate_connection():
        logger.error("Unable to connect to Immich")
        return 1

    cache_store = CacheStore(options["cache"], logger)
    service = ImmichToCacheService(client, cache_store, logger)

    try:
        result = service.run(options)
    except Exception as exc:
        logger.error("immich_to_cache failed: %s", exc)
        return 1

    logger.info("Extraction complete")
    logger.info("Fetched: %s", result.fetched)
    logger.info("Inserted: %s", result.inserted)
    logger.info("Updated: %s", result.updated)
    logger.info("Cache path: %s", result.cache_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
