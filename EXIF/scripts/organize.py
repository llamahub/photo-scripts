#!/usr/bin/env python3
"""
Photo Organization Script - Organize photos by date using EXIF metadata

Organizes photos from a source directory into a target directory with structured
subdirectories based on photo dates obtained from EXIF metadata.

Target directory structure: <decade>/<year>/<year>-<month>/<parent folder>/<filename>
- <decade>: Decade in format "YYYY+" (e.g., 1990+, 2000+, 2010+)  
- <year>: 4-digit year (e.g., 1995, 2021)
- <month>: 2-digit month (e.g., 01, 02, 12)
- <parent folder>: Name of immediate parent folder from source
- <filename>: Original filename
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add project source paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

# Import COMMON logging
common_src_path = project_root.parent / 'COMMON' / 'src'
sys.path.insert(0, str(common_src_path))

try:
    from common.logging import ScriptLogging
    from exif.image_data import ImageData
except ImportError as e:
    print(f"Error importing required modules: {e}", file=sys.stderr)
    sys.exit(1)


class PhotoOrganizer:
    """Organizes photos by date using EXIF metadata."""
    
    # Supported image file extensions
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.heic', '.raw', '.cr2', '.nef', '.arw'}
    
    def __init__(self, source: Path, target: Path, dry_run: bool = False, debug: bool = False):
        self.source = Path(source).resolve()
        self.target = Path(target).resolve()
        self.dry_run = dry_run
        self.debug = debug
        
        # Setup logging using COMMON ScriptLogging (auto-detects script name and uses .log dir)
        self.logger = ScriptLogging.get_script_logger(debug=debug)
        
        # Statistics tracking
        self.stats = {
            'processed': 0,
            'copied': 0,
            'skipped': 0,
            'errors': 0
        }

    def is_image_file(self, file_path: Path) -> bool:
        """Check if file is a supported image format."""
        return file_path.suffix.lower() in self.IMAGE_EXTENSIONS

    def get_decade_folder(self, year: int) -> str:
        """Get decade folder name in format 'YYYY+'."""
        decade_start = (year // 10) * 10
        return f"{decade_start}+"

    def get_target_path(self, source_file: Path, image_date: str) -> Path:
        """
        Calculate target path based on image date and source structure.
        
        Format: <decade>/<year>/<year>-<month>/<parent folder>/<filename>
        """
        # Parse date (format: "YYYY-MM-DD HH:MM" or "YYYY-MM-DD")
        try:
            date_part = image_date.split(' ')[0]  # Get just the date part
            year, month, day = date_part.split('-')
            year_int = int(year)
            month_str = month.zfill(2)
        except (ValueError, IndexError) as e:
            self.logger.error(f"Invalid date format '{image_date}' for {source_file}: {e}")
            # Fallback to unknown date structure
            year_int = 1900
            year = "1900"
            month_str = "01"

        # Get parent folder name (immediate parent of the file)
        parent_folder = source_file.parent.name
        
        # Build target path structure
        decade = self.get_decade_folder(year_int)
        year_month = f"{year}-{month_str}"
        
        target_path = self.target / decade / year / year_month / parent_folder / source_file.name
        
        return target_path

    def find_images(self) -> List[Path]:
        """Find all image files in source directory recursively."""
        images = []
        
        try:
            self.logger.info(f"Scanning source directory: {self.source}")
            
            for root, dirs, files in os.walk(self.source):
                root_path = Path(root)
                
                for file in files:
                    file_path = root_path / file
                    if self.is_image_file(file_path):
                        images.append(file_path)
                        
                        if len(images) % 100 == 0:  # Progress indicator
                            self.logger.debug(f"Found {len(images)} images so far...")
                            
        except PermissionError as e:
            self.logger.error(f"Permission denied accessing {self.source}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error while scanning {self.source}: {e}")
        
        self.logger.info(f"Found {len(images)} image files to process")
        return images

    def copy_image(self, source_file: Path, target_file: Path):
        """Copy image file to target location."""
        try:
            # Create target directory if it doesn't exist
            if not self.dry_run:
                target_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Check if target file already exists
                if target_file.exists():
                    self.logger.warning(f"Target file already exists, skipping: {target_file}")
                    self.stats['skipped'] += 1
                    return False
                
                # Copy the file
                shutil.copy2(source_file, target_file)
                self.stats['copied'] += 1
            else:
                # Dry run - just log what would happen
                self.stats['copied'] += 1
                
            action = "Would copy" if self.dry_run else "Copied"
            self.logger.debug(f"{action}: {source_file} -> {target_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error copying {source_file} to {target_file}: {e}")
            self.stats['errors'] += 1
            return False

    def process_image(self, image_file: Path):
        """Process a single image file."""
        try:
            self.stats['processed'] += 1
            
            # Get image date using ImageData class
            image_date = ImageData.getImageDate(str(image_file))
            
            if not image_date or image_date.startswith("1900"):
                self.logger.warning(f"No valid date found for {image_file}, using fallback date")
                # Use file modification time as fallback
                try:
                    mtime = image_file.stat().st_mtime
                    fallback_date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                    image_date = fallback_date
                except Exception:
                    image_date = "1900-01-01 00:00"
            
            # Calculate target path
            target_file = self.get_target_path(image_file, image_date)
            
            # Log the mapping
            rel_source = image_file.relative_to(self.source)
            rel_target = target_file.relative_to(self.target)
            self.logger.debug(f"Date: {image_date} | {rel_source} -> {rel_target}")
            
            # Copy the file
            self.copy_image(image_file, target_file)
            
        except Exception as e:
            self.logger.error(f"Error processing {image_file}: {e}")
            self.stats['errors'] += 1

    def run(self):
        """Execute the photo organization process."""
        # Log header
        mode = "DRY RUN" if self.dry_run else "LIVE MODE"
        debug_status = "ENABLED" if self.debug else "DISABLED"
        
        header = [
            "=" * 80,
            f" [organize.py] Organize photos by date - {mode}",
            "=" * 80,
            f"SOURCE: {self.source}",
            f"TARGET: {self.target}",
            f"DRY RUN: {self.dry_run}",
            f"DEBUG: {debug_status}",
            "=" * 80
        ]
        
        for line in header:
            self.logger.info(line)
        
        # Validate source directory
        if not self.source.exists():
            raise FileNotFoundError(f"Source directory '{self.source}' does not exist")
        if not self.source.is_dir():
            raise NotADirectoryError(f"Source '{self.source}' is not a directory")
        
        # Create target directory (unless dry run)
        if not self.dry_run:
            self.target.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created target directory: {self.target}")
        else:
            self.logger.info(f"Target directory (dry run): {self.target}")
        
        # Find all images
        images = self.find_images()
        
        if not images:
            self.logger.info("No image files found to process")
            return
        
        # Process each image
        self.logger.info(f"Starting to process {len(images)} images...")
        
        for i, image_file in enumerate(images, 1):
            if i % 50 == 0 or i == len(images):  # Progress indicator
                self.logger.info(f"Progress: {i}/{len(images)} images processed")
            
            self.process_image(image_file)
        
        # Log final statistics
        summary = [
            "=" * 80,
            " ORGANIZATION COMPLETE",
            "=" * 80,
            f"Total files processed: {self.stats['processed']}",
            f"Files copied: {self.stats['copied']}",
            f"Files skipped: {self.stats['skipped']}",
            f"Errors encountered: {self.stats['errors']}",
        ]
        
        if self.dry_run:
            summary.append("NOTE: This was a dry run - no files were actually copied")
        
        summary.append("=" * 80)
        
        for line in summary:
            self.logger.info(line)


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Organize photos by date using EXIF metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Target directory structure:
  <decade>/<year>/<year>-<month>/<parent folder>/<filename>

Where:
  - <decade>: Decade in format "YYYY+" (e.g., 1990+, 2000+, 2010+)
  - <year>: 4-digit year (e.g., 1995, 2021)
  - <month>: 2-digit month (e.g., 01, 02, 12)  
  - <parent folder>: Name of immediate parent folder from source
  - <filename>: Original filename

Examples:
  %(prog)s /path/to/photos /path/to/organized
  %(prog)s --source /path/to/photos --target /path/to/organized --dry-run
  %(prog)s /path/to/photos /path/to/organized --debug
        """
    )
    
    # Positional arguments
    parser.add_argument('source', nargs='?', help='Source directory containing photos')
    parser.add_argument('target', nargs='?', help='Target directory for organized photos')
    
    # Named arguments
    parser.add_argument('--source', dest='source_named', 
                       help='Source directory containing photos (required)')
    parser.add_argument('--target', dest='target_named', 
                       help='Target directory for organized photos (required)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without actually copying files')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug output with detailed logging')
    
    args = parser.parse_args()
    
    # Determine source and target
    source = args.source_named or args.source
    target = args.target_named or args.target
    
    if not source:
        parser.error("source directory is required")
    if not target:
        parser.error("target directory is required")
    
    try:
        organizer = PhotoOrganizer(
            source=source,
            target=target,
            dry_run=args.dry_run,
            debug=args.debug
        )
        
        organizer.run()
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())