#!/usr/bin/env python3
"""
================================================================================
=== [Link Photo Drive] - Mount and link /mnt/photo_drive to remote or local storage
================================================================================
"""

import os
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
from link_photo_drive import LinkPhotoDrive


SCRIPT_INFO = {
    'name': 'Link Photo Drive',
    'description': 'Mount and link /mnt/photo_drive to remote or local storage',
    'examples': [
        '--remote',
        '--local',
        '--dry-run',
    ],
}

SCRIPT_ARGUMENTS = {
    'remote': {
        'flag': '--remote',
        'action': 'store_true',
        'help': 'Mount and link the remote photo drive only',
    },
    'local': {
        'flag': '--local',
        'action': 'store_true',
        'help': 'Link the local photo drive only',
    },
}

ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


def main() -> None:
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    parser.print_header()

    args = parser.parse_args()
    resolved_args = parser.validate_required_args(args)

    logger = parser.setup_logging(resolved_args, 'link_photo_drive')
    parser.display_configuration(resolved_args)

    if resolved_args.get('remote') and resolved_args.get('local'):
        logger.error("--remote and --local cannot be used together")
        if not resolved_args.get('quiet'):
            print("ERROR: --remote and --local cannot be used together")
        sys.exit(1)

    linker = LinkPhotoDrive(
        logger=logger,
        dry_run=resolved_args.get('dry_run', False),
    )

    try:
        if resolved_args.get('remote'):
            result = linker.link_remote()
            logger.info("Linked to remote: %s", result.linked_to)
        elif resolved_args.get('local'):
            result = linker.link_local()
            logger.info("Linked to local: %s", result.linked_to)
        else:
            result = linker.link_auto()
            logger.info("Linked automatically to: %s", result.linked_to)

        if not resolved_args.get('quiet'):
            print(f"OK: Linked /mnt/photo_drive -> {result.linked_to}")

    except Exception as exc:
        logger.error("Error linking photo drive: %s", exc)
        if not resolved_args.get('quiet'):
            print(f"ERROR: {exc}")
        sys.exit(1)


if __name__ == '__main__':
    main()
