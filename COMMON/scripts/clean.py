#!/usr/bin/env python3
"""
Clean utility script for removing unwanted files and empty folders.

This script can remove:
- Apple-generated files (.DS_Store, ._* files) with --mac flag
- Empty directories with --empty flag  
- Log files (.log files) with --log flag
- Thumbnail files (Thumbs.db, Desktop.ini, etc) with --thumbs flag
"""

import sys
import os
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

# Business logic will be embedded for now (Step 4 will extract to module)
    
# Script metadata
SCRIPT_INFO = {
    'name': 'Clean Utility Script',
    'description': '''Clean unwanted files and empty directories

This script can remove:
- Apple-generated files (.DS_Store, ._* files) with --mac flag
- Empty directories with --empty flag
- Log files (.log files) with --log flag
- Thumbnail files (Thumbs.db, Desktop.ini, etc) with --thumbs flag''',
    'examples': [
        '/path/to/folder --mac --empty',
        '/path/to/folder --log',
        '/path/to/folder --thumbs',
        '/path/to/folder --mac --thumbs --empty --dry-run'
    ]
}

# Script-specific arguments
SCRIPT_ARGUMENTS = {
    'target': {
        'positional': True,
        'help': 'Path to target folder to clean'
    },
    'mac': {
        'flag': '--mac',
        'action': 'store_true',
        'help': 'Remove Apple-generated files (.DS_Store, ._* files)'
    },
    'empty': {
        'flag': '--empty',
        'action': 'store_true',
        'help': 'Remove empty directories'
    },
    'log': {
        'flag': '--log',
        'action': 'store_true',
        'help': 'Remove .log files'
    },
    'thumbs': {
        'flag': '--thumbs',
        'action': 'store_true',
        'help': 'Remove thumbnail files (Thumbs.db, Desktop.ini, etc)'
    }
}

# Merge with standard arguments (verbose, quiet, dry_run)
ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


class DirectoryCleaner:
    """Handles cleaning operations for directories."""
    
    def __init__(self, target_path: Path, logger):
        self.target_path = Path(target_path)
        self.logger = logger
        self.stats = {
            'mac_files_removed': 0,
            'log_files_removed': 0,
            'thumb_files_removed': 0,
            'empty_dirs_removed': 0,
            'errors': 0
        }
    
    def clean_mac_files(self, dry_run: bool = False) -> None:
        """Remove Apple-generated files (.DS_Store and ._* files)."""
        self.logger.info("Scanning for Apple-generated files...")
        
        # Find .DS_Store files
        ds_store_files = list(self.target_path.rglob('.DS_Store'))
        self.logger.info(f"Found {len(ds_store_files)} .DS_Store files")
        
        for file_path in ds_store_files:
            try:
                if dry_run:
                    self.logger.info(f"Would remove: {file_path}")
                else:
                    file_path.unlink()
                    self.logger.debug(f"Removed .DS_Store: {file_path}")
                self.stats['mac_files_removed'] += 1
            except Exception as e:
                self.logger.error(f"Failed to remove {file_path}: {e}")
                self.stats['errors'] += 1
        
        # Find ._* files (AppleDouble files)
        apple_double_count = 0
        for file_path in self.target_path.rglob('._*'):
            if file_path.is_file():
                try:
                    if dry_run:
                        self.logger.info(f"Would remove: {file_path}")
                    else:
                        file_path.unlink()
                        self.logger.debug(f"Removed AppleDouble: {file_path}")
                    apple_double_count += 1
                    self.stats['mac_files_removed'] += 1
                except Exception as e:
                    self.logger.error(f"Failed to remove {file_path}: {e}")
                    self.stats['errors'] += 1
        
        self.logger.info(f"Found {apple_double_count} AppleDouble (._*) files")
    
    def clean_log_files(self, dry_run: bool = False) -> None:
        """Remove .log files."""
        self.logger.info("Scanning for log files...")
        
        log_files = list(self.target_path.rglob('*.log'))
        self.logger.info(f"Found {len(log_files)} log files")
        
        for file_path in log_files:
            try:
                if dry_run:
                    self.logger.info(f"Would remove: {file_path}")
                else:
                    file_path.unlink()
                    self.logger.debug(f"Removed log file: {file_path}")
                self.stats['log_files_removed'] += 1
            except Exception as e:
                self.logger.error(f"Failed to remove {file_path}: {e}")
                self.stats['errors'] += 1
    
    def clean_thumb_files(self, dry_run: bool = False) -> None:
        """Remove thumbnail files (Thumbs.db, Desktop.ini, etc)."""
        self.logger.info("Scanning for thumbnail files...")
        
        thumb_patterns = [
            'Thumbs.db', 'Desktop.ini', 'Folder.jpg',
            'AlbumArtSmall.jpg', 'AlbumArt*.jpg'
        ]
        total_files = 0
        
        for pattern in thumb_patterns:
            thumb_files = list(self.target_path.rglob(pattern))
            total_files += len(thumb_files)
            
            for file_path in thumb_files:
                try:
                    if dry_run:
                        self.logger.info(f"Would remove: {file_path}")
                    else:
                        file_path.unlink()
                        self.logger.debug(f"Removed thumbnail: {file_path}")
                    self.stats['thumb_files_removed'] += 1
                except Exception as e:
                    self.logger.error(f"Failed to remove {file_path}: {e}")
                    self.stats['errors'] += 1
        
        self.logger.info(f"Found {total_files} thumbnail files")
    
    def clean_empty_directories(self, dry_run: bool = False) -> None:
        """Remove empty directories."""
        self.logger.info("Scanning for empty directories...")
        
        # Iteratively remove empty directories until no more are found
        removed_any = True
        while removed_any:
            removed_any = False
            empty_dirs = []
            
            for dir_path in self.target_path.rglob('*'):
                if dir_path.is_dir():
                    try:
                        # Check if directory is empty (no files or subdirectories)
                        if not any(dir_path.iterdir()):
                            empty_dirs.append(dir_path)
                    except (OSError, PermissionError):
                        # Skip directories we can't read
                        continue
            
            # Sort by depth (deepest first) to remove child directories before parents
            empty_dirs.sort(key=lambda p: len(p.parts), reverse=True)
            
            if not empty_dirs:
                break
                
            self.logger.info(f"Found {len(empty_dirs)} empty directories")
            
            for dir_path in empty_dirs:
                try:
                    if dry_run:
                        self.logger.info(f"Would remove: {dir_path}")
                        self.stats['empty_dirs_removed'] += 1
                    else:
                        dir_path.rmdir()
                        self.logger.debug(f"Removed empty directory: {dir_path}")
                        self.stats['empty_dirs_removed'] += 1
                        removed_any = True
                except Exception as e:
                    self.logger.error(f"Failed to remove {dir_path}: {e}")
                    self.stats['errors'] += 1
            
            # In dry-run mode, break after first iteration to avoid infinite loop
            if dry_run:
                break
    
    def print_summary(self):
        """Print cleaning summary statistics."""
        self.logger.info("=" * 50)
        self.logger.info("CLEANING SUMMARY:")
        self.logger.info(f"Apple files removed: {self.stats['mac_files_removed']}")
        self.logger.info(f"Log files removed: {self.stats['log_files_removed']}")
        self.logger.info(f"Thumbnail files removed: "
                         f"{self.stats['thumb_files_removed']}")
        self.logger.info(f"Empty directories removed: "
                         f"{self.stats['empty_dirs_removed']}")
        if self.stats['errors'] > 0:
            self.logger.warning(f"Errors encountered: {self.stats['errors']}")
        self.logger.info("=" * 50)


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
        'target_path': ['target']
    })
    
    # Setup logging with three handlers: stdout (INFO+), stderr (WARNING+), file (DEBUG+)
    import logging
    log_dir = Path('.log')
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / 'clean.log'

    logger = logging.getLogger('clean')
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Console handler for stdout (INFO and above)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.addFilter(lambda record: record.levelno == logging.INFO)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    # Console handler for stderr (WARNING and above)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    # File handler for all logs (DEBUG and above)
    file_handler = logging.FileHandler(log_file, mode='a')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Display configuration with clean-specific labels
    config_map = {
        'target_path': 'Target directory',
        'mac': 'Clean Mac files',
        'empty': 'Clean empty directories',
        'log': 'Clean log files',
        'thumbs': 'Clean thumbnail files'
    }
    parser.display_configuration(resolved_args, config_map)
    
    try:
        # Convert to Path object and validate
        target_path = Path(resolved_args['target_path'])
        
        logger.info("Starting directory cleaning")
        logger.info(f"Target directory: {target_path}")
        
        # Validate target directory
        if not target_path.exists():
            logger.error(f"Target directory does not exist: {target_path}")
            return 1
        
        if not target_path.is_dir():
            logger.error(f"Target path is not a directory: {target_path}")
            return 1
        
        # Check if any cleaning options were specified
        cleaning_options = ['mac', 'empty', 'log', 'thumbs']
        if not any(resolved_args.get(option, False) for option in cleaning_options):
            logger.error("No cleaning options specified. Use --mac, --empty, "
                         "--log, and/or --thumbs")
            return 1
        
        # Check for dry run mode
        dry_run = resolved_args.get('dry_run', False)
        if dry_run:
            logger.info("DRY RUN MODE - No files will actually be removed")
        
        # Initialize cleaner
        cleaner = DirectoryCleaner(target_path, logger)
        
        # Perform requested cleaning operations
        if resolved_args.get('mac', False):
            cleaner.clean_mac_files(dry_run=dry_run)
        
        if resolved_args.get('log', False):
            cleaner.clean_log_files(dry_run=dry_run)
        
        if resolved_args.get('thumbs', False):
            cleaner.clean_thumb_files(dry_run=dry_run)
        
        if resolved_args.get('empty', False):
            cleaner.clean_empty_directories(dry_run=dry_run)
        
        # Print summary
        cleaner.print_summary()
        
        if cleaner.stats['errors'] > 0:
            logger.warning("Cleaning completed with errors")
            return 1
        
        logger.info("Cleaning completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.warning("Cleaning interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during cleaning: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())