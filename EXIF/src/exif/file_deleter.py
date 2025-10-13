"""
File deleter for duplicate removal operations.

This module provides the FileDeleter class for safely deleting files based on CSV input
with configurable filtering criteria.
"""

import os
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional


class FileDeleter:
    """Handles file deletion operations based on CSV input with status filtering."""

    def __init__(self, logger=None):
        """Initialize the FileDeleter.

        Args:
            logger: Logger instance for output (optional)
        """
        self.logger = logger
        self.stats = {
            "total_rows": 0,
            "matching_rows": 0,
            "files_deleted": 0,
            "files_not_found": 0,
            "errors": 0,
        }

    def delete_files_from_csv(
        self,
        csv_path: str,
        status_col: str = "match_type",
        status_val: str = "Exact match",
        file_col: str = "source_file_path",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Delete files listed in CSV based on status criteria.

        Args:
            csv_path: Path to the input CSV file
            status_col: Column name containing the status values
            file_col: Column name containing the file paths
            status_val: Status value that indicates files should be deleted
            dry_run: If True, only log what would be deleted without actually deleting

        Returns:
            Dictionary with deletion statistics
        """
        if self.logger:
            self.logger.info(f"Processing CSV file: {csv_path}")
            self.logger.info(f"Status column: {status_col}")
            self.logger.info(f"Target status value: {status_val}")
            self.logger.info(f"File path column: {file_col}")
            self.logger.info(f"Dry run mode: {dry_run}")

        # Reset statistics
        self.stats = {
            "total_rows": 0,
            "matching_rows": 0,
            "files_deleted": 0,
            "files_not_found": 0,
            "errors": 0,
        }

        try:
            # Read and process CSV file
            with open(csv_path, "r", newline="", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)

                # Validate required columns exist
                if status_col not in reader.fieldnames:
                    raise ValueError(
                        f"Status column '{status_col}' not found in CSV. Available columns: {reader.fieldnames}"
                    )

                if file_col not in reader.fieldnames:
                    raise ValueError(
                        f"File path column '{file_col}' not found in CSV. Available columns: {reader.fieldnames}"
                    )

                if self.logger:
                    self.logger.info(f"CSV columns found: {reader.fieldnames}")

                # Process each row
                for row in reader:
                    self.stats["total_rows"] += 1

                    # Check if this row matches our deletion criteria
                    if row.get(status_col) == status_val:
                        self.stats["matching_rows"] += 1
                        file_path = row.get(file_col)

                        if not file_path:
                            if self.logger:
                                self.logger.warning(
                                    f"Empty file path in row {self.stats['total_rows']}"
                                )
                            self.stats["errors"] += 1
                            continue

                        # Attempt to delete the file
                        self._delete_file(file_path, dry_run)

        except FileNotFoundError:
            error_msg = f"CSV file not found: {csv_path}"
            if self.logger:
                self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        except Exception as e:
            error_msg = f"Error processing CSV file: {e}"
            if self.logger:
                self.logger.error(error_msg)
            self.stats["errors"] += 1
            raise

        # Log summary
        if self.logger:
            self.logger.info("File deletion summary:")
            self.logger.info(f"  Total rows processed: {self.stats['total_rows']}")
            self.logger.info(f"  Matching rows: {self.stats['matching_rows']}")
            if dry_run:
                self.logger.info(
                    f"  Files that would be deleted: {self.stats['files_deleted']}"
                )
            else:
                self.logger.info(
                    f"  Files successfully deleted: {self.stats['files_deleted']}"
                )
            self.logger.info(f"  Files not found: {self.stats['files_not_found']}")
            self.logger.info(f"  Errors: {self.stats['errors']}")

        return self.stats

    def _delete_file(self, file_path: str, dry_run: bool) -> None:
        """Delete a single file or log what would be deleted in dry run mode.

        Args:
            file_path: Path to the file to delete
            dry_run: If True, only log without actually deleting
        """
        try:
            # Convert to Path object for easier handling
            path = Path(file_path)

            # Check if file exists
            if not path.exists():
                if self.logger:
                    self.logger.warning(f"File not found: {file_path}")
                self.stats["files_not_found"] += 1
                return

            # Check if it's actually a file (not a directory)
            if not path.is_file():
                if self.logger:
                    self.logger.warning(f"Path is not a file: {file_path}")
                self.stats["errors"] += 1
                return

            if dry_run:
                if self.logger:
                    self.logger.info(f"[DRY RUN] Would delete: {file_path}")
                self.stats["files_deleted"] += 1
            else:
                # Actually delete the file
                path.unlink()
                if self.logger:
                    self.logger.info(f"Deleted: {file_path}")
                self.stats["files_deleted"] += 1

        except PermissionError:
            error_msg = f"Permission denied deleting file: {file_path}"
            if self.logger:
                self.logger.error(error_msg)
            self.stats["errors"] += 1
        except Exception as e:
            error_msg = f"Error deleting file {file_path}: {e}"
            if self.logger:
                self.logger.error(error_msg)
            self.stats["errors"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get current deletion statistics.

        Returns:
            Dictionary with current statistics
        """
        return self.stats.copy()
