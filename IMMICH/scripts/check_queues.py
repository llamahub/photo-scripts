#!/usr/bin/env python3
"""
================================================================================
=== [Check Queues] - report queue status and idle state
================================================================================

Fetches Immich queue status and reports whether all queues appear idle.
"""

import sys
import time
from pathlib import Path

# Add project src and COMMON to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root.parent / "COMMON" / "src"))

from common.argument_parser import (
    ScriptArgumentParser,
    create_standard_arguments,
    merge_arguments,
)
from immich_config import ImmichConfig
from immich_connection import ImmichConnection
from queue_checker import QueueChecker


SCRIPT_INFO = {
    "name": "Check Queues",
    "description": "Report Immich queue status and whether all queues are idle",
    "examples": [
        "",
        "--verbose",
        "--wait",
        "--wait 30",
    ],
}

SCRIPT_ARGUMENTS = {
    "wait": {
        "flag": "--wait",
        "type": int,
        "nargs": "?",
        "const": 10,
        "help": "Wait N seconds, then check queues again (default 10 if flag only)",
    }
}

ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


def main() -> int:
    """Main entry point."""
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    parser.print_header()

    args = parser.parse_args()
    resolved_args = parser.validate_required_args(args, {})

    logger = parser.setup_logging(resolved_args, "check_queues")
    parser.display_configuration(resolved_args)

    config = ImmichConfig()
    if not config.immich_url or not config.immich_api_key:
        parser.error(
            "Immich URL and API key must be provided via IMMICH_URL and IMMICH_API_KEY"
        )

    connection = ImmichConnection(config.immich_url, config.immich_api_key, logger)
    if not connection.validate_connection():
        logger.error("Failed to connect to Immich server")
        return 1

    checker = QueueChecker(connection, logger)
    overview = checker.fetch_queue_overview()
    _log_queues(logger, overview.queues, only_active=False)

    if overview.all_idle:
        logger.info("All queues appear idle")
        return 0

    wait_seconds = resolved_args.get("wait")
    if wait_seconds is not None:
        if wait_seconds < 0:
            parser.error("Wait seconds must be zero or greater")
        while True:
            logger.info("Waiting %d seconds before rechecking queues", wait_seconds)
            time.sleep(wait_seconds)
            overview = checker.fetch_queue_overview()
            _log_queues(logger, overview.queues, only_active=True)
            if overview.all_idle:
                logger.info("All queues appear idle")
                return 0

    logger.warning("One or more queues are active")
    return 2


def _log_queues(logger, queues, only_active: bool) -> None:
    printed = False
    for queue in queues:
        if only_active and queue.is_idle:
            continue
        printed = True
        logger.info(
            "Queue %s paused=%s active=%d waiting=%d delayed=%d failed=%d completed=%d",
            queue.name,
            queue.is_paused,
            queue.active,
            queue.waiting,
            queue.delayed,
            queue.failed,
            queue.completed,
        )
    if only_active and not printed:
        logger.info("No active queues")


if __name__ == "__main__":
    raise SystemExit(main())
