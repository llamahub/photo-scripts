#!/usr/bin/env python3
"""
================================================================================
=== [Immich Counts] - List per-day counts of updated Immich assets
================================================================================

Read-only script that groups Immich asset updates by day.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT.parent / "COMMON" / "src"))

from common.argument_parser import ScriptArgumentParser, create_standard_arguments, merge_arguments
from immich_config import ImmichConfig
from immich_client import ImmichClient
from immich_counts_service import ImmichCountsService


SCRIPT_INFO = {
    "name": "Immich Counts",
    "description": "List counts of Immich assets updated per day",
    "examples": [
        "",
        "--after 2026-03-01T00:00:00Z",
        "--before 2026-03-20T00:00:00Z --after 2026-03-01T00:00:00Z",
        "--album-name Favorites",
    ],
}

SCRIPT_ARGUMENTS = {
    "album_name": {
        "flag": "--album-name",
        "help": "Only count assets for this album name",
    },
    "before": {
        "flag": "--before",
        "help": "Only count assets modified before ISO date/time",
    },
    "after": {
        "flag": "--after",
        "help": "Only count assets modified after ISO date/time",
    },
}

ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


def validate_iso8601_date(value: str, arg_name: str, parser: ScriptArgumentParser) -> None:
    """Validate full ISO datetime values used by Immich filter args."""
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


def build_runtime_options(resolved_args: Dict[str, Any]) -> Dict[str, Any]:
    """Build normalized options for business logic."""
    return {
        "album_name": resolved_args.get("album_name"),
        "before": resolved_args.get("before"),
        "after": resolved_args.get("after"),
    }


def load_immich_credentials() -> tuple[str, str]:
    """Load Immich URL and API key from WORKFLOW .env via ImmichConfig."""
    config = ImmichConfig(
        _env_file=PROJECT_ROOT / ".env",
        _env_file_encoding="utf-8",
    )

    immich_url = config.immich_url
    immich_api_key = config.immich_api_key
    return immich_url, immich_api_key


def main() -> int:
    """CLI entry point."""
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    parser.print_header()

    args = parser.parse_args()
    resolved_args = vars(args)

    validate_iso8601_date(resolved_args.get("before"), "--before", parser)
    validate_iso8601_date(resolved_args.get("after"), "--after", parser)

    immich_url, immich_api_key = load_immich_credentials()
    if not immich_url or not immich_api_key:
        parser.error(
            "IMMICH_URL and IMMICH_API_KEY must be set in WORKFLOW/.env for immich_counts"
        )

    logger = parser.setup_logging(resolved_args, "immich_counts")
    logger.info("Starting Immich daily counts")

    client = ImmichClient(immich_url, immich_api_key, logger)
    if not client.validate_connection():
        logger.error("Unable to connect to Immich")
        return 1

    service = ImmichCountsService(client, logger)

    try:
        result = service.run(build_runtime_options(resolved_args))
    except Exception as exc:
        logger.error("immich_counts failed: %s", exc)
        return 1

    logger.info("Total assets counted: %s", result.total_assets)
    logger.info("Total days: %s", result.total_days)
    return 0


if __name__ == "__main__":
    sys.exit(main())
