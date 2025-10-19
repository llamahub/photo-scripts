#!/usr/bin/env python3
"""
================================================================================
=== [Photo Organization Script] - Organize photos by date using EXIF/metadata
================================================================================

Organizes photos or videos from a source directory into a target directory with structured
subdirectories based on dates obtained from EXIF/metadata.

Target directory structure: <decade>/<year>/<year>-<month>/<parent folder>/<filename>
- <decade>: Decade in format "YYYY+" (e.g., 1990+, 2000+, 2010+)
- <year>: 4-digit year (e.g., 1995, 2021)
- <month>: 2-digit month (e.g., 01, 02, 12)
- <parent folder>: Name of immediate parent folder from source
- <filename>: Original filename
"""

import sys
import os
from pathlib import Path

# Add COMMON to path for shared utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'COMMON', 'src'))

# Add project source paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

# Import COMMON framework modules
try:
    from common.logging import ScriptLogging
    from common.argument_parser import (
        ScriptArgumentParser,
        create_standard_arguments,
        merge_arguments
    )
except ImportError:
    ScriptLogging = None
    print("Warning: COMMON modules not available")

# Import EXIF modules
try:
    from exif import PhotoOrganizer
except ImportError as e:
    print(f"Error importing required modules: {e}", file=sys.stderr)
    sys.exit(1)

# Script metadata
SCRIPT_INFO = {
    'name': 'Photo Organization Script',
    'description': '''Organize photos or videos by date using EXIF/metadata

Target directory structure:
  Default: <decade>/<year>/<year>-<month>/<parent folder>/<filename>
  --no-parent: <decade>/<year>/<year>-<month>/<filename>

Where:
  - <decade>: Decade in format "YYYY+" (e.g., 1990+, 2000+, 2010+)
  - <year>: 4-digit year (e.g., 1995, 2021)
  - <month>: 2-digit month (e.g., 01, 02, 12)
  - <parent folder>: Name of immediate parent folder from source (skipped with --no-parent)
  - <filename>: Original filename''',
    'examples': [
        '/path/to/photos /path/to/organized',
        '--source /path/to/photos --target /path/to/organized --dry-run',
        '/path/to/photos /path/to/organized --move --no-parent --verbose',
        '/path/to/videos /path/to/organized --video --workers 8',
        '. run organize tests/test_images .tmp/sorted'
    ]
}

# Script-specific arguments
SCRIPT_ARGUMENTS = {
    'source': {
        'positional': True,
        'help': 'Source directory containing photos/videos'
    },
    'target': {
        'positional': True,
        'help': 'Target directory for organized photos/videos'
    },
    'move': {
        'flag': '--move',
        'action': 'store_true',
        'help': 'Move files instead of copying them (faster for large sets)'
    },
    'workers': {
        'flag': '--workers',
        'type': int,
        'help': 'Number of parallel workers (default: auto-detect, use 1 for single-threaded)'
    },
    'video': {
        'flag': '--video',
        'action': 'store_true',
        'help': 'Process video files instead of image files (supports mp4, mov, avi, mkv, etc.)'
    },
    'no_parent': {
        'flag': '--no-parent',
        'action': 'store_true',
        'help': 'Skip parent folder in target path - files go directly to YYYY-MM folders'
    },
    'debug': {
        'flag': '--debug',
        'action': 'store_true',
        'help': 'Enable debug output with detailed logging (alias for --verbose)'
    }
}

# Merge with standard arguments (verbose, quiet, dry_run)
ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


def main():
    """Main entry point with consistent argument parsing and structure."""
    
    # Create argument parser
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    
    # Print standardized header
    parser.print_header()
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate and resolve required arguments with custom error handling
    try:
        resolved_args = parser.validate_required_args(args, {
            'source_dir': ['source_file', 'source'],
            'target_dir': ['target_file', 'target']
        })
    except SystemExit:
        # Handle missing arguments with specific error messages for backward compatibility
        source = getattr(args, 'source_file', None) or getattr(args, 'source', None)
        target = getattr(args, 'target_file', None) or getattr(args, 'target', None)
        
        if not source:
            print("source directory is required", file=sys.stderr)
            sys.exit(1)
        if not target:
            print("target directory is required", file=sys.stderr)
            sys.exit(1)
    
    # Setup logging with consistent pattern
    debug_mode = resolved_args.get('verbose') or resolved_args.get('debug')
    logger = parser.setup_logging(resolved_args, "organize")
    
    # Display configuration with organize-specific labels
    config_map = {
        'source_dir': 'Source directory',
        'target_dir': 'Target directory'
    }
    parser.display_configuration(resolved_args, config_map)
    
    # Additional configuration display for organize-specific options
    if not resolved_args.get('quiet'):
        if resolved_args.get('move'):
            print("Operation: MOVE files (cut and paste)")
        else:
            print("Operation: COPY files (preserve originals)")
        
        if resolved_args.get('video'):
            print("Mode: VIDEO file processing")
        else:
            print("Mode: IMAGE file processing")
        
        if resolved_args.get('no_parent'):
            print("Structure: Direct to YYYY-MM folders (no parent folder)")
        else:
            print("Structure: Include parent folder in path")
        
        if resolved_args.get('workers'):
            print(f"Workers: {resolved_args['workers']} parallel threads")
        else:
            print("Workers: Auto-detect optimal thread count")
        
        print()
    
    try:
        # Initialize PhotoOrganizer with resolved arguments
        logger.info("Initializing PhotoOrganizer")
        logger.info(f"Source: {resolved_args['source_dir']}")
        logger.info(f"Target: {resolved_args['target_dir']}")
        logger.info(f"Mode: {'MOVE' if resolved_args.get('move') else 'COPY'}")
        logger.info(f"File type: {'VIDEO' if resolved_args.get('video') else 'IMAGE'}")
        logger.info(f"Structure: {'No parent' if resolved_args.get('no_parent') else 'Include parent'}")
        
        organizer = PhotoOrganizer(
            source=resolved_args['source_dir'],
            target=resolved_args['target_dir'],
            dry_run=resolved_args.get('dry_run', False),
            debug=debug_mode,
            move_files=resolved_args.get('move', False),
            max_workers=resolved_args.get('workers'),
            video_mode=resolved_args.get('video', False),
            no_parent_folder=resolved_args.get('no_parent', False)
        )
        
        logger.info("Starting photo organization process")
        
        # Run the organization process
        organizer.run()
        
        # Get and log final statistics
        stats = organizer.get_stats()
        logger.info("Photo organization completed successfully")
        logger.info(f"Files processed: {stats.get('processed', 0)}")
        logger.info(f"Files copied/moved: {stats.get('copied', 0)}")
        logger.info(f"Files skipped: {stats.get('skipped', 0)}")
        logger.info(f"Errors encountered: {stats.get('errors', 0)}")
        
        if not resolved_args.get('quiet'):
            print("✅ Photo organization completed successfully")
            print(f"Files processed: {stats.get('processed', 0)}")
            print(f"Files copied/moved: {stats.get('copied', 0)}")
            if stats.get('skipped', 0) > 0:
                print(f"Files skipped: {stats.get('skipped', 0)}")
            if stats.get('errors', 0) > 0:
                print(f"⚠️  Errors encountered: {stats.get('errors', 0)}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during photo organization: {e}")
        if not resolved_args.get('quiet'):
            print(f"❌ Error: {e}")
            print(f"Error: {e}", file=sys.stderr)  # For test compatibility
        return 1


if __name__ == '__main__':
    sys.exit(main())
