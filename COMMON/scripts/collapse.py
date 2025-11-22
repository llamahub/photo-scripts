#!/usr/bin/env python3
"""
================================================================================
=== [Collapse Script] - Flatten directory structure by moving all files
================================================================================

Collapse all files from nested subdirectories into a single target directory.
This script recursively finds all files in the source directory tree and
copies (or moves) them to the root of the target directory, flattening the
hierarchy.

Use cases:
- Consolidate scattered files from multiple folders
- Flatten nested directory structures
- Prepare files for batch processing

Warning: Files with duplicate names will be skipped to prevent overwrites.
"""

import sys
import os
import shutil
from pathlib import Path

# Add src to path for COMMON modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import COMMON framework modules
try:
    from common.logging import ScriptLogging
    from common.argument_parser import (
        ScriptArgumentParser,
        create_standard_arguments,
        merge_arguments
    )
except ImportError as e:
    ScriptLogging = None
    print(f"Warning: COMMON modules not available: {e}")
    sys.exit(1)

# Script metadata
SCRIPT_INFO = {
    'name': 'Collapse Script',
    'description': '''Flatten directory structure by moving all files to target

Recursively finds all files in source directory and copies/moves them to the
target directory root, removing the nested folder structure. Duplicate 
filenames are automatically skipped to prevent overwrites.''',
    'examples': [
        '/path/to/source /path/to/target',
        '--source /path/to/source --target /path/to/target --dry-run',
        '/path/to/source /path/to/target --move --verbose',
        '--source /nested/files --target /flat/output --move'
    ]
}

# Script-specific arguments
SCRIPT_ARGUMENTS = {
    'source_positional': {
        'positional': True,
        'metavar': 'SOURCE',
        'nargs': '?',
        'help': 'Source directory containing nested files'
    },
    'target_positional': {
        'positional': True,
        'metavar': 'TARGET',
        'nargs': '?',
        'help': 'Target directory for flattened files'
    },
    'source_dir': {
        'flag': '--source',
        'help': 'Source directory containing nested files (alternative)'
    },
    'target_dir': {
        'flag': '--target',
        'help': 'Target directory for flattened files (alternative)'
    },
    'move': {
        'flag': '--move',
        'action': 'store_true',
        'help': 'Move files instead of copying (faster but removes originals)'
    }
}

# Merge with standard arguments (verbose, quiet, dry_run)
ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


def find_all_files(source_dir: Path, logger) -> list:
    """
    Recursively find all files in source directory.
    
    Args:
        source_dir: Root directory to search
        logger: Logger instance for progress updates
        
    Returns:
        List of Path objects for all files found
    """
    files = []
    
    logger.info(f"Scanning source directory: {source_dir}")
    
    try:
        for root, dirs, filenames in os.walk(source_dir):
            root_path = Path(root)
            
            for filename in filenames:
                file_path = root_path / filename
                files.append(file_path)
                
                if len(files) % 100 == 0:
                    logger.debug(f"Found {len(files)} files so far...")
    
    except PermissionError as e:
        logger.error(f"Permission denied accessing {source_dir}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while scanning {source_dir}: {e}")
    
    logger.info(f"Found {len(files)} files to process")
    return files


def collapse_files(source_dir: Path, target_dir: Path, move: bool,
                   dry_run: bool, logger) -> dict:
    """
    Collapse all files from source subdirectories to target root.
    
    Args:
        source_dir: Source directory with nested files
        target_dir: Target directory for flattened output
        move: If True, move files instead of copying
        dry_run: If True, simulate without making changes
        logger: Logger instance
        
    Returns:
        Dictionary with processing statistics
    """
    stats = {
        'processed': 0,
        'copied': 0,
        'moved': 0,
        'skipped': 0,
        'errors': 0
    }
    
    # Find all files in source
    files = find_all_files(source_dir, logger)
    
    if not files:
        logger.info("No files found to process")
        return stats
    
    # Create target directory if needed
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Target directory ready: {target_dir}")
    
    # Track filenames to detect duplicates
    seen_filenames = set()
    
    # Process each file
    operation = "move" if move else "copy"
    logger.info(f"Starting to {operation} {len(files)} files...")
    
    for i, source_file in enumerate(files, 1):
        stats['processed'] += 1
        
        if i % 50 == 0 or i == len(files):
            logger.info(f"Progress: {i}/{len(files)} files processed")
        
        try:
            filename = source_file.name
            target_file = target_dir / filename
            
            # Skip if file is already in target directory (same location)
            if source_file.parent == target_dir:
                logger.debug(f"Skipping (already in target): {filename}")
                stats['skipped'] += 1
                continue
            
            # Check for duplicate filenames
            if filename in seen_filenames:
                logger.warning(
                    f"Skipping duplicate filename: {filename} "
                    f"(from {source_file.parent})"
                )
                stats['skipped'] += 1
                continue
            
            # Check if target already exists
            if target_file.exists() and not dry_run:
                logger.warning(
                    f"Skipping (target exists): {filename}"
                )
                stats['skipped'] += 1
                continue
            
            # Perform copy or move
            if not dry_run:
                if move:
                    shutil.move(str(source_file), str(target_file))
                    stats['moved'] += 1
                    logger.info(
                        f"Moved: {source_file.relative_to(source_dir)} "
                        f"→ {filename}"
                    )
                else:
                    shutil.copy2(source_file, target_file)
                    stats['copied'] += 1
                    logger.info(
                        f"Copied: {source_file.relative_to(source_dir)} "
                        f"→ {filename}"
                    )
            else:
                action = "move" if move else "copy"
                if move:
                    stats['moved'] += 1
                else:
                    stats['copied'] += 1
                logger.info(
                    f"[DRY RUN] Would {action}: "
                    f"{source_file.relative_to(source_dir)} → {filename}"
                )
            
            seen_filenames.add(filename)
        
        except Exception as e:
            logger.error(f"Error processing {source_file}: {e}")
            stats['errors'] += 1
    
    return stats


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
        'source_dir': ['source_dir', 'source_positional'],
        'target_dir': ['target_dir', 'target_positional']
    })
    
    # Setup logging with consistent pattern
    logger = parser.setup_logging(resolved_args, "collapse")
    
    # Display configuration
    config_map = {
        'source_dir': 'Source directory',
        'target_dir': 'Target directory'
    }
    parser.display_configuration(resolved_args, config_map)
    
    # Additional configuration display
    if not resolved_args.get('quiet'):
        if resolved_args.get('move'):
            print("Operation: MOVE files (originals will be removed)")
        else:
            print("Operation: COPY files (originals preserved)")
        print()
    
    try:
        source_dir = Path(resolved_args['source_dir']).resolve()
        target_dir = Path(resolved_args['target_dir']).resolve()
        move = resolved_args.get('move', False)
        dry_run = resolved_args.get('dry_run', False)
        
        # Validate source directory
        if not source_dir.exists():
            raise FileNotFoundError(
                f"Source directory does not exist: {source_dir}"
            )
        if not source_dir.is_dir():
            raise NotADirectoryError(
                f"Source is not a directory: {source_dir}"
            )
        
        # Prevent collapsing into a subdirectory of source
        # (but allow target == source for in-place collapse)
        if target_dir != source_dir and target_dir.is_relative_to(source_dir):
            raise ValueError(
                f"Target directory cannot be a subdirectory of source. "
                f"Target: {target_dir}, Source: {source_dir}"
            )
        
        logger.info("Starting collapse operation")
        logger.info(f"Source directory: {source_dir}")
        logger.info(f"Target directory: {target_dir}")
        logger.info(f"Operation: {'MOVE' if move else 'COPY'}")
        logger.info(f"Dry run: {dry_run}")
        
        # Perform collapse operation
        stats = collapse_files(source_dir, target_dir, move, dry_run, logger)
        
        # Log final statistics
        logger.info("=" * 80)
        logger.info(" COLLAPSE COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Files processed: {stats['processed']}")
        logger.info(f"Files copied: {stats['copied']}")
        logger.info(f"Files moved: {stats['moved']}")
        logger.info(f"Files skipped: {stats['skipped']}")
        logger.info(f"Errors encountered: {stats['errors']}")
        
        if dry_run:
            logger.info(
                "NOTE: This was a dry run - no files were actually changed"
            )
        
        logger.info("=" * 80)
        
        # User-friendly summary
        if not resolved_args.get('quiet'):
            print("✅ Collapse operation completed successfully")
            print(f"Files processed: {stats['processed']}")
            
            if move:
                print(f"Files moved: {stats['moved']}")
            else:
                print(f"Files copied: {stats['copied']}")
            
            if stats['skipped'] > 0:
                print(f"Files skipped: {stats['skipped']}")
            if stats['errors'] > 0:
                print(f"⚠️  Errors encountered: {stats['errors']}")
            
            if dry_run:
                print("\n🔍 This was a DRY RUN - no actual changes were made")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error during collapse operation: {e}")
        if not resolved_args.get('quiet'):
            print(f"❌ Error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
