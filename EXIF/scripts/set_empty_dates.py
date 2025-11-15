#!/usr/bin/env python3
"""
================================================================================
=== [set_empty_dates] - Sets DateTimeOriginal for images missing this field
================================================================================
"""

import sys
import os
from pathlib import Path

# Add COMMON to path for shared utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'COMMON', 'src'))

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

# Script metadata
SCRIPT_NAME = 'set_empty_dates'
SCRIPT_INFO = {
    'name': SCRIPT_NAME,
    'description': 'Sets the original date for all images in a target folder where this date is currently not set',
    'examples': [
        '--target /photos/2023',
        '--target /photos/2023 --dry-run'
    ]
}

SCRIPT_ARGUMENTS = {
    'target': {
        'positional': True,
        'flag': '--target',
        'help': 'Root folder to scan and update images in',
        'required': False
    },
    'input': {
        'flag': '--input',
        'help': 'CSV file containing list of files to process',
        'required': False
    },
    'file_column': {
        'flag': '--file-column',
        'help': 'Column name in CSV for file paths (default: file)',
        'default': 'file',
        'required': False
    },
    'dry_run': {
        'flag': '--dry-run',
        'action': 'store_true',
        'help': 'Log updates but do not action'
    }
}

ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)

class EmptyDateManager:
    def __init__(self, target_folder=None, dry_run=False, logger=None, input_csv=None, file_column='file'):
        self.target_folder = target_folder
        self.dry_run = dry_run
        self.logger = logger
        self.input_csv = input_csv
        self.file_column = file_column
        # Import here to avoid circular import
        from exif.image_data import ImageData
        self.ImageData = ImageData

    def find_images(self):
        """Yield image file paths to process, from CSV or by scanning folder."""
        if self.input_csv:
            import csv
            with open(self.input_csv, newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    file_path = row.get(self.file_column)
                    if file_path:
                        yield file_path
        else:
            image_exts = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.cr2', '.nef', '.orf', '.raf', '.rw2', '.heic', '.heif'}
            for root, _, files in os.walk(self.target_folder):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in image_exts:
                        yield os.path.join(root, f)

    def get_datetimeoriginal(self, exif_data):
        return exif_data.get('DateTimeOriginal') or exif_data.get('EXIF:DateTimeOriginal')

    def set_date(self, image_path, new_date):
        """Set DateTimeOriginal using exiftool, preserving atime/mtime."""
        import subprocess
        if self.dry_run:
            self.logger.info(f"[DRY-RUN] Would set DateTimeOriginal={new_date} for {image_path}")
            return True
        # Record original timestamps
        try:
            stat = os.stat(image_path)
            orig_mtime = stat.st_mtime
            orig_atime = stat.st_atime
        except Exception as e:
            self.logger.warning(f"Could not stat {image_path} to preserve timestamps: {e}")
            orig_mtime = orig_atime = None
        cmd = [
            'exiftool',
            '-overwrite_original',
            '-P',  # preserve file modification date/time
            f'-DateTimeOriginal={new_date}',
            image_path
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                self.logger.info(f"Set DateTimeOriginal={new_date} for {image_path}")
                # Restore atime/mtime in case exiftool did not fully preserve
                if orig_atime is not None and orig_mtime is not None:
                    try:
                        os.utime(image_path, (orig_atime, orig_mtime))
                    except Exception as e:
                        self.logger.warning(f"Failed to restore timestamps for {image_path}: {e}")
                return True
            else:
                self.logger.error(f"Failed to set DateTimeOriginal for {image_path}: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Exception setting DateTimeOriginal for {image_path}: {e}")
            return False

    # (Removed broken/duplicate code from previous patch)
    def process(self):
        updated = 0
        skipped = 0
        for img_path in self.find_images():
            exif_data = self.ImageData.get_exif(img_path)
            dt_orig = self.get_datetimeoriginal(exif_data)
            if dt_orig:
                self.logger.info(f"[SKIP] {img_path} already has DateTimeOriginal: {dt_orig}")
                skipped += 1
                continue
            # Try to get a date to set
            date_to_set = self.ImageData.getImageDate(img_path)
            if not date_to_set or date_to_set == '1900-01-01 00:00':
                date_to_set = self.ImageData.getFilenameDate(img_path)
            if not date_to_set or date_to_set == '1900-01-01 00:00':
                self.logger.warning(f"[NO DATE] Could not determine date for {img_path}")
                skipped += 1
                continue
            # exiftool expects format YYYY:MM:DD HH:MM:SS
            date_to_set_fmt = date_to_set.replace('-', ':', 2)
            if len(date_to_set_fmt) == 16:
                date_to_set_fmt += ':00'  # Add seconds if missing
            self.set_date(img_path, date_to_set_fmt)
            updated += 1
        self.logger.info(f"Done. Updated {updated} images, skipped {skipped}.")


def main():
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    parser.print_header()
    args = parser.parse_args()
    target = getattr(args, 'target', None)
    input_csv = getattr(args, 'input', None)
    file_column = getattr(args, 'file_column', 'file')
    dry_run = getattr(args, 'dry_run', False)
    if not target and not input_csv:
        parser.error('Either --target or --input must be provided.')
    if target and not os.path.exists(target):
        parser.error('Target folder must exist.')
    if input_csv and not os.path.exists(input_csv):
        parser.error('Input CSV file must exist.')
    logger = parser.setup_logging(vars(args), SCRIPT_NAME)
    parser.display_configuration(vars(args), {'target': 'Target folder', 'input': 'Input CSV', 'file_column': 'File column'})
    mgr = EmptyDateManager(target_folder=target, dry_run=dry_run, logger=logger, input_csv=input_csv, file_column=file_column)
    mgr.process()

if __name__ == '__main__':
    main()
