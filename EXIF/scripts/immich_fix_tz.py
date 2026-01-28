#!/usr/bin/env python3
"""
Fix Image Timezone Offsets from CSV

Reads a CSV file (output from immich_extract) and updates timezone offsets for images
where the fix_timezone column is populated. Preserves the UTC moment in time while
changing the timezone representation.
"""

import sys
import os
from pathlib import Path

# Add COMMON to path for shared utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'COMMON', 'src'))

try:
    from common.argument_parser import ScriptArgumentParser, create_standard_arguments, merge_arguments
    from common.logging import ScriptLogging
except ImportError:
    ScriptArgumentParser = None
    print("Warning: COMMON modules not available")

from exif.timezone_fixer import TimezoneFixer

SCRIPT_INFO = {
    'name': 'immich_fix_tz',
    'description': 'Fix image timezone offsets based on CSV input from immich_extract',
    'examples': [
        'immich_extract_20260128_123456.csv --dry-run',
        'immich_extract_20260128_123456.csv --verbose',
        '.log/immich_extract_20260128_123456.csv'
    ]
}

SCRIPT_ARGUMENTS = {
    'input': {
        'positional': True,
        'help': 'Input CSV file from immich_extract (with fix_timezone column populated)'
    }
}

# Merge with standard arguments (verbose, quiet, dry_run)
ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)

def main():
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    parser.print_header()

    args = parser.parse_args()

    # If --help is present, argparse will exit before this point
    if '--help' in sys.argv or '-h' in sys.argv:
        return

    # Validate and resolve required arguments
    resolved_args = parser.validate_required_args(args, {
        'input': ['input']
    })

    # Setup logging with consistent pattern
    logger = parser.setup_logging(resolved_args, "immich_fix_tz")

    # Display configuration for audit
    config_map = {
        'input': 'Input CSV file',
        'dry_run': 'Dry run',
        'verbose': 'Verbose',
        'quiet': 'Quiet'
    }

    # Log configuration instead of printing
    if not resolved_args.get("quiet"):
        for arg_key, display_label in config_map.items():
            value = resolved_args.get(arg_key)
            if value:
                logger.info(f"{display_label}: {value}")
        if resolved_args.get("dry_run"):
            logger.info("Mode: DRY RUN (simulation only)")
        logger.info("")

    # Validate input file exists
    input_csv = Path(resolved_args.get('input'))
    if not input_csv.exists():
        logger.error(f"Input CSV file not found: {input_csv}")
        return 1

    # Call business logic
    fixer = TimezoneFixer(
        input_csv=str(input_csv),
        dry_run=resolved_args.get('dry_run', False),
        logger=logger
    )

    try:
        result = fixer.run()

        # Log summary output
        logger.info("\n" + ("="*50))
        logger.info("SUMMARY")
        logger.info("="*50)
        logger.info(f"Total rows in CSV: {result.get('total', 0)}")
        logger.info(f"Images processed: {result.get('processed', 0)}")
        logger.info(f"Images skipped (no fix_timezone): {result.get('skipped', 0)}")
        logger.info(f"Errors: {result.get('errors', 0)}")

        if resolved_args.get("dry_run"):
            logger.info("\nThis was a dry run. No files were actually modified.")

        return 0

    except Exception as e:
        logger.error(f"Error running timezone fixer: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main() or 0)
