#!/usr/bin/env python3
"""
Move files between folders based on CSV instructions.

Processes a CSV file with folder move instructions, moving all files from source
folders to specified target folders. Supports validation, overwrite protection,
and comprehensive logging of all operations.

CSV format expected:
- 'Folder': Source folder path (required)
- 'Target Folder': Destination folder path (required when moving)
- 'New Folder': Optional new folder name (not used in this script)

Safety features:
- By default, prevents overwriting existing files
- Requires parent directories to exist unless --overwrite is specified
- Preserves directory structure when moving files
- Removes empty source directories after successful moves
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
    sys.exit(1)

# Import EXIF modules
try:
    from exif.folder_mover import FolderMover
except ImportError as e:
    print(f"Error importing required modules: {e}", file=sys.stderr)
    sys.exit(1)

# Script metadata
SCRIPT_INFO = {
    'name': 'Folder Move Script',
    'description': '''Move files between folders based on CSV instructions

Processes a CSV file with folder move instructions, moving all files from source
folders to specified target folders. Supports validation, overwrite protection,
and comprehensive logging of all operations.

CSV format expected:
- 'Folder': Source folder path (required)
- 'Target Folder': Destination folder path (required when moving)
- 'New Folder': Optional new folder name (not used in this script)

Safety features:
- By default, prevents overwriting existing files
- Requires parent directories to exist unless --overwrite is specified
- Preserves directory structure when moving files
- Removes empty source directories after successful moves''',
    'examples': [
        'move_instructions.csv',
        '--input move_instructions.csv --dry-run',
        'move_instructions.csv --overwrite --verbose',
        '--input move_instructions.csv --overwrite --quiet'
    ]
}

# Script-specific arguments
SCRIPT_ARGUMENTS = {
    'input': {
        'positional': True,
        'help': 'CSV file with Folder and Target Folder columns for move instructions'
    },
    'overwrite': {
        'flag': '--overwrite',
        'action': 'store_true',
        'help': 'Allow overwriting existing files and create full target paths'
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
    
    # Validate and resolve required arguments
    resolved_args = parser.validate_required_args(args, {
        'input_file': ['input_file', 'input']
    })
    
    # Setup logging with different levels for console and file
    # Only summary/progress/errors go to stdout (INFO), all details to file (DEBUG)
    import logging
    from common.logging import ScriptLogging
    logger = ScriptLogging.get_script_logger(
        name="move_folders",
        log_dir=Path(".log"),
        debug=resolved_args.get('verbose', False),
        console_level=logging.INFO,
        file_level=logging.DEBUG,
    )
    
    # Display configuration
    parser.display_configuration(resolved_args)
    
    try:
        # Initialize business logic processor
        mover = FolderMover(
            input_csv=resolved_args['input_file'],
            overwrite=resolved_args.get('overwrite', False),
            dry_run=resolved_args.get('dry_run', False),
            verbose=resolved_args.get('verbose', False),
            logger=logger
        )
        
        logger.info("Starting folder move processing")
        
        # Main processing with progress indicator
        if not resolved_args.get('quiet'):
            print("📁 Processing folder move instructions...")
        
        stats = mover.process_moves()
        
        logger.info("Folder move processing completed successfully")
        logger.debug(f"Final statistics: {stats}")
        
        if not resolved_args.get('quiet'):
            print("✅ Folder move processing completed successfully")
            print(f"Rows processed: {stats['rows_processed']}")
            print(f"Folders moved: {stats['folders_moved']}")
            print(f"Files moved: {stats['files_moved']}")
            if stats['errors'] > 0:
                print(f"⚠️  Errors: {stats['errors']}")
            if stats['skipped'] > 0:
                print(f"⏭️  Skipped: {stats['skipped']}")
            
            if resolved_args.get('dry_run'):
                print("\n📝 This was a dry run - no files were actually moved")
        
    except Exception as e:
        logger.error(f"Error during folder move processing: {e}")
        if not resolved_args.get('quiet'):
            print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
