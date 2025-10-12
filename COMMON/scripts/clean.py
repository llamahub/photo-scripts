#!/usr/bin/env python3
"""
Clean utility script for removing unwanted files and empty folders.

This script can remove:
- Apple-generated files (.DS_Store, ._* files) with --mac flag
- Empty directories with --empty flag  
- Log files (.log files) with --log flag
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import os
import glob

# Standard COMMON import pattern
common_src_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(common_src_path))

try:
    from common.logging import ScriptLogging
except ImportError:
    import logging
    ScriptLogging = None


class DirectoryCleaner:
    """Handles cleaning operations for directories."""
    
    def __init__(self, target_path: Path, logger):
        self.target_path = Path(target_path)
        self.logger = logger
        self.stats = {
            'mac_files_removed': 0,
            'log_files_removed': 0,
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
    
    def clean_empty_directories(self, dry_run: bool = False) -> None:
        """Remove empty directories (bottom-up to handle nested empty dirs)."""
        self.logger.info("Scanning for empty directories...")
        
        # Get all directories, sorted by depth (deepest first)
        all_dirs = [d for d in self.target_path.rglob('*') if d.is_dir()]
        all_dirs.sort(key=lambda x: len(x.parts), reverse=True)
        
        empty_dirs_found = 0
        for dir_path in all_dirs:
            try:
                # Check if directory is empty (no files or subdirectories)
                if not any(dir_path.iterdir()):
                    if dry_run:
                        self.logger.info(f"Would remove empty directory: {dir_path}")
                    else:
                        dir_path.rmdir()
                        self.logger.debug(f"Removed empty directory: {dir_path}")
                    empty_dirs_found += 1
                    self.stats['empty_dirs_removed'] += 1
            except OSError as e:
                # Directory not empty or permission error
                self.logger.debug(f"Could not remove directory {dir_path}: {e}")
            except Exception as e:
                self.logger.error(f"Failed to remove directory {dir_path}: {e}")
                self.stats['errors'] += 1
        
        self.logger.info(f"Found {empty_dirs_found} empty directories")
    
    def print_summary(self) -> None:
        """Print cleaning summary statistics."""
        self.logger.info("=" * 50)
        self.logger.info("CLEANING SUMMARY")
        self.logger.info("=" * 50)
        self.logger.info(f"Apple files removed: {self.stats['mac_files_removed']}")
        self.logger.info(f"Log files removed: {self.stats['log_files_removed']}")
        self.logger.info(f"Empty directories removed: {self.stats['empty_dirs_removed']}")
        if self.stats['errors'] > 0:
            self.logger.warning(f"Errors encountered: {self.stats['errors']}")
        self.logger.info("=" * 50)


def main():
    """Main function for the clean script."""
    parser = argparse.ArgumentParser(
        description="Clean unwanted files and empty directories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/folder --mac --empty    # Clean Apple files and empty dirs
  %(prog)s /path/to/folder --log            # Clean only log files
  %(prog)s /path/to/folder --mac --log --empty --dry-run  # Preview all cleaning
        """
    )
    
    parser.add_argument(
        'target',
        type=Path,
        help='Path to target folder to clean'
    )
    
    parser.add_argument(
        '--mac',
        action='store_true',
        help='Remove Apple-generated files (.DS_Store, ._* files)'
    )
    
    parser.add_argument(
        '--empty',
        action='store_true',
        help='Remove empty directories'
    )
    
    parser.add_argument(
        '--log',
        action='store_true',
        help='Remove .log files'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be removed without actually removing anything'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output'
    )
    
    args = parser.parse_args()
    
    # Standard logging setup
    if ScriptLogging:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        logger = ScriptLogging.get_script_logger(
            name=f"clean_{timestamp}",
            debug=args.debug
        )
    else:
        logging.basicConfig(
            level=logging.DEBUG if args.debug else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger("clean")
    
    # Validate target directory
    if not args.target.exists():
        logger.error(f"Target directory does not exist: {args.target}")
        return 1
    
    if not args.target.is_dir():
        logger.error(f"Target path is not a directory: {args.target}")
        return 1
    
    # Check if any cleaning options were specified
    if not any([args.mac, args.empty, args.log]):
        logger.error("No cleaning options specified. Use --mac, --empty, and/or --log")
        logger.info("Use --help for usage information")
        return 1
    
    # Start cleaning
    logger.info("Starting directory cleaning")
    logger.info(f"Target directory: {args.target}")
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No files will actually be removed")
    
    cleaner = DirectoryCleaner(args.target, logger)
    
    try:
        # Perform requested cleaning operations
        if args.mac:
            cleaner.clean_mac_files(dry_run=args.dry_run)
        
        if args.log:
            cleaner.clean_log_files(dry_run=args.dry_run)
        
        if args.empty:
            cleaner.clean_empty_directories(dry_run=args.dry_run)
        
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