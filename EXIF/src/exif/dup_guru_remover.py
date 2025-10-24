#!/usr/bin/env python3
"""
DupGuru File Remover

Business logic class for processing dupGuru CSV files and moving files
marked for deletion to a backup directory, preserving folder structure.
"""

import csv
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


class DupGuruRemover:
    """Remove duplicate files based on dupGuru CSV decisions."""

    def __init__(
        self,
        csv_file: str,
        target_path: str,
        dup_path: str,
        dry_run: bool = False,
        verbose: bool = False,
        logger=None,
    ):
        """
        Initialize the duplicate file remover.

        Args:
            csv_file: Path to dupGuru CSV file with Action column
            target_path: Root directory where files to be removed are located
            dup_path: Directory where removed files will be moved to
            dry_run: If True, only simulate actions without moving files
            verbose: Enable verbose logging
            logger: Logger instance to use (optional)
        """
        self.csv_file = Path(csv_file)
        self.target_path = Path(target_path)
        self.dup_path = Path(dup_path)
        self.dry_run = dry_run
        self.verbose = verbose
        self.logger = logger

        # Statistics tracking
        self.stats = {
            "total_rows": 0,
            "delete_actions": 0,
            "files_moved": 0,
            "files_not_found": 0,
            "errors": 0,
            "warnings": 0,
            "skipped_rows": 0,
        }

        # Validate inputs
        self._validate_inputs()

    def _log_file_only(self, message: str, level: str = "INFO"):
        """
        Log a message only to the log file, not to console output.

        This is useful for detailed file operations that should be auditable
        but don't need to clutter the console output.

        Args:
            message: Message to log
            level: Log level (INFO, WARNING, ERROR, DEBUG)
        """
        if self.logger:
            # Get the file handler(s) only
            file_handlers = [
                h for h in self.logger.handlers if isinstance(h, logging.FileHandler)
            ]

            if file_handlers:
                # Temporarily disable console handlers
                console_handlers = [
                    h
                    for h in self.logger.handlers
                    if not isinstance(h, logging.FileHandler)
                ]

                # Remove console handlers temporarily
                for handler in console_handlers:
                    self.logger.removeHandler(handler)

                # Log the message
                log_method = getattr(self.logger, level.lower(), self.logger.info)
                log_method(message)

                # Restore console handlers
                for handler in console_handlers:
                    self.logger.addHandler(handler)
            else:
                # Fallback to regular logging if no file handler found
                log_method = getattr(self.logger, level.lower(), self.logger.info)
                log_method(message)

    def _log_warning_file_only(self, message: str):
        """
        Log a warning only to the log file and increment warning counter.

        Args:
            message: Warning message to log
        """
        self.stats["warnings"] += 1
        self._log_file_only(message, "WARNING")

    def _log_error_file_only(self, message: str):
        """
        Log an error only to the log file and increment error counter.

        Args:
            message: Error message to log
        """
        self.stats["errors"] += 1
        self._log_file_only(message, "ERROR")

    def _validate_inputs(self):
        """Validate input parameters."""
        if not self.csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_file}")

        if not self.target_path.exists():
            raise FileNotFoundError(f"Target directory not found: {self.target_path}")

        if not self.target_path.is_dir():
            raise NotADirectoryError(
                f"Target path is not a directory: {self.target_path}"
            )

        # Create dup_path if it doesn't exist
        if not self.dry_run:
            self.dup_path.mkdir(parents=True, exist_ok=True)
            if self.logger:
                self.logger.info(f"Duplicate storage directory: {self.dup_path}")
        else:
            if self.logger:
                self.logger.info(
                    f"DRY RUN: Would create duplicate storage directory: {self.dup_path}"
                )

    def _normalize_path(self, folder_path: str) -> Path:
        """
        Normalize a folder path from the CSV to work with local filesystem.

        Handles Windows-style paths by removing the drive letter and making them
        relative to the target directory.

        Args:
            folder_path: Folder path from CSV (may be Windows-style)

        Returns:
            Normalized path relative to target directory
        """
        # Convert Windows path separators
        normalized = folder_path.replace("\\", "/")

        # Handle Windows drive paths by removing drive letter
        if ":" in normalized and len(normalized.split(":")[0]) <= 2:
            # Remove drive letter (e.g., "X:/santee-images/..." -> "santee-images/...")
            path_without_drive = normalized.split(":", 1)[1].lstrip("/")

            # The CSV path structure should match the target directory structure
            # For example, if CSV has "X:/santee-images/2020+/..." and target is "/path/to/santee-images"
            # then we need "2020+/..." relative to the target

            # Try to find where the CSV path intersects with the target path
            target_name = self.target_path.name  # e.g., "santee-images"
            path_parts = Path(path_without_drive).parts

            # Find the target directory name in the CSV path
            if target_name in path_parts:
                # Get everything after the target directory name
                target_index = path_parts.index(target_name)
                relative_parts = path_parts[target_index + 1 :]
                relative_path = Path(*relative_parts) if relative_parts else Path(".")
                if self.logger:
                    self.logger.debug(
                        f"Normalized '{folder_path}' -> '{relative_path}' "
                        f"(found target '{target_name}' in path)"
                    )
                return relative_path
            else:
                # Target name not found in path, use the whole path without drive
                if self.logger:
                    self.logger.debug(
                        f"Normalized '{folder_path}' -> '{path_without_drive}' "
                        f"(target name not in path)"
                    )
                return Path(path_without_drive)
        else:
            # Remove leading slashes for any other format
            normalized = normalized.lstrip("/")

        return Path(normalized)

    def _detect_common_base_path(self) -> str:
        """Detect the common base directory from CSV file paths."""
        try:
            with open(self.csv_file, "r", encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file)
                paths = []

                # Collect first 50 paths to analyze
                for i, row in enumerate(reader):
                    if i >= 50:  # Limit analysis to first 50 rows for performance
                        break
                    if row.get("Action", "").strip().lower() == "delete":
                        # Use Folder column which contains the directory path
                        folder_path = row.get("Folder", "").strip()
                        if folder_path:
                            # Convert Windows path format and extract base
                            normalized = folder_path.replace("\\", "/")
                            if ":" in normalized:
                                path_part = normalized.split(":", 1)[1].lstrip("/")
                                # Get first directory component (like 'santee-images')
                                if "/" in path_part:
                                    base_dir = path_part.split("/")[0]
                                    paths.append(base_dir)

                if not paths:
                    return None

                # Find most common base directory
                from collections import Counter

                counter = Counter(paths)
                most_common = counter.most_common(1)
                return most_common[0][0] if most_common else None

        except Exception as e:
            if self.verbose:
                self._log_warning_file_only(f"Could not detect common base path: {e}")
            return None

    def _find_file_in_target(self, folder_path: str, filename: str) -> Optional[Path]:
        """
        Find a file in the target directory structure.

        Args:
            folder_path: Folder path from CSV
            filename: Filename from CSV

        Returns:
            Full path to file if found, None otherwise
        """
        # Normalize the folder path
        rel_folder = self._normalize_path(folder_path)

        # Construct full path
        full_path = self.target_path / rel_folder / filename

        if full_path.exists():
            return full_path

        # Try alternative path normalization if not found
        # Sometimes paths may have different structures
        potential_paths = [
            self.target_path / filename,  # File might be directly in target
            self.target_path / rel_folder.name / filename,  # Only last folder
        ]

        for path in potential_paths:
            if path.exists():
                if self.logger:
                    self.logger.debug(f"Found file at alternative path: {path}")
                return path

        return None

    def _calculate_dup_path(self, original_path: Path) -> Path:
        """
        Calculate the destination path in the duplicate directory.

        Preserves the relative structure from the target directory.

        Args:
            original_path: Original file path

        Returns:
            Destination path in duplicate directory
        """
        try:
            # Get relative path from target directory
            rel_path = original_path.relative_to(self.target_path)
            return self.dup_path / rel_path
        except ValueError:
            # File is not under target directory, use filename only
            return self.dup_path / original_path.name

    def _move_file(self, source_path: Path, dest_path: Path) -> bool:
        """
        Move a file from source to destination, creating directories as needed.

        Args:
            source_path: Source file path
            dest_path: Destination file path

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.dry_run:
                self._log_file_only(f"DRY RUN: Would move {source_path} -> {dest_path}")
                return True

            # Create destination directory
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Handle existing files
            if dest_path.exists():
                # Add timestamp to avoid conflicts
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stem = dest_path.stem
                suffix = dest_path.suffix
                dest_path = dest_path.parent / f"{stem}_{timestamp}{suffix}"
                self._log_warning_file_only(f"Destination exists, using: {dest_path}")

            # Move the file
            shutil.move(str(source_path), str(dest_path))
            self._log_file_only(f"Moved: {source_path} -> {dest_path}")
            return True

        except Exception as e:
            self._log_error_file_only(f"Failed to move {source_path}: {e}")
            return False

    def process_csv(self):
        """Process the CSV file and move files marked for deletion."""
        if self.logger:
            self.logger.info(f"Processing CSV file: {self.csv_file}")

        try:
            with open(self.csv_file, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                # Validate required columns
                required_columns = ["Filename", "Folder", "Action"]
                missing_columns = [
                    col for col in required_columns if col not in reader.fieldnames
                ]
                if missing_columns:
                    raise ValueError(f"Missing required columns: {missing_columns}")

                for row_num, row in enumerate(reader, 1):
                    self.stats["total_rows"] += 1

                    # Skip rows without filename or folder
                    if not row.get("Filename") or not row.get("Folder"):
                        self.stats["skipped_rows"] += 1
                        if self.logger:
                            self.logger.debug(
                                f"Row {row_num}: Skipping row with missing filename/folder"
                            )
                        continue

                    # Process rows marked for deletion
                    action = row.get("Action", "").strip()
                    if action.lower() == "delete":
                        self.stats["delete_actions"] += 1
                        success = self._process_delete_row(row, row_num)
                        if success:
                            self.stats["files_moved"] += 1

        except Exception as e:
            self._log_error_file_only(f"Error processing CSV: {e}")
            raise

    def _process_delete_row(self, row: dict, row_num: int) -> bool:
        """
        Process a single row marked for deletion.

        Args:
            row: CSV row data
            row_num: Row number for logging

        Returns:
            True if successful, False otherwise
        """
        filename = row["Filename"]
        folder_path = row["Folder"]

        if self.logger:
            self.logger.debug(f"Row {row_num}: Processing delete action for {filename}")

        # Find the file in target directory
        source_path = self._find_file_in_target(folder_path, filename)
        if not source_path:
            self.stats["files_not_found"] += 1
            self._log_warning_file_only(
                f"Row {row_num}: File not found: {folder_path}/{filename}"
            )
            return False

        # Calculate destination path
        dest_path = self._calculate_dup_path(source_path)

        # Move the file
        return self._move_file(source_path, dest_path)

    def print_statistics(self):
        """Print processing statistics."""
        print("\nDupGuru Removal Results:")
        print(f"  Total rows processed: {self.stats['total_rows']}")
        print(f"  Delete actions found: {self.stats['delete_actions']}")
        print(f"  Files moved: {self.stats['files_moved']}")
        print(f"  Files not found: {self.stats['files_not_found']}")
        print(f"  Warnings: {self.stats['warnings']}")
        print(f"  Errors: {self.stats['errors']}")
        print(f"  Rows skipped: {self.stats['skipped_rows']}")

        if self.dry_run:
            print("\n  *** DRY RUN - No files were actually moved ***")
