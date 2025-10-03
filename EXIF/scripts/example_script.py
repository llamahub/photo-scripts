#!/usr/bin/env python3
"""
Example script showing how to use COMMON ScriptLogging with auto-detection.
"""

import sys
from pathlib import Path

# Import COMMON logging
common_src_path = Path(__file__).parent.parent.parent / 'COMMON' / 'src'
sys.path.insert(0, str(common_src_path))

try:
    from common.logging import ScriptLogging
except ImportError:
    print("Warning: COMMON ScriptLogging not available, using basic logging")
    import logging
    ScriptLogging = None


def main():
    """Main function demonstrating ScriptLogging usage."""
    
    # Setup logging - enhanced version with auto-detection!
    if ScriptLogging:
        logger = ScriptLogging.get_script_logger(debug=True)  # Auto-detects script name and uses .log dir
    else:
        # Fallback
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("example")
    
    # Use the logger
    logger.info("Starting example script")
    logger.debug("This is a debug message")
    logger.warning("This is a warning")
    logger.error("This is an error")
    logger.info("Script completed successfully")


if __name__ == '__main__':
    main()