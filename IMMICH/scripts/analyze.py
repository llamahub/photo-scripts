#!/usr/bin/env python3
"""
Gathers info on all files in image library and outputs to a CSV file.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add COMMON and project src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root.parent / "COMMON" / "src"))

from common.logging import ScriptLogging
from common.argument_parser import (
    ScriptArgumentParser,
    create_standard_arguments,
    merge_arguments,
)
from image_analyzer import ImageAnalyzer


SCRIPT_INFO = {
    "name": "Analyze",
    "description": "Gathers info on all files in image library and outputs to a CSV file",
    "examples": [
        "/path/to/photos",
        "--source /path/to/photos",
        "/path/to/photos --output /tmp/analyze.csv",
        "--source /path/to/photos --output /tmp/analyze.csv --verbose",
    ],
}

SCRIPT_ARGUMENTS = {
    "source": {
        "flag": "--source",
        "positional": True,
        "help": "Path to root folder of source image library",
    },
    "output": {
        "flag": "--output",
        "positional": True,
        "help": "Output CSV file for analysis (default: .log/analyze_YYYY-MM-DD_HHMM.csv)",
    },
}

ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


def main() -> int:
    """Main entry point with consistent argument parsing and structure."""
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    parser.print_header()

    args = parser.parse_args()

    resolved_args = parser.validate_required_args(
        args, {"source": ["source", "source_file"]}
    )

    output_arg = getattr(args, "output", None) or getattr(args, "output_file", None)
    resolved_args["output"] = output_arg
    resolved_args.pop("output_file", None)

    debug_mode = resolved_args.get("verbose") and not resolved_args.get("quiet")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    logger = ScriptLogging.get_script_logger(
        name=f"analyze_{timestamp}", log_dir=Path(".log"), debug=debug_mode
    )

    config_map = {
        "source": "Source Folder",
        "output": "Output CSV file",
    }
    parser.display_configuration(resolved_args, config_map)

    source_folder = resolved_args["source"]
    if not os.path.exists(source_folder):
        logger.error(f"Source folder not found: {source_folder}")
        print(f"❌ Error: Source folder not found: {source_folder}")
        return 1

    output_file = resolved_args.get("output")
    if not output_file:
        log_dir = Path(".log")
        log_dir.mkdir(exist_ok=True)
        output_file = str(log_dir / f"analyze_{timestamp}.csv")

    logger.info(f"Source Folder: {source_folder}")
    logger.info(f"Output file: {output_file}")
    logger.info("Using ExifTool for accurate file type detection")

    analyzer = ImageAnalyzer(
        source_folder,
        logger,
    )
    try:
        rows = analyzer.analyze_to_csv(output_file)
    except Exception as exc:
        logger.error(f"Analyze failed: {exc}")
        print(f"❌ Error: {exc}")
        return 1

    logger.info(f"Analysis complete. Rows written: {rows}")
    if not resolved_args.get("quiet"):
        print(f"✅ Analysis complete. Rows written: {rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
