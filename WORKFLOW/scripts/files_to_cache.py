#!/usr/bin/env python3
"""
================================================================================
=== [Files To Cache] - Extract file metadata from library into WORKFLOW cache
================================================================================

Extract file-derived metadata from a source library into cache JSON.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT.parent / "COMMON" / "src"))

from common.argument_parser import ScriptArgumentParser, create_standard_arguments, merge_arguments
from cache_store import CacheStore
from files_to_cache_service import FilesToCacheService


SCRIPT_INFO = {
    "name": "Files To Cache",
    "description": "Extract metadata from files library into WORKFLOW cache",
    "examples": [
        "/mnt/photos/library",
        "--source /mnt/photos/library",
        "/mnt/photos/library --cache .cache/cache_2026-03-20.json",
    ],
}

SCRIPT_ARGUMENTS = {
    "source": {
        "flag": "--source",
        "positional": True,
        "help": "Source files library root directory",
    },
    "cache": {
        "flag": "--cache",
        "help": "Path to cache JSON file (default: .cache/cache_YYYY-MM-DD.json)",
    },
}

ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


def default_cache_path() -> str:
    """Return default day-based cache path."""
    return f".cache/cache_{datetime.now().strftime('%Y-%m-%d')}.json"


def build_runtime_options(resolved_args: Dict[str, Any]) -> Dict[str, Any]:
    """Build normalized options for service execution."""
    cache_path = resolved_args.get("cache") or default_cache_path()
    return {
        "source": resolved_args["source"],
        "cache": cache_path,
    }


def main() -> int:
    """CLI entry point."""
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    parser.print_header()

    args = parser.parse_args()
    resolved_args = parser.validate_required_args(
        args,
        {
            "source": ["source", "source_file"],
        },
    )

    source_path = Path(resolved_args["source"])
    if not source_path.exists() or not source_path.is_dir():
        parser.error(f"Source directory does not exist: {source_path}")

    options = build_runtime_options(resolved_args)
    logger = parser.setup_logging(resolved_args, "files_to_cache")

    logger.info("Starting files metadata extraction")
    logger.info("Source: %s", options["source"])
    logger.info("Cache file: %s", options["cache"])

    cache_store = CacheStore(options["cache"], logger)
    service = FilesToCacheService(cache_store, logger)

    try:
        result = service.run(options)
    except Exception as exc:
        logger.error("files_to_cache failed: %s", exc)
        return 1

    logger.info("Extraction complete")
    logger.info("Scanned: %s", result.scanned)
    logger.info("Inserted: %s", result.inserted)
    logger.info("Updated: %s", result.updated)
    logger.info("Cache path: %s", result.cache_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
