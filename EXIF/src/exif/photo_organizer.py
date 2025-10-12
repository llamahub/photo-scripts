"""
Photo Organization Module - Organize photos by date using EXIF metadata

Contains the PhotoOrganizer class for organizing photos from a source directory
into a target directory with structured subdirectories based on photo dates.

Target directory structure: <decade>/<year>/<year>-<month>/<parent folder>/<filename>
- <decade>: Decade in format "YYYY+" (e.g., 1990+, 2000+, 2010+)
- <year>: 4-digit year (e.g., 1995, 2021)
- <month>: 2-digit month (e.g., 01, 02, 12)
- <parent folder>: Name of immediate parent folder from source
- <filename>: Original filename
"""

import os
import shutil
import concurrent.futures
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from .image_data import ImageData

# Import COMMON logging with fallback
try:
    import sys
    from pathlib import Path

    common_src_path = Path(__file__).parent.parent.parent.parent / "COMMON" / "src"
    sys.path.insert(0, str(common_src_path))
    from common.logging import ScriptLogging
except ImportError:
    # Fallback for when COMMON logging is not available
    import logging

    ScriptLogging = None


class PhotoOrganizer:
    """Organizes photos by date using EXIF metadata."""

    # Supported image file extensions
    IMAGE_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".tif",
        ".tiff",
        ".heic",
        ".raw",
        ".cr2",
        ".nef",
        ".arw",
    }

    # Supported video file extensions
    VIDEO_EXTENSIONS = {
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".wmv",
        ".flv",
        ".webm",
        ".m4v",
        ".3gp",
        ".mts",
        ".m2ts",
        ".ts",
    }

    def __init__(
        self,
        source: Path,
        target: Path,
        dry_run: bool = False,
        debug: bool = False,
        move_files: bool = False,
        max_workers: int = None,
        video_mode: bool = False,
    ):
        """
        Initialize PhotoOrganizer.

        Args:
            source: Source directory containing photos
            target: Target directory for organized photos
            dry_run: If True, show what would be done without actually copying files
            debug: If True, enable debug logging
            move_files: If True, move files instead of copying them
            max_workers: Number of parallel workers (default: CPU count)
            video_mode: If True, process video files instead of image files
        """
        self.source = Path(source).resolve()
        self.target = Path(target).resolve()
        self.dry_run = dry_run
        self.debug = debug
        self.move_files = move_files
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.video_mode = video_mode

        # Setup logging
        self._setup_logging()

        # Statistics tracking
        action = "moved" if move_files else "copied"
        self.stats = {"processed": 0, action: 0, "skipped": 0, "errors": 0}

        # Set file type for logging
        self.file_type = "video" if video_mode else "image"

    def _setup_logging(self):
        """Setup logging using COMMON ScriptLogging if available, otherwise fallback."""
        if ScriptLogging:
            # Use COMMON ScriptLogging (auto-detects script name and uses .log dir)
            self.logger = ScriptLogging.get_script_logger(debug=self.debug)
        else:
            # Fallback logging setup
            import logging

            logging.basicConfig(
                level=logging.DEBUG if self.debug else logging.INFO,
                format="%(asctime)s - %(levelname)s - %(message)s",
            )
            self.logger = logging.getLogger(__name__)

    def is_image_file(self, file_path: Path) -> bool:
        """Check if file is a supported image format."""
        return file_path.suffix.lower() in self.IMAGE_EXTENSIONS

    def is_video_file(self, file_path: Path) -> bool:
        """Check if file is a supported video format."""
        return file_path.suffix.lower() in self.VIDEO_EXTENSIONS

    def is_target_file(self, file_path: Path) -> bool:
        """Check if file matches the current mode (image or video)."""
        if self.video_mode:
            return self.is_video_file(file_path)
        else:
            return self.is_image_file(file_path)

    def get_decade_folder(self, year: int) -> str:
        """Get decade folder name in format 'YYYY+'."""
        decade_start = (year // 10) * 10
        return f"{decade_start}+"

    def get_target_path(self, source_file: Path, image_date: str) -> Path:
        """
        Calculate target path based on image date and source structure.

        Format: <decade>/<year>/<year>-<month>/<parent folder>/<filename>

        Args:
            source_file: Source file path
            image_date: Image date in format "YYYY-MM-DD HH:MM" or "YYYY-MM-DD"

        Returns:
            Target file path
        """
        # Parse date (format: "YYYY-MM-DD HH:MM" or "YYYY-MM-DD")
        try:
            date_part = image_date.split(" ")[0]  # Get just the date part
            year, month, day = date_part.split("-")
            year_int = int(year)
            month_str = month.zfill(2)
        except (ValueError, IndexError) as e:
            self.logger.error(
                f"Invalid date format '{image_date}' for {source_file}: {e}"
            )
            # Fallback to unknown date structure
            year_int = 1900
            year = "1900"
            month_str = "01"

        # Get parent folder name (immediate parent of the file)
        parent_folder = source_file.parent.name

        # Build target path structure
        decade = self.get_decade_folder(year_int)
        year_month = f"{year}-{month_str}"

        target_path = (
            self.target / decade / year / year_month / parent_folder / source_file.name
        )

        return target_path

    def find_files(self) -> List[Path]:
        """
        Find all target files (images or videos) in source directory recursively.

        Returns:
            List of file paths
        """
        files = []

        try:
            self.logger.info(f"Scanning source directory: {self.source}")

            for root, dirs, filenames in os.walk(self.source):
                root_path = Path(root)

                for filename in filenames:
                    file_path = root_path / filename
                    if self.is_target_file(file_path):
                        files.append(file_path)

                        if len(files) % 100 == 0:  # Progress indicator
                            self.logger.debug(f"Found {len(files)} {self.file_type} files so far...")

        except PermissionError as e:
            self.logger.error(f"Permission denied accessing {self.source}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error while scanning {self.source}: {e}")

        self.logger.info(f"Found {len(files)} {self.file_type} files to process")
        return files

    def copy_file(self, source_file: Path, target_file: Path) -> bool:
        """
        Copy or move file to target location.

        Args:
            source_file: Source file path
            target_file: Target file path

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create target directory if it doesn't exist
            if not self.dry_run:
                target_file.parent.mkdir(parents=True, exist_ok=True)

                # Check if target file already exists
                if target_file.exists():
                    self.logger.warning(
                        f"Target file already exists, skipping: {target_file}"
                    )
                    self.stats["skipped"] += 1
                    return False

                # Move or copy the file
                if self.move_files:
                    shutil.move(str(source_file), str(target_file))
                    action_key = "moved"
                else:
                    shutil.copy2(source_file, target_file)
                    action_key = "copied"

                self.stats[action_key] += 1
            else:
                # Dry run - just log what would happen
                action_key = "moved" if self.move_files else "copied"
                self.stats[action_key] += 1

            operation = "move" if self.move_files else "copy"
            action = (
                f"Would {operation}"
                if self.dry_run
                else f"{'Moved' if self.move_files else 'Copied'}"
            )
            self.logger.debug(f"{action}: {source_file} -> {target_file}")
            return True

        except Exception as e:
            operation = "moving" if self.move_files else "copying"
            self.logger.error(f"Error {operation} {source_file} to {target_file}: {e}")
            self.stats["errors"] += 1
            return False

    def process_file(self, file_path: Path):
        """
        Process a single file (image or video).

        Args:
            file_path: Path to file to process
        """
        try:
            self.stats["processed"] += 1

            # Get file date using ImageData class (works for both images and videos via exiftool)
            file_date = ImageData.getImageDate(str(file_path))

            if not file_date or file_date.startswith("1900"):
                self.logger.warning(
                    f"No valid date found for {file_path}, using fallback date"
                )
                # Use file modification time as fallback
                try:
                    mtime = file_path.stat().st_mtime
                    fallback_date = datetime.fromtimestamp(mtime).strftime(
                        "%Y-%m-%d %H:%M"
                    )
                    file_date = fallback_date
                except Exception:
                    file_date = "1900-01-01 00:00"

            # Calculate target path
            target_file = self.get_target_path(file_path, file_date)

            # Log the mapping
            rel_source = file_path.relative_to(self.source)
            rel_target = target_file.relative_to(self.target)
            self.logger.debug(f"Date: {file_date} | {rel_source} -> {rel_target}")

            # Copy the file
            self.copy_file(file_path, target_file)

        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            self.stats["errors"] += 1

    def run(self):
        """Execute the photo organization process."""
        # Log header
        mode = "DRY RUN" if self.dry_run else "LIVE MODE"
        debug_status = "ENABLED" if self.debug else "DISABLED"
        file_type_title = "videos" if self.video_mode else "photos"

        header = [
            "=" * 80,
            f" [PhotoOrganizer] Organize {file_type_title} by date - {mode}",
            "=" * 80,
            f"SOURCE: {self.source}",
            f"TARGET: {self.target}",
            f"FILE TYPE: {self.file_type.upper()}",
            f"DRY RUN: {self.dry_run}",
            f"DEBUG: {debug_status}",
            "=" * 80,
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

        # Find all files
        files = self.find_files()

        if not files:
            self.logger.info(f"No {self.file_type} files found to process")
            return

        # Process each file (with parallel processing)
        operation = "move" if self.move_files else "copy"
        self.logger.info(
            f"Starting to {operation} {len(files)} {self.file_type} files using {self.max_workers} workers..."
        )

        if self.max_workers == 1:
            # Single-threaded processing
            for i, file_path in enumerate(files, 1):
                if i % 50 == 0 or i == len(files):  # Progress indicator
                    self.logger.info(f"Progress: {i}/{len(files)} {self.file_type} files processed")
                self.process_file(file_path)
        else:
            # Multi-threaded processing
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_workers
            ) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(self.process_file, file_path): file_path
                    for file_path in files
                }

                # Process completed tasks
                completed = 0
                for future in concurrent.futures.as_completed(future_to_file):
                    completed += 1
                    if completed % 50 == 0 or completed == len(files):
                        self.logger.info(
                            f"Progress: {completed}/{len(files)} {self.file_type} files processed"
                        )

                    try:
                        future.result()  # This will raise any exception that occurred
                    except Exception as e:
                        file_path = future_to_file[future]
                        self.logger.error(f"Error processing {file_path}: {e}")
                        self.stats["errors"] += 1

        # Log final statistics
        operation = "moved" if self.move_files else "copied"
        action_count = self.stats.get("moved", 0) + self.stats.get("copied", 0)

        summary = [
            "=" * 80,
            " ORGANIZATION COMPLETE",
            "=" * 80,
            f"Total files processed: {self.stats['processed']}",
            f"Files {operation}: {action_count}",
            f"Files skipped: {self.stats['skipped']}",
            f"Errors encountered: {self.stats['errors']}",
        ]

        if self.dry_run:
            operation_verb = "moved" if self.move_files else "copied"
            summary.append(
                f"NOTE: This was a dry run - no files were actually {operation_verb}"
            )

        summary.append("=" * 80)

        for line in summary:
            self.logger.info(line)

    def get_stats(self) -> dict:
        """
        Get current processing statistics.

        Returns:
            Dictionary with processing statistics
        """
        return self.stats.copy()
