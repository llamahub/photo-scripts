"""
Photo Organization Module - Organize photos by date using EXIF metadata

Contains the PhotoOrganizer class for organizing photos from a source directory
into a target directory with structured subdirectories based on photo dates.

Target directory structure:
  Default: <decade>/<year>/<year>-<month>/<parent folder>/<filename>
  Month-only: <year>-<month>/<filename>
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

# Import COMMON modules with fallback
try:
    import sys
    from pathlib import Path

    common_src_path = Path(__file__).parent.parent.parent.parent / "COMMON" / "src"
    sys.path.insert(0, str(common_src_path))
    from common.logging import ScriptLogging
    from common.file_manager import FileManager
except ImportError:
    # Fallback for when COMMON modules are not available
    ScriptLogging = None
    FileManager = None


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
        ".mpg",
        ".mpeg",
        ".mts",
        ".m2ts",
        ".ts",
    }

    # Supported sidecar file extensions
    SIDECAR_EXTENSIONS = {
        ".xmp",  # Adobe XMP sidecar files
        ".yml",  # YAML metadata files
        ".yaml",  # YAML metadata files (alternative extension)
    }

    @classmethod
    def get_image_extensions(cls):
        """Get set of supported image file extensions."""
        if FileManager:
            return FileManager.get_image_extensions()
        return cls.IMAGE_EXTENSIONS.copy()

    @classmethod
    def get_video_extensions(cls):
        """Get set of supported video file extensions."""
        if FileManager:
            return FileManager.get_video_extensions()
        return cls.VIDEO_EXTENSIONS.copy()

    def __init__(
        self,
        source: Path,
        target: Path,
        dry_run: bool = False,
        debug: bool = False,
        move_files: bool = False,
        max_workers: int = None,
        video_mode: bool = False,
        month_only_mode: bool = False,
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
            month_only_mode: If True, use simplified YYYY-MM structure without decades/parent folders
        """
        self.source = Path(source).resolve()
        self.target = Path(target).resolve()
        self.dry_run = dry_run
        self.debug = debug
        self.move_files = move_files
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.video_mode = video_mode
        self.month_only_mode = month_only_mode

        # Setup logging
        self._setup_logging()

        # Statistics tracking
        action = "moved" if move_files else "copied"
        self.stats = {"processed": 0, action: 0, "skipped": 0, "errors": 0}

        # Set file type for logging
        self.file_type = "video" if video_mode else "image"

        # Message collapsing for console output (track counts of repetitive messages)
        self.message_counts = {
            "sidecar_already_exists": 0,
            "sidecar_file_missing": 0,
            "target_file_exists": 0,
            "other_errors": 0,
        }

    def _setup_logging(self):
        """Setup logging with DEBUG in files, INFO on console."""
        if ScriptLogging:
            # Use custom setup with different levels for console vs file
            self.logger = self._setup_script_logger_custom()
        else:
            # Fallback logging setup
            import logging

            logging.basicConfig(
                level=logging.DEBUG if self.debug else logging.INFO,
                format="%(asctime)s - %(levelname)s - %(message)s",
            )
            self.logger = logging.getLogger(__name__)

    def _create_filtered_console_handler(self):
        """Create a console handler that filters repetitive warning messages."""
        import logging

        class FilteredConsoleHandler(logging.StreamHandler):
            def __init__(self, photo_organizer):
                super().__init__()
                self.photo_organizer = photo_organizer
                self.shown_message_types = set()

            def emit(self, record):
                # Check if this is a repetitive message type that should be filtered
                if record.levelname == "WARNING":
                    if "Target file already exists, skipping:" in record.getMessage():
                        if (
                            "target_file_exists_warning_shown"
                            not in self.shown_message_types
                        ):
                            # Show first occurrence with note about collapsing
                            original_msg = record.getMessage()
                            record.msg = f"{original_msg} (further duplicates will be summarized at end)"
                            self.shown_message_types.add(
                                "target_file_exists_warning_shown"
                            )
                            super().emit(record)
                        return
                    elif (
                        "Target sidecar file already exists, skipping:"
                        in record.getMessage()
                    ):
                        if (
                            "sidecar_exists_warning_shown"
                            not in self.shown_message_types
                        ):
                            original_msg = record.getMessage()
                            record.msg = f"{original_msg} (further duplicates will be summarized at end)"
                            self.shown_message_types.add("sidecar_exists_warning_shown")
                            super().emit(record)
                        return
                    elif (
                        "Sidecar file already moved or missing:" in record.getMessage()
                    ):
                        if (
                            "sidecar_missing_warning_shown"
                            not in self.shown_message_types
                        ):
                            original_msg = record.getMessage()
                            record.msg = f"{original_msg} (further duplicates will be summarized at end)"
                            self.shown_message_types.add(
                                "sidecar_missing_warning_shown"
                            )
                            super().emit(record)
                        return

                # Show all other messages normally
                super().emit(record)

        return FilteredConsoleHandler(self)

    def _setup_script_logger_custom(self):
        """Custom logger setup with DEBUG in files, INFO on console."""
        import logging
        import inspect
        from datetime import datetime

        # Auto-generate name from calling script
        frame = inspect.currentframe()
        try:
            # Go up the call stack to find the calling script
            caller_frame = frame.f_back.f_back  # Go back 2 levels to get to the script
            while caller_frame:
                filename = caller_frame.f_code.co_filename
                if filename != __file__ and not filename.endswith("common_tasks.py"):
                    # Found the calling script
                    script_name = Path(filename).stem
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    name = f"{script_name}_{timestamp}"
                    break
                caller_frame = caller_frame.f_back

            # Fallback if we couldn't determine the script name
            if "name" not in locals():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name = f"photo_organizer_{timestamp}"
        finally:
            del frame  # Prevent reference cycles

        # Create log directory
        log_dir = Path(".log")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"{name}.log"

        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)  # Always DEBUG for the logger itself

        # Clear any existing handlers to avoid duplicates
        logger.handlers.clear()

        # Create formatters
        console_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Console handler - INFO level (unless debug flag is set) with message filtering
        console_handler = self._create_filtered_console_handler()
        console_handler.setLevel(logging.DEBUG if self.debug else logging.INFO)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler - always DEBUG level
        file_handler = logging.FileHandler(log_file, mode="a")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Add header with log file info
        logger.info("=" * 80)
        logger.info(f"LOG FILE: {log_file}")
        logger.info(f"SCRIPT: {name}")
        logger.info(f"DEBUG MODE: {self.debug}")
        logger.info("=" * 80)

        logger.info(f"Script logging initialized for {name} (debug: {self.debug})")
        return logger

    def is_image_file(self, file_path: Path) -> bool:
        """Check if file is a supported image format."""
        if FileManager:
            return FileManager.is_image_file(file_path)
        return file_path.suffix.lower() in self.IMAGE_EXTENSIONS

    def is_video_file(self, file_path: Path) -> bool:
        """Check if file is a supported video format."""
        if FileManager:
            return FileManager.is_video_file(file_path)
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

        Format: <decade>/<year>/<year>-<month>/[<parent folder>/]<filename> or <year>-<month>/<filename>
        - Full hierarchy (default): <decade>/<year>/<year>-<month>/<parent folder>/<filename>
        - Month only (--month-only): <year>-<month>/<filename>

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

        # Build target path structure
        year_month = f"{year}-{month_str}"

        if self.month_only_mode:
            # Simplified structure: just YYYY-MM folder
            target_path = self.target / year_month / source_file.name
        else:
            # Full hierarchy (default behavior)
            decade = self.get_decade_folder(year_int)
            parent_folder = source_file.parent.name
            target_path = (
                self.target
                / decade
                / year
                / year_month
                / parent_folder
                / source_file.name
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
                            self.logger.debug(
                                f"Found {len(files)} {self.file_type} files so far..."
                            )

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
                    self.message_counts["target_file_exists"] += 1
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

            # Handle all sidecar files if they exist (works in both dry-run and real modes)
            self._handle_all_sidecars(source_file, target_file)

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

    def _handle_all_sidecars(self, source_file: Path, target_file: Path) -> None:
        """
        Handle all sidecar files that exist alongside the image or video file.

        This includes:
        - XMP files (.xmp)
        - YAML metadata files (.yml, .yaml)
        - Google Takeout JSON files (.json, .supplemental-metadata.json)

        Args:
            source_file: Original image/video file path
            target_file: Target image/video file path
        """
        source_dir = source_file.parent
        source_stem = source_file.stem
        target_dir = target_file.parent
        target_stem = target_file.stem

        # Track sidecars found and processed
        sidecars_found = []

        # 1. Standard sidecar extensions with same base name
        for ext in self.SIDECAR_EXTENSIONS:
            if self.video_mode:
                # Videos: sidecar keeps the full video filename + extension
                # e.g., video.mp4 -> video.mp4.xmp
                source_sidecar = source_file.with_suffix(source_file.suffix + ext)
                target_sidecar = target_file.with_suffix(target_file.suffix + ext)
            else:
                # Images: sidecar replaces image extension
                # e.g., image.jpg -> image.xmp
                source_sidecar = source_file.with_suffix(ext)
                target_sidecar = target_file.with_suffix(ext)

            if source_sidecar.exists():
                sidecars_found.append((source_sidecar, target_sidecar))

        # 2. Google Takeout style JSON files
        # Look for .json files that contain the source filename in their name
        try:
            for json_file in source_dir.glob("*.json"):
                if source_stem in json_file.stem or json_file.name.endswith(
                    ".supplemental-metadata.json"
                ):
                    # Create corresponding target JSON path
                    if source_stem in json_file.stem:
                        # Replace source stem with target stem in the sidecar name
                        new_name = json_file.name.replace(source_stem, target_stem)
                        target_sidecar = target_dir / new_name
                    else:
                        # For .supplemental-metadata.json, keep the same name pattern
                        target_sidecar = target_dir / json_file.name

                    sidecars_found.append((json_file, target_sidecar))
        except PermissionError:
            self.logger.debug(f"Permission denied accessing directory: {source_dir}")

        # Process all found sidecars
        for source_sidecar, target_sidecar in sidecars_found:
            self._process_single_sidecar(source_sidecar, target_sidecar)

    def _process_single_sidecar(
        self, source_sidecar: Path, target_sidecar: Path
    ) -> None:
        """
        Process a single sidecar file (move or copy).

        Args:
            source_sidecar: Source sidecar file path
            target_sidecar: Target sidecar file path
        """
        try:
            if not self.dry_run:
                # Check if target sidecar already exists
                if target_sidecar.exists():
                    self.message_counts["sidecar_already_exists"] += 1
                    self.logger.warning(
                        f"Target sidecar file already exists, skipping: {target_sidecar}"
                    )
                    return

                # Move or copy the sidecar file
                if self.move_files:
                    shutil.move(str(source_sidecar), str(target_sidecar))
                    action = "Moved"
                    stat_key = "sidecars_moved"
                else:
                    shutil.copy2(source_sidecar, target_sidecar)
                    action = "Copied"
                    stat_key = "sidecars_copied"

                # Update statistics
                if stat_key not in self.stats:
                    self.stats[stat_key] = 0
                self.stats[stat_key] += 1

                file_type = "video" if self.video_mode else "image"
                sidecar_type = source_sidecar.suffix.upper().lstrip(".")
                self.logger.debug(
                    f"{action} {file_type} {sidecar_type} sidecar: {source_sidecar} -> {target_sidecar}"
                )
            else:
                # Dry run
                operation = "move" if self.move_files else "copy"
                file_type = "video" if self.video_mode else "image"
                sidecar_type = source_sidecar.suffix.upper().lstrip(".")
                self.logger.debug(
                    f"Would {operation} {file_type} {sidecar_type} sidecar: "
                    f"{source_sidecar} -> {target_sidecar}"
                )

                # Update dry-run statistics
                stat_key = "sidecars_moved" if self.move_files else "sidecars_copied"
                if stat_key not in self.stats:
                    self.stats[stat_key] = 0
                self.stats[stat_key] += 1

        except FileNotFoundError:
            # Sidecar file was already moved by another media file - this is expected
            self.message_counts["sidecar_file_missing"] += 1
            sidecar_type = source_sidecar.suffix.upper().lstrip(".")
            self.logger.warning(
                f"Sidecar file already moved or missing: {source_sidecar} "
                f"(likely moved by duplicate media file)"
            )
        except Exception as e:
            operation = "moving" if self.move_files else "copying"
            sidecar_type = source_sidecar.suffix.upper().lstrip(".")
            self.message_counts["other_errors"] += 1
            self.logger.error(
                f"Error {operation} {sidecar_type} sidecar {source_sidecar} to {target_sidecar}: {e}"
            )
            self.stats["errors"] += 1

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
                    self.logger.info(
                        f"Progress: {i}/{len(files)} {self.file_type} files processed"
                    )
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

        # Include sidecar statistics (new unified approach)
        sidecar_action_count = self.stats.get("sidecars_moved", 0) + self.stats.get(
            "sidecars_copied", 0
        )

        summary = [
            "=" * 80,
            " ORGANIZATION COMPLETE",
            "=" * 80,
            f"Total files processed: {self.stats['processed']}",
            f"Files {operation}: {action_count}",
            f"Sidecar files {operation}: {sidecar_action_count}",
            f"Files skipped: {self.stats['skipped']}",
            f"Errors encountered: {self.stats['errors']}",
        ]

        # Add collapsed message summary
        if any(self.message_counts.values()):
            summary.append("")
            summary.append("Message Summary:")
            if self.message_counts["target_file_exists"] > 0:
                count = self.message_counts["target_file_exists"]
                summary.append(f"  Target files already existed: {count} (skipped)")
            if self.message_counts["sidecar_already_exists"] > 0:
                count = self.message_counts["sidecar_already_exists"]
                summary.append(f"  Sidecar files already existed: {count} (skipped)")
            if self.message_counts["sidecar_file_missing"] > 0:
                count = self.message_counts["sidecar_file_missing"]
                summary.append(
                    f"  Sidecar files already moved: {count} (expected for duplicates)"
                )
            if self.message_counts["other_errors"] > 0:
                count = self.message_counts["other_errors"]
                summary.append(f"  Other sidecar errors: {count} (see log for details)")
            summary.append("  (Full details in log file)")

        if self.dry_run:
            operation_verb = "moved" if self.move_files else "copied"
            summary.append("")
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
