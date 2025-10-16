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
        description="Extract and enhance images from Google Takeout ZIP files or process existing folders",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s takeout.zip output_folder              # Extract ZIP and process (default)
  %(prog)s takeout.zip output_folder --subdir     # Create subdirectory for ZIP
  %(prog)s --source takeout.zip --target output_folder
  %(prog)s --folder existing_folder --target output_folder  # Process existing folder
  
This script will:
  ZIP mode:
    1. Extract all files from the Google Takeout ZIP
    2. Identify images, videos, and sidecar JSON files
    3. Update media file metadata using sidecar information
    4. Preserve original directory structure in target folder
  
  Folder mode:
    1. Scan existing folder for images, videos, and sidecar JSON files
    2. Update media file metadata using sidecar information
    3. Files are processed in-place (original files are modified)
  
By default in ZIP mode, files are extracted directly to target directory.
Use --subdir to create ZIP-named subdirectories (prevents conflicts when processing multiple ZIPs).
        """
    )
    
    # Positional argument (also available as named)
    parser.add_argument('source', nargs='?',
                        help='Path to Google Takeout ZIP file (for ZIP mode)')
    
    # Named arguments
    parser.add_argument('target', nargs='?',
                        help='Path to target directory for extraction')
    parser.add_argument('--source', dest='source_named',
                        help='Path to Google Takeout ZIP file (for ZIP mode)')
    parser.add_argument('--folder', dest='folder_path',
                        help='Path to existing folder containing Takeout files to process in-place')
    parser.add_argument('--target', dest='target_named',
                        help='Path to target directory for extraction (ZIP mode) or processing (folder mode)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug output')
    parser.add_argument('--subdir', action='store_true',
                        help='Create subdirectory based on ZIP filename to prevent conflicts (ZIP mode only)')
    
    args = parser.parse_args()
    
    # Determine processing mode
    has_zip_source = bool(args.source or args.source_named)
    has_folder_source = bool(args.folder_path)
    
    if has_zip_source and has_folder_source:
        parser.error("Cannot specify both ZIP source and folder source. "
                     "Choose either --source or --folder.")
    
    if not has_zip_source and not has_folder_source:
        parser.error("Must specify either ZIP source (positional or --source) "
                     "or --folder for processing mode.")
    
    # Create a new namespace with resolved values
    final_args = argparse.Namespace()
    final_args.debug = args.debug
    final_args.create_subdir = args.subdir
    
    if has_folder_source:
        # Folder processing mode
        final_args.mode = 'folder'
        final_args.source = Path(args.folder_path)
        
        # For folder mode, target is optional (defaults to processing in-place)
        if args.target:
            final_args.target = Path(args.target)
        elif args.target_named:
            final_args.target = Path(args.target_named)
        else:
            # Process in-place - use the folder itself as target
            final_args.target = Path(args.folder_path)
            
    else:
        # ZIP processing mode (original behavior)
        final_args.mode = 'zip'
        
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
        
        final_args.source = Path(final_source)
        final_args.target = Path(final_target)
    
    return final_args


def main():
    """Main entry point with argument parsing and logging setup."""
    args = parse_arguments()
    
    # Standard logging setup using COMMON framework
    if ScriptLogging:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        mode_suffix = args.mode
        logger = ScriptLogging.get_script_logger(
            name=f"takeout_{mode_suffix}_{timestamp}",
            debug=args.debug
        )
    else:
        # Fallback logging setup
        logging.basicConfig(
            level=logging.DEBUG if args.debug else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger("takeout")
    
    # Validate arguments based on mode
    if args.mode == 'zip':
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
            
        logger.info("Starting Google Takeout ZIP processing")
        logger.info(f"Source ZIP: {args.source}")
        logger.info(f"Target directory: {args.target}")
        
    else:  # folder mode
        if not args.source.exists():
            logger.error(f"Source folder does not exist: {args.source}")
            return 1
        
        if not args.source.is_dir():
            logger.error(f"Source path is not a directory: {args.source}")
            return 1
        
        logger.info("Starting Google Takeout folder processing")
        logger.info(f"Source folder: {args.source}")
        if args.source != args.target:
            logger.info(f"Target directory: {args.target}")
        else:
            logger.info("Processing files in-place")
    
    try:
        # Create and run the processor
        if args.mode == 'zip':
            processor = TakeoutProcessor(
                zip_path=args.source,
                target_dir=args.target,
                create_subdir=args.create_subdir
            )
        else:  # folder mode
            processor = TakeoutProcessor(
                folder_path=args.source,
                target_dir=args.target,
                create_subdir=False  # Not applicable for folder mode
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
