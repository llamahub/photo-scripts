#!/usr/bin/env python3
"""
Google Takeout Processor - Extract and enhance images from Google Takeout ZIP files

This script extracts all images and videos from Google Takeout ZIP files and
updates their EXIF metadata using the associated sidecar JSON files.

Usage:
    takeout.py /path/to/takeout.zip /path/to/output/dir
    takeout.py --source /path/to/takeout.zip --target /path/to/output/dir
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add project source paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

# Import COMMON framework with fallback
try:
    common_src_path = project_root.parent / 'COMMON' / 'src'
    sys.path.insert(0, str(common_src_path))
    from common.logging import ScriptLogging
except ImportError:
    import logging
    ScriptLogging = None

try:
    from exif.takeout_processor import TakeoutProcessor
except ImportError as e:
    print(f"Error importing required modules: {e}", file=sys.stderr)
    sys.exit(1)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract and enhance images from Google Takeout ZIP files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s takeout.zip output_folder              # Direct extraction (default)
  %(prog)s takeout.zip output_folder --subdir     # Create subdirectory for ZIP
  %(prog)s --source takeout.zip --target output_folder
  
This script will:
  1. Extract all files from the Google Takeout ZIP
  2. Identify images, videos, and sidecar JSON files
  3. Update media file metadata using sidecar information
  4. Preserve original directory structure in target folder
  
By default, files are extracted directly to target directory.
Use --subdir to create ZIP-named subdirectories (prevents conflicts when processing multiple ZIPs).
        """
    )
    
    # Positional argument (also available as named)
    parser.add_argument('source', nargs='?',
                        help='Path to Google Takeout ZIP file')
    
    # Named arguments
    parser.add_argument('target', nargs='?',
                        help='Path to target directory for extraction')
    parser.add_argument('--source', dest='source_named',
                        help='Path to Google Takeout ZIP file')
    parser.add_argument('--target', dest='target_named',
                        help='Path to target directory for extraction')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug output')
    parser.add_argument('--subdir', action='store_true',
                        help='Create subdirectory based on ZIP filename to prevent conflicts')
    
    args = parser.parse_args()
    
    # Resolve source: positional takes precedence over named
    if args.source:
        final_source = args.source
    elif args.source_named:
        final_source = args.source_named
    else:
        parser.error("Source ZIP file is required (provide as positional argument or --source)")
    
    # Resolve target: positional takes precedence over named
    if args.target:
        final_target = args.target
    elif args.target_named:
        final_target = args.target_named
    else:
        parser.error("Target directory is required (provide as positional argument or --target)")
    
    # Create a new namespace with resolved values
    final_args = argparse.Namespace()
    final_args.source = Path(final_source)
    final_args.target = Path(final_target)
    final_args.debug = args.debug
    final_args.create_subdir = args.subdir  # Use flag directly - default False
    
    return final_args


def main():
    """Main entry point with argument parsing and logging setup."""
    args = parse_arguments()
    
    # Standard logging setup using COMMON framework
    if ScriptLogging:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        logger = ScriptLogging.get_script_logger(
            name=f"takeout_{timestamp}",
            debug=args.debug
        )
    else:
        # Fallback logging setup
        logging.basicConfig(
            level=logging.DEBUG if args.debug else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger("takeout")
    
    # Validate arguments
    if not args.source.exists():
        logger.error(f"Source ZIP file does not exist: {args.source}")
        return 1
    
    if not args.source.is_file():
        logger.error(f"Source path is not a file: {args.source}")
        return 1
    
    if not str(args.source).lower().endswith('.zip'):
        logger.error(f"Source file is not a ZIP file: {args.source}")
        return 1
    
    if args.target.exists() and not args.target.is_dir():
        logger.error(f"Target path exists but is not a directory: {args.target}")
        return 1
    
    logger.info("Starting Google Takeout processing")
    logger.info(f"Source ZIP: {args.source}")
    logger.info(f"Target directory: {args.target}")
    
    try:
        # Create and run the processor
        processor = TakeoutProcessor(
            zip_path=args.source,
            target_dir=args.target,
            create_subdir=args.create_subdir
        )
        
        # Set the logger
        processor.logger = logger
        
        processor.process_takeout()
        processor.print_summary()
        
        logger.info("Google Takeout processing completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.warning("Processing interrupted by user")
        return 1
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except PermissionError as e:
        logger.error(f"Permission denied: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during processing: {e}")
        if args.debug:
            logger.exception("Full traceback:")
        return 1


if __name__ == '__main__':
    sys.exit(main())
