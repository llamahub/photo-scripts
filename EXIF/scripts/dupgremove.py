#!/usr/bin/env python3
"""
================================================================================
=== [DupGuru File Removal Script] - Move duplicate files based on dupGuru CSV decisions
================================================================================

This script processes dupGuru CSV files (output from dupguru.py) and moves files
marked for deletion to a backup directory, preserving the original folder structure.

The script safely moves duplicates instead of deleting them, allowing for recovery
if needed.
"""

import sys
import os
from pathlib import Path

# Add COMMON to path for shared utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'COMMON', 'src'))

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

# Add project source paths for business logic
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

# Import business logic
try:
    from exif.dup_guru_remover import DupGuruRemover
except ImportError:
    # Fallback - print error and exit
    print("Error: DupGuruRemover class not found in src/exif/dup_guru_remover.py")
    print("Please ensure the business logic has been properly extracted.")
    sys.exit(1)

# Script metadata
SCRIPT_INFO = {
    'name': 'DupGuru File Removal Script',
    'description': 'Move duplicate files based on dupGuru CSV decisions',
    'examples': [
        'results.csv /photos',
        'results.csv /photos --target /backup/duplicates',
        '--input results.csv --source /photos --dry-run',
        'results.csv /photos --target /backup --verbose'
    ]
}

# Script-specific arguments
SCRIPT_ARGUMENTS = {
    'input': {
        'positional': True,
        'help': 'dupGuru CSV file with Action column'
    },
    'source': {
        'positional': True,
        'help': 'Root directory where files to remove are located'
    },
    'target': {
        'flag': '--target',
        'help': 'Directory to move duplicates to (default: {source}.duplicates_{timestamp})'
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
            'input_file': ['input_file', 'input'],
            'source_dir': ['source_file', 'source']
        })
    except SystemExit:
        # Handle missing arguments with specific error messages for backward compatibility
        input_file = getattr(args, 'input_file', None) or getattr(args, 'input', None)
        source_dir = getattr(args, 'source_file', None) or getattr(args, 'source', None)
        
        if not input_file:
            print("input file is required", file=sys.stderr)
            sys.exit(1)
        if not source_dir:
            print("source directory is required", file=sys.stderr)
            sys.exit(1)
    
    # Add target to resolved_args
    resolved_args['target'] = args.target
    
    # Setup logging with consistent pattern
    # Use script name without extension for proper log file naming
    logger = parser.setup_logging(resolved_args, "dupgremove")
    
    # Generate default target if not provided
    if not resolved_args['target']:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Try to detect common base path for better default
        try:
            # Create a temporary remover just to detect base path
            temp_remover = DupGuruRemover(
                csv_file=resolved_args['input_file'],
                target_path=resolved_args['source_dir'],
                dup_path="/tmp",  # temporary, will be overridden
                dry_run=True,
                verbose=False,
                logger=logger
            )
            base_dir = temp_remover._detect_common_base_path()
            
            if base_dir:
                # Use the detected base directory for a better default path
                resolved_args['target'] = f"{resolved_args['source_dir']}/{base_dir}.duplicates_{timestamp}"
            else:
                # Fall back to original logic
                resolved_args['target'] = f"{resolved_args['source_dir']}.duplicates_{timestamp}"
        except Exception:
            # Fall back to original logic if detection fails
            resolved_args['target'] = f"{resolved_args['source_dir']}.duplicates_{timestamp}"
    
    # Display configuration with dupgremove-specific labels
    config_map = {
        'input_file': 'Input CSV file',
        'source_dir': 'Source directory',
        'target': 'Target directory',
        'dry_run': 'Dry run mode',
        'verbose': 'Verbose mode',
        'quiet': 'Quiet mode'
    }
    parser.display_configuration(resolved_args, config_map)
    
    try:
        # Initialize business logic processor
        remover = DupGuruRemover(
            csv_file=resolved_args['input_file'],
            target_path=resolved_args['source_dir'],
            dup_path=resolved_args['target'],
            dry_run=resolved_args.get('dry_run', False),
            verbose=resolved_args.get('verbose', False),
            logger=logger
        )
        
        logger.info("Starting dupGuru file removal")
        logger.info(f"Input CSV: {resolved_args['input_file']}")
        logger.info(f"Source directory: {resolved_args['source_dir']}")
        logger.info(f"Target directory: {resolved_args['target']}")
        
        # Process the CSV
        logger.info("Processing dupGuru CSV file")
        remover.process_csv()
        
        # Print statistics
        stats = remover.stats
        logger.info("Processing complete")
        logger.info(f"Total rows processed: {stats['total_rows']}")
        logger.info(f"Delete actions found: {stats['delete_actions']}")
        logger.info(f"Files moved: {stats['files_moved']}")
        logger.info(f"Files not found: {stats['files_not_found']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info(f"Rows skipped: {stats['skipped_rows']}")
        
        if not resolved_args.get('quiet'):
            remover.print_statistics()
            
            if stats['files_moved'] > 0 and not resolved_args.get('dry_run'):
                print(f"\n✅ Successfully moved {stats['files_moved']} files")
            elif resolved_args.get('dry_run'):
                print(f"\n✅ Dry run complete - would move {stats['files_moved']} files")
            else:
                print("\n✅ No files needed to be moved")
        
        logger.info("DupGuru file removal completed successfully")
        
        # Exit with error code if there were errors but no files moved
        if stats['errors'] > 0 and stats['files_moved'] == 0:
            if not resolved_args.get('quiet'):
                print("⚠️  No files were moved due to errors")
            logger.warning("No files were moved due to errors")
            sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        if not resolved_args.get('quiet'):
            print("\n❌ Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        if not resolved_args.get('quiet'):
            print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
