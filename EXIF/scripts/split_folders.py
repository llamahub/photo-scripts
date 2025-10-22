#!/usr/bin/env python3
"""
================================================================================
=== [Folder Splitting Script] - Split large folders by image dates
================================================================================

Scans through subdirectories of a source folder and splits any folder containing
more than 50 images into organized subfolders based on image date information.

Uses ImageData.getImageDate() which prioritizes:
1. EXIF DateTimeOriginal, CreateDate, etc. 
2. Filename-embedded dates
3. File modification time as fallback

Each large folder is split into subfolders containing up to 50 images each,
organized chronologically by the best available date for each image.

Example transformation:
- "2025-05 ABC" (125 images) becomes:
  - "2025-05 ABC/2025-05-10" (50 images with dates <= 2025-05-10)
  - "2025-05 ABC/2025-05-15" (50 images with dates <= 2025-05-15)
  - "2025-05 ABC/2025-05-28" (25 remaining images, latest date is 2025-05-28)
"""

import sys
import os
from pathlib import Path
from datetime import datetime

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
    from exif.image_data import ImageData
    from exif.photo_organizer import PhotoOrganizer
except ImportError as e:
    print(f"Error importing required modules: {e}", file=sys.stderr)
    sys.exit(1)

# Script metadata
SCRIPT_INFO = {
    'name': 'Folder Splitting Script',
    'description': '''Split large folders by image dates

Scans subdirectories and splits folders with >50 images into chronological subfolders.
Each subfolder contains up to 50 images organized by best available date (EXIF, filename, or file date).

Uses ImageData.getImageDate() priority: EXIF dates → filename dates → file modification time.
Naming convention: <original-folder>/<YYYY-MM-DD> where date is the latest image date in that batch.''',
    'examples': [
        '/path/to/photos',
        '--source /path/to/photos --dry-run',
        '/path/to/photos --threshold 75 --verbose',
        '/path/to/photos --max-per-folder 25'
    ]
}

# Script-specific arguments
SCRIPT_ARGUMENTS = {
    'source': {
        'positional': True,
        'help': 'Source directory containing folders to potentially split'
    },
    'threshold': {
        'flag': '--threshold',
        'type': int,
        'default': 50,
        'help': 'Minimum number of images in folder to trigger splitting (default: 50)'
    },
    'max_per_folder': {
        'flag': '--max-per-folder',
        'type': int,
        'default': 50,
        'help': 'Maximum number of images per split subfolder (default: 50)'
    }
}

# Merge with standard arguments (verbose, quiet, dry_run)
ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


class FolderSplitter:
    """Splits large image folders into chronologically organized subfolders."""
    
    def __init__(self, source_dir, threshold=50, max_per_folder=50, dry_run=False, logger=None, quiet=False):
        self.source_dir = Path(source_dir)
        self.threshold = threshold
        self.max_per_folder = max_per_folder
        self.dry_run = dry_run
        self.logger = logger or (lambda x: print(x))
        self.quiet = quiet
        
        # Statistics
        self.stats = {
            'folders_scanned': 0,
            'folders_split': 0,
            'subfolders_created': 0,
            'images_processed': 0,
            'errors': 0
        }
        
        # Progress tracking
        self.last_progress_update = 0
        self.progress_interval = 10  # Print progress every N folders
        
        # Get supported image extensions from PhotoOrganizer
        self.image_extensions = PhotoOrganizer.get_image_extensions()
    
    def _show_progress(self, message="Processing..."):
        """Show progress indicator to stdout (always shown unless quiet mode)."""
        if not self.quiet and self.stats['folders_scanned'] > 0:
            if (self.stats['folders_scanned'] - self.last_progress_update) >= self.progress_interval:
                print(f"📁 Processed {self.stats['folders_scanned']} folders, {self.stats['folders_split']} split so far...")
                self.last_progress_update = self.stats['folders_scanned']
        
    def is_image_file(self, filepath):
        """Check if file is a supported image type."""
        return filepath.suffix.lower() in self.image_extensions
        
    def get_image_date(self, filepath):
        """Extract date from image file using ImageData.getImageDate()."""
        try:
            # Use the existing ImageData.getImageDate() method for consistency
            date_str = ImageData.getImageDate(str(filepath))
            
            # ImageData.getImageDate() returns "YYYY-MM-DD HH:MM" or "1900-01-01 00:00" for invalid dates
            if date_str and not date_str.startswith('1900'):
                try:
                    return datetime.strptime(date_str[:10], '%Y-%m-%d').date()
                except ValueError:
                    pass
            
            # Fallback to file modification time if ImageData returns invalid date
            return datetime.fromtimestamp(filepath.stat().st_mtime).date()
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error getting date for {filepath}: {e}")
            # Fallback to file modification time
            return datetime.fromtimestamp(filepath.stat().st_mtime).date()
    
    def scan_folder(self, folder_path):
        """Scan a folder for image files and return list with dates."""
        images = []
        folder_path = Path(folder_path)
        
        if not folder_path.is_dir():
            return images
            
        for file_path in folder_path.iterdir():
            if file_path.is_file() and self.is_image_file(file_path):
                try:
                    image_date = self.get_image_date(file_path)
                    images.append((file_path, image_date))
                except Exception as e:
                    if self.logger:
                        self.logger.debug(f"Error processing {file_path}: {e}")
                    self.stats['errors'] += 1
        
        return images
    
    def create_split_groups(self, images):
        """Group images into batches of max_per_folder, sorted by date."""
        # Sort images by date
        sorted_images = sorted(images, key=lambda x: x[1])
        
        groups = []
        current_batch = []
        date_counters = {}  # Track how many folders we've created for each date
        
        for image_path, image_date in sorted_images:
            current_batch.append((image_path, image_date))
            
            if len(current_batch) >= self.max_per_folder:
                # Use the latest date in this batch as the base folder name
                latest_date = max(item[1] for item in current_batch)
                
                # Create unique folder name using date + sequence number
                date_str = latest_date.strftime('%Y-%m-%d')
                if date_str not in date_counters:
                    date_counters[date_str] = 0
                
                date_counters[date_str] += 1
                if date_counters[date_str] == 1:
                    # First folder for this date - use date as-is
                    folder_name = date_str
                else:
                    # Subsequent folders for same date - add sequence number
                    folder_name = f"{date_str}_{date_counters[date_str]:02d}"
                
                groups.append((folder_name, current_batch))
                current_batch = []
        
        # Handle remaining images
        if current_batch:
            latest_date = max(item[1] for item in current_batch)
            
            # Create unique folder name
            date_str = latest_date.strftime('%Y-%m-%d')
            if date_str not in date_counters:
                date_counters[date_str] = 0
            
            date_counters[date_str] += 1
            if date_counters[date_str] == 1:
                folder_name = date_str
            else:
                folder_name = f"{date_str}_{date_counters[date_str]:02d}"
            
            groups.append((folder_name, current_batch))
        
        return groups
    
    def split_folder(self, folder_path):
        """Split a single folder if it meets the threshold."""
        folder_path = Path(folder_path)
        
        if self.logger:
            self.logger.debug(f"Scanning folder: {folder_path}")
        
        # Get all images in the folder
        images = self.scan_folder(folder_path)
        image_count = len(images)
        
        if self.logger:
            self.logger.debug(f"Found {image_count} images in {folder_path.name}")
        
        # Check if splitting is needed
        if image_count <= self.threshold:
            if self.logger:
                # Single INFO message for skipped folder
                self.logger.info(f"{folder_path} - skipped ({image_count} images)")
            return False
        
        # Create split groups
        groups = self.create_split_groups(images)
        
        if self.logger:
            self.logger.debug(f"Splitting {folder_path.name} into {len(groups)} subfolders")
        
        # Show split notification to stdout (always shown unless quiet mode)
        if not self.quiet:
            mode_text = "[DRY RUN] " if self.dry_run else ""
            print(f"✂️  {mode_text}Splitting '{folder_path.name}' ({image_count} images) → {len(groups)} subfolders")
        
        if not self.dry_run:
            for subfolder_name, batch in groups:
                # subfolder_name is already formatted as a string
                subfolder_path = folder_path / subfolder_name
                
                # Create the subfolder
                subfolder_path.mkdir(exist_ok=True)
                
                # Move images to subfolder
                for image_path, _ in batch:
                    try:
                        target_path = subfolder_path / image_path.name
                        # Handle filename conflicts by adding a counter
                        counter = 1
                        while target_path.exists():
                            stem = image_path.stem
                            suffix = image_path.suffix
                            target_path = subfolder_path / f"{stem}_{counter:03d}{suffix}"
                            counter += 1
                        
                        image_path.rename(target_path)
                        self.stats['images_processed'] += 1
                        
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Error moving {image_path} to {target_path}: {e}")
                        self.stats['errors'] += 1
                
                self.stats['subfolders_created'] += 1
                
                if self.logger:
                    # INFO message for created subfolder 
                    self.logger.info(f"{subfolder_path} - created ({len(batch)} images)")
        else:
            # Dry run - just log what would happen
            for subfolder_name, batch in groups:
                # subfolder_name is already formatted as a string
                subfolder_path = folder_path / subfolder_name
                if self.logger:
                    # INFO message for would-be created subfolder
                    self.logger.info(f"{subfolder_path} - created ({len(batch)} images)")
                self.stats['subfolders_created'] += 1
                self.stats['images_processed'] += len(batch)
        
        self.stats['folders_split'] += 1
        return True
    
    def run(self):
        """Main execution method to process all folders recursively."""
        if not self.source_dir.exists():
            raise ValueError(f"Source directory does not exist: {self.source_dir}")

        if not self.source_dir.is_dir():
            raise ValueError(f"Source path is not a directory: {self.source_dir}")

        if self.logger:
            self.logger.info(f"Starting folder splitting process")
            self.logger.info(f"Source: {self.source_dir}")
            self.logger.info(f"Threshold: {self.threshold} images")
            self.logger.info(f"Max per folder: {self.max_per_folder} images")

        # First check if the source directory itself needs splitting
        self.stats['folders_scanned'] += 1
        self._show_progress()
        try:
            self.split_folder(self.source_dir)
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error processing source folder {self.source_dir}: {e}")
            self.stats['errors'] += 1
        
        # Then recursively scan all subdirectories
        self._scan_recursively(self.source_dir)

        if self.logger:
            self.logger.info("Folder splitting process completed")
    
    def _scan_recursively(self, directory):
        """Recursively scan directory and all subdirectories for folders to split."""
        try:
            for item in directory.iterdir():
                if item.is_dir():
                    # Process this directory
                    self.stats['folders_scanned'] += 1
                    self._show_progress()
                    
                    try:
                        self.split_folder(item)
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Error processing folder {item}: {e}")
                        self.stats['errors'] += 1
                    
                    # Recursively scan subdirectories
                    # Only recurse if the folder wasn't split (to avoid scanning newly created subfolders)
                    if item.exists():  # Make sure folder still exists (wasn't renamed or moved)
                        try:
                            self._scan_recursively(item)
                        except Exception as e:
                            if self.logger:
                                self.logger.debug(f"Error recursively scanning {item}: {e}")
                            # Continue processing other directories
                            
        except PermissionError as e:
            if self.logger:
                self.logger.warning(f"Permission denied accessing {directory}: {e}")
            self.stats['errors'] += 1
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error scanning directory {directory}: {e}")
            self.stats['errors'] += 1

    def get_stats(self):
        """Return processing statistics."""
        return self.stats.copy()


def main():
    """Main entry point with consistent argument parsing and structure."""
    
    # Create argument parser
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    
    # Print standardized header
    parser.print_header()
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate and resolve required arguments
    try:
        resolved_args = parser.validate_required_args(args, {
            'source_dir': ['source_file', 'source']
        })
    except SystemExit:
        # Handle missing arguments
        source = getattr(args, 'source_file', None) or getattr(args, 'source', None)
        
        if not source:
            print("source directory is required", file=sys.stderr)
            sys.exit(1)
    
    # Setup logging with consistent pattern
    debug_mode = resolved_args.get('verbose')
    logger = parser.setup_logging(resolved_args, "split_folders")
    
    # Display configuration
    config_map = {
        'source_dir': 'Source directory'
    }
    parser.display_configuration(resolved_args, config_map)
    
    # Additional configuration display for split-specific options
    if not resolved_args.get('quiet'):
        print(f"Threshold: {resolved_args.get('threshold', 50)} images to trigger split")
        print(f"Max per folder: {resolved_args.get('max_per_folder', 50)} images per subfolder")
        print()
    
    try:
        # Initialize FolderSplitter with resolved arguments
        logger.info("Initializing FolderSplitter")
        logger.info(f"Source: {resolved_args['source_dir']}")
        logger.info(f"Threshold: {resolved_args.get('threshold', 50)}")
        logger.info(f"Max per folder: {resolved_args.get('max_per_folder', 50)}")
        
        splitter = FolderSplitter(
            source_dir=resolved_args['source_dir'],
            threshold=resolved_args.get('threshold', 50),
            max_per_folder=resolved_args.get('max_per_folder', 50),
            dry_run=resolved_args.get('dry_run', False),
            logger=logger,
            quiet=resolved_args.get('quiet', False)
        )
        
        logger.info("Starting folder splitting process")
        
        # Show startup message to stdout (clean by default, unless quiet)
        if not resolved_args.get('quiet'):
            print(f"🚀 Starting recursive scan of {resolved_args['source_dir']}")
            if resolved_args.get('dry_run'):
                print("   Mode: DRY RUN (simulation only)")
        
        # Run the splitting process
        splitter.run()
        
        # Show final progress update (unless quiet)
        if not resolved_args.get('quiet'):
            print(f"📁 Final: Processed {splitter.stats['folders_scanned']} folders total")
        
        # Get and log final statistics
        stats = splitter.get_stats()
        logger.info("Folder splitting completed successfully")
        logger.info(f"Folders scanned: {stats.get('folders_scanned', 0)}")
        logger.info(f"Folders split: {stats.get('folders_split', 0)}")
        logger.info(f"Subfolders created: {stats.get('subfolders_created', 0)}")
        logger.info(f"Images processed: {stats.get('images_processed', 0)}")
        logger.info(f"Errors encountered: {stats.get('errors', 0)}")
        
        # Show clean summary (unless quiet)
        if not resolved_args.get('quiet'):
            print()
            print("=" * 60)
            print("✅ FOLDER SPLITTING COMPLETE")
            print("=" * 60)
            print(f"📊 Summary:")
            print(f"   • Folders scanned: {stats.get('folders_scanned', 0)}")
            print(f"   • Folders split: {stats.get('folders_split', 0)}")
            print(f"   • Subfolders created: {stats.get('subfolders_created', 0)}")
            print(f"   • Images organized: {stats.get('images_processed', 0)}")
            if stats.get('errors', 0) > 0:
                print(f"   ⚠️  Errors: {stats.get('errors', 0)} (check log for details)")
            # Find the log file path from file handlers
            log_file = "N/A"
            for handler in logger.handlers:
                if hasattr(handler, 'baseFilename'):
                    log_file = handler.baseFilename
                    break
            print(f"📋 Detailed log: {log_file}")
            print("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error during folder splitting: {e}")
        if not resolved_args.get('quiet'):
            print(f"❌ Error: {e}")
            print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())