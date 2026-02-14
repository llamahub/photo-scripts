#!/usr/bin/env python3
"""
================================================================================
=== [update] - updates files selected from output csv file from analyze script
================================================================================

Applies EXIF and file path updates based on rows selected in an analyze CSV file.

Key features:
- Uses ScriptArgumentParser for standardized argument handling
- Uses ScriptLogging for consistent console and file logging
- Processes selected CSV rows and applies EXIF updates and file moves
"""

import sys
from pathlib import Path

# Add COMMON and project src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root.parent / "COMMON" / "src"))

from common.argument_parser import (
    ScriptArgumentParser,
    create_standard_arguments,
    merge_arguments,
)

from image_updater import ImageUpdater


SCRIPT_INFO = {
    "name": "update",
    "description": "updates files selected from output csv file from analyze script",
    "examples": [
        ".log/analyze_2025-01-01_1200.csv",
        "--input .log/analyze_2025-01-01_1200.csv --dry-run",
        "--last --dry-run",
    ],
}

SCRIPT_ARGUMENTS = {
    "input": {
        "flag": "--input",
        "positional": True,
        "help": "Path to CSV file created by analyze script",
    },
    "last": {
        "flag": "--last",
        "action": "store_true",
        "help": "Use the latest analyze output CSV from .log",
    },
    "all": {
        "flag": "--all",
        "action": "store_true",
        "help": "Process all rows regardless of Select column value",
    },
    "force": {
        "flag": "--force",
        "action": "store_true",
        "help": "Force update of calculated values regardless of status",
    },
}

ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


def _find_latest_analyze_csv(log_dir: Path) -> Path | None:
    if not log_dir.exists():
        return None

    candidates = list(log_dir.glob("analyze_*.csv"))
    if not candidates:
        return None

    return max(candidates, key=lambda path: path.stat().st_mtime)


def main() -> int:
    """Main entry point with consistent argument parsing and structure."""
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    args = parser.parse_args()
    resolved_args = parser.validate_required_args(args)

    logger = parser.setup_logging(resolved_args, "update")
    logger.info(parser.get_header())

    input_value = getattr(args, "input", None) or getattr(args, "input_file", None)
    use_last = resolved_args.get("last")

    if input_value and use_last:
        logger.error("Cannot use both --input and --last")
        return 1

    if use_last:
        latest = _find_latest_analyze_csv(Path(".log"))
        if not latest:
            logger.error("No analyze CSV files found in .log")
            return 1
        input_value = str(latest)

    if not input_value:
        logger.error("Missing required --input (or use --last)")
        return 1

    resolved_args["input"] = input_value
    config_map = {
        "input": "Input CSV",
        "last": "Use latest CSV",
        "all": "Process all rows",
        "force": "Force update",
        "dry_run": "Dry run",
    }
    for arg_key, display_label in config_map.items():
        value = resolved_args.get(arg_key)
        if value:
            logger.info(f"{display_label}: {value}")
    if resolved_args.get("dry_run"):
        logger.info("Mode: DRY RUN (simulation only)")

    try:
        updater = ImageUpdater(
            csv_path=input_value,
            logger=logger,
            dry_run=resolved_args.get("dry_run", False),
            all_rows=resolved_args.get("all", False),
            force=resolved_args.get("force", False),
        )
        stats = updater.process()
    except Exception as exc:
        logger.error(f"Update failed: {exc}")
        return 1

    logger.info(
        "Update complete. Total=%d Selected=%d EXIF Updated=%d Renamed=%d Moved=%d "
        "Sidecar Renamed=%d Sidecar Moved=%d Sidecar Errors=%d Errors=%d",
        stats.get("rows_total", 0),
        stats.get("rows_selected", 0),
        stats.get("exif_updated", 0),
        stats.get("renamed", 0),
        stats.get("moved", 0),
        stats.get("sidecar_renamed", 0),
        stats.get("sidecar_moved", 0),
        stats.get("sidecar_errors", 0),
        stats.get("errors", 0),
    )

    # Only fail if we have CRITICAL errors (e.g., exiftool missing, file I/O issues)
    # File-level EXIF update failures (e.g., corrupted files) are acceptable
    if stats.get("sidecar_errors", 0) > 0:
        logger.warning(f"Sidecar errors encountered: {stats['sidecar_errors']}")
        return 1
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
