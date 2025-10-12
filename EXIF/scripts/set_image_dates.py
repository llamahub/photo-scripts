#!/usr/bin/env python3
"""Update EXIF dates in images based on CSV input with Set Date column."""

import sys
import argparse
import csv
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# Standard COMMON import pattern
common_src_path = Path(__file__).parent.parent.parent / 'COMMON' / 'src'
sys.path.insert(0, str(common_src_path))

try:
    from common.logging import ScriptLogging
except ImportError:
    import logging
    ScriptLogging = None


class ImageDateSetter:
    """Updates EXIF dates in image files using ExifTool."""
    
    def __init__(self, logger=None):
        self.logger = logger or self._setup_fallback_logger()
        self.stats = {
            'processed': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
    
    def _setup_fallback_logger(self):
        """Set up basic logging if COMMON framework not available."""
        import logging
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger("set_image_dates")
    
    def validate_exiftool(self) -> bool:
        """Check if ExifTool is available."""
        try:
            result = subprocess.run(['exiftool', '-ver'], 
                                   capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip()
                self.logger.info(f"ExifTool version {version} found")
                return True
            else:
                self.logger.error("ExifTool command failed")
                return False
        except FileNotFoundError:
            self.logger.error("ExifTool not found. Please install ExifTool to use this script.")
            return False
        except subprocess.TimeoutExpired:
            self.logger.error("ExifTool command timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error checking ExifTool: {e}")
            return False
    
    def parse_date(self, date_str: str) -> str:
        """Parse various date formats into ExifTool format (YYYY:MM:DD HH:MM:SS)."""
        if not date_str or date_str.strip() == "":
            return None
        
        date_str = date_str.strip()
        
        # Common date formats to try
        formats = [
            "%Y-%m-%d %H:%M:%S",  # 2023-08-20 15:45:30
            "%Y-%m-%d %H:%M",     # 2023-08-20 15:45
            "%Y-%m-%d",           # 2023-08-20
            "%Y/%m/%d %H:%M:%S",  # 2023/08/20 15:45:30
            "%Y/%m/%d %H:%M",     # 2023/08/20 15:45
            "%Y/%m/%d",           # 2023/08/20
            "%m/%d/%Y %H:%M:%S",  # 08/20/2023 15:45:30
            "%m/%d/%Y %H:%M",     # 08/20/2023 15:45
            "%m/%d/%Y",           # 08/20/2023
            "%m/%d/%y %H:%M:%S",  # 8/20/24 15:45:30 (2-digit year)
            "%m/%d/%y %H:%M",     # 8/20/24 15:45
            "%m/%d/%y",           # 8/20/24 (2-digit year)
            "%Y:%m:%d %H:%M:%S",  # 2023:08:20 15:45:30 (EXIF format)
            "%Y:%m:%d %H:%M",     # 2023:08:20 15:45
            "%Y:%m:%d",           # 2023:08:20
        ]
        
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                # Return in ExifTool format
                return parsed_date.strftime("%Y:%m:%d %H:%M:%S")
            except ValueError:
                continue
        
        self.logger.warning(f"Could not parse date format: '{date_str}'")
        return None
    
    def detect_file_type(self, image_path: Path) -> str:
        """Detect the actual file type using ExifTool."""
        try:
            cmd = ['exiftool', '-FileType', '-s3', str(image_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return result.stdout.strip().upper()
            else:
                return None
        except Exception as e:
            self.logger.debug(f"Error detecting file type for {image_path}: {e}")
            return None
    
    def get_correct_extension(self, file_type: str) -> str:
        """Map file type to correct extension."""
        extension_map = {
            'JPEG': '.jpg',
            'PNG': '.png',
            'TIFF': '.tif',
            'GIF': '.gif',
            'BMP': '.bmp',
            'WEBP': '.webp',
            'HEIC': '.heic',
            'HEIF': '.heif',
            'MOV': '.mov',
            'MP4': '.mp4',
            'AVI': '.avi'
        }
        return extension_map.get(file_type, None)
    
    def fix_file_extension(self, image_path: Path, dry_run: bool = False) -> Path:
        """Check and fix file extension if it doesn't match the actual file type."""
        actual_type = self.detect_file_type(image_path)
        
        if not actual_type:
            self.logger.warning(f"Could not detect file type for {image_path}")
            return image_path
        
        correct_extension = self.get_correct_extension(actual_type)
        if not correct_extension:
            self.logger.warning(f"Unknown file type '{actual_type}' for {image_path}")
            return image_path
        
        current_extension = image_path.suffix.lower()
        
        if current_extension != correct_extension:
            # Handle cases like .jpg.png - remove all suffixes and add correct one
            name_without_extensions = image_path.name
            # Remove all known extensions from the end
            while any(name_without_extensions.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.heic', '.heif', '.mov', '.mp4', '.avi']):
                name_without_extensions = str(Path(name_without_extensions).stem)
            
            # Create new path with correct extension
            new_path = image_path.parent / (name_without_extensions + correct_extension)
            
            if dry_run:
                self.logger.info(f"DRY RUN: Would rename {image_path} → {new_path} (detected {actual_type})")
                return new_path
            else:
                try:
                    image_path.rename(new_path)
                    self.logger.info(f"Renamed {image_path} → {new_path} (detected {actual_type})")
                    return new_path
                except Exception as e:
                    self.logger.error(f"Failed to rename {image_path}: {e}")
                    return image_path
        
        return image_path
    
    def set_image_date(self, image_path: Path, exif_date: str, dry_run: bool = False, fix_extensions: bool = True) -> bool:
        """Update EXIF dates for a single image using ExifTool."""
        try:
            if not image_path.exists():
                self.logger.error(f"Image file not found: {image_path}")
                return False
            
            # First, check and fix file extension if needed
            if fix_extensions:
                corrected_path = self.fix_file_extension(image_path, dry_run)
            else:
                corrected_path = image_path
            
            # ExifTool command to set multiple date fields
            cmd = [
                'exiftool', 
                '-overwrite_original',
                f'-DateTimeOriginal={exif_date}',
                f'-ExifIFD:DateTimeOriginal={exif_date}',
                f'-XMP-photoshop:DateCreated={exif_date}',
                f'-FileModifyDate={exif_date}',
                str(corrected_path)
            ]
            
            if dry_run:
                self.logger.info(f"DRY RUN: Would update {corrected_path} with date {exif_date}")
                self.logger.debug(f"DRY RUN: Command would be: {' '.join(cmd)}")
                return True
            
            self.logger.debug(f"Running ExifTool command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.logger.info(f"Updated {corrected_path} with date {exif_date}")
                return True
            else:
                self.logger.error(f"ExifTool failed for {corrected_path}: {result.stderr.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"ExifTool timeout for {image_path}")
            return False
        except Exception as e:
            self.logger.error(f"Error updating {image_path}: {e}")
            return False
    
    def process_csv(self, csv_path: Path, target_folder: Path = None, file_col: str = "Source Path", date_col: str = "Set Date", dry_run: bool = False, fix_extensions: bool = True) -> None:
        """Process CSV file to update image dates."""
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        
        self.logger.info(f"Processing CSV: {csv_path}")
        if target_folder:
            self.logger.info(f"Target folder: {target_folder}")
        else:
            self.logger.info("Target folder: Using paths from CSV directly")
        self.logger.info(f"File column: '{file_col}'")
        self.logger.info(f"Date column: '{date_col}'")
        self.logger.info(f"Fix extensions: {'Enabled' if fix_extensions else 'Disabled'}")
        self.logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        
        with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Validate columns exist
            if file_col not in reader.fieldnames:
                raise ValueError(f"File column '{file_col}' not found in CSV. Available columns: {reader.fieldnames}")
            if date_col not in reader.fieldnames:
                raise ValueError(f"Date column '{date_col}' not found in CSV. Available columns: {reader.fieldnames}")
            
            rows = list(reader)
            total_rows = len(rows)
            
            self.logger.info(f"Found {total_rows} rows in CSV")
            
            for i, row in enumerate(rows):
                self.stats['processed'] += 1
                
                # Get file path and date from CSV
                source_file_path = row.get(file_col, '').strip()
                set_date = row.get(date_col, '').strip()
                
                # Progress logging
                if (i + 1) % 10 == 0 or i == len(rows) - 1:
                    self.logger.info(f"Progress: {i + 1}/{total_rows}")
                
                # Skip if no date specified
                if not set_date:
                    self.logger.debug(f"Skipping {source_file_path}: no date specified")
                    self.stats['skipped'] += 1
                    continue
                
                # Parse the date
                exif_date = self.parse_date(set_date)
                if not exif_date:
                    self.logger.error(f"Invalid date format '{set_date}' for {source_file_path}")
                    self.stats['errors'] += 1
                    continue
                
                # Use path directly from CSV (analyze.py provides complete paths)
                # If target_folder is provided and path is relative, combine them
                source_path = Path(source_file_path)
                if target_folder and not source_path.is_absolute() and not source_path.exists():
                    target_path = target_folder / source_path
                else:
                    target_path = source_path
                
                # Update the image
                if self.set_image_date(target_path, exif_date, dry_run, fix_extensions):
                    self.stats['updated'] += 1
                else:
                    self.stats['errors'] += 1
    
    def print_summary(self) -> None:
        """Print processing summary statistics."""
        self.logger.info("=" * 50)
        self.logger.info("PROCESSING SUMMARY")
        self.logger.info("=" * 50)
        self.logger.info(f"Total processed: {self.stats['processed']}")
        self.logger.info(f"Successfully updated: {self.stats['updated']}")
        self.logger.info(f"Skipped (no date): {self.stats['skipped']}")
        self.logger.info(f"Errors: {self.stats['errors']}")
        
        if self.stats['processed'] > 0:
            success_rate = (self.stats['updated'] / self.stats['processed']) * 100
            self.logger.info(f"Success rate: {success_rate:.1f}%")


def main():
    parser = argparse.ArgumentParser(
        description="Update EXIF dates in images based on CSV input with Set Date column",
        epilog="""
Examples:
  %(prog)s analysis.csv
  %(prog)s analysis.csv --dry-run
  %(prog)s analysis.csv --file-col "Source Path" --date-col "Set Date"
  %(prog)s analysis.csv --no-fix-extensions  # Disable automatic extension fixing
  %(prog)s analysis.csv --target /path/to/photos  # Only if CSV has relative paths
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('input', help='Path to CSV file with file paths and dates')
    parser.add_argument('--target', help='Target folder (optional - only needed if CSV has relative paths)')
    parser.add_argument('--file-col', default='Source Path', 
                       help='Header name for column containing file paths (default: "Source Path")')
    parser.add_argument('--date-col', default='Set Date', 
                       help='Header name for column containing dates to set (default: "Set Date")')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without actually updating files')
    parser.add_argument('--fix-extensions', action='store_true',
                       help='Automatically rename files with incorrect extensions (default: enabled)')
    parser.add_argument('--no-fix-extensions', action='store_true',
                       help='Disable automatic extension fixing')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()
    
    # Handle fix-extensions logic (default is True unless --no-fix-extensions is specified)
    fix_extensions = not args.no_fix_extensions
    
    # Standard logging setup
    if ScriptLogging:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        logger = ScriptLogging.get_script_logger(
            name=f"set_image_dates_{timestamp}",
            debug=args.debug
        )
    else:
        import logging
        level = logging.DEBUG if args.debug else logging.INFO
        logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger("set_image_dates")
    
    logger.info("Starting EXIF date update process")
    
    try:
        # Validate inputs - target folder is now optional
        target_folder = None
        if args.target:
            target_folder = Path(args.target)
            if not target_folder.exists():
                logger.error(f"Target folder does not exist: {target_folder}")
                return 1
            if not target_folder.is_dir():
                logger.error(f"Target path is not a directory: {target_folder}")
                return 1
        
        csv_path = Path(args.input)
        if not csv_path.exists():
            logger.error(f"CSV file does not exist: {csv_path}")
            return 1
        
        # Create date setter and validate ExifTool
        setter = ImageDateSetter(logger)
        
        if not setter.validate_exiftool():
            logger.error("ExifTool validation failed. Please install ExifTool.")
            return 1
        
        # Process the CSV
        setter.process_csv(
            csv_path=csv_path,
            target_folder=target_folder,
            file_col=args.file_col,
            date_col=args.date_col,
            dry_run=args.dry_run,
            fix_extensions=fix_extensions
        )
        
        # Print summary
        setter.print_summary()
        
        if args.dry_run:
            logger.info("DRY RUN completed - no files were actually modified")
        else:
            logger.info("EXIF date update process completed")
        
        return 0
        
    except Exception as e:
        logger.error(f"Script failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())