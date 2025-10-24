"""
Folder Mover - Move files between folders based on CSV instructions.

This module provides functionality to move files from source folders to target folders
based on CSV instructions with proper error handling and logging.
"""

import csv
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Import COMMON framework modules
import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "COMMON", "src")
)

try:
    from common.logging import ScriptLogging
except ImportError:
    ScriptLogging = None


class FolderMover:
    """Move files between folders based on CSV instructions."""

    def __init__(
        self,
        input_csv: str,
        overwrite: bool = False,
        dry_run: bool = False,
        verbose: bool = False,
        logger=None,
    ):
        """
        Initialize the FolderMover.

        Args:
            input_csv: Path to CSV file with folder move instructions
            overwrite: Allow overwriting existing files and create full target paths
            dry_run: Show what would be done without making changes
            verbose: Enable verbose logging
            logger: Logger instance to use for logging
        """
        self.input_csv = Path(input_csv)
        self.overwrite = overwrite
        self.dry_run = dry_run
        self.verbose = verbose
        self.logger = logger

        # Statistics
        self.stats = {
            "rows_processed": 0,
            "folders_moved": 0,
            "files_moved": 0,
            "errors": 0,
            "skipped": 0,
        }

    def validate_csv_file(self) -> bool:
        """
        Validate that the CSV file exists and has required columns.

        Returns:
            True if CSV file is valid, False otherwise
        """
        if not self.input_csv.exists():
            if self.logger:
                self.logger.error(f"CSV file does not exist: {self.input_csv}")
            return False

        try:
            with open(self.input_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames

                required_columns = ["Folder", "Target Folder"]
                missing_columns = [
                    col for col in required_columns if col not in headers
                ]

                if missing_columns:
                    if self.logger:
                        self.logger.error(
                            f"Missing required columns: {missing_columns}"
                        )
                    return False

                if self.logger:
                    self.logger.debug(
                        f"CSV file validated successfully with columns: {headers}"
                    )

                return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error reading CSV file: {e}")
            return False

    def read_move_instructions(self) -> List[Dict[str, str]]:
        """
        Read move instructions from CSV file.

        Returns:
            List of dictionaries containing move instructions
        """
        instructions = []

        try:
            with open(self.input_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row_num, row in enumerate(reader, start=2):  # Start at 2 for header
                    self.stats["rows_processed"] += 1

                    # Skip rows without target folder
                    if not row.get("Target Folder", "").strip():
                        if self.verbose and self.logger:
                            self.logger.debug(
                                f"Row {row_num}: No target folder specified, skipping"
                            )
                        self.stats["skipped"] += 1
                        continue

                    # Clean up the data
                    instruction = {
                        "row_num": row_num,
                        "source_folder": row.get("Folder", "").strip(),
                        "target_folder": row.get("Target Folder", "").strip(),
                        "new_folder": row.get("New Folder", "").strip(),
                    }

                    # Validate source folder exists
                    if not instruction["source_folder"]:
                        if self.logger:
                            self.logger.warning(
                                f"Row {row_num}: No source folder specified"
                            )
                        self.stats["errors"] += 1
                        continue

                    source_path = Path(instruction["source_folder"])
                    if not source_path.exists():
                        if self.logger:
                            self.logger.warning(
                                f"Row {row_num}: Source folder does not exist: {source_path}"
                            )
                        self.stats["errors"] += 1
                        continue

                    if not source_path.is_dir():
                        if self.logger:
                            self.logger.warning(
                                f"Row {row_num}: Source path is not a directory: {source_path}"
                            )
                        self.stats["errors"] += 1
                        continue

                    instructions.append(instruction)

        except Exception as e:
            if self.logger:
                self.logger.error(f"Error reading CSV instructions: {e}")
            raise

        return instructions

    def validate_target_path(self, target_path: Path, row_num: int) -> bool:
        """
        Validate target path according to overwrite settings.

        Args:
            target_path: Target directory path
            row_num: CSV row number for error reporting

        Returns:
            True if target path is valid, False otherwise
        """
        if target_path.exists():
            if not target_path.is_dir():
                if self.logger:
                    self.logger.error(
                        f"Row {row_num}: Target path exists but is not a directory: {target_path}"
                    )
                return False
            return True

        # Check if parent exists
        parent_path = target_path.parent
        if not parent_path.exists():
            if self.overwrite:
                # With overwrite, we can create the full path
                return True
            else:
                # Without overwrite, parent must exist
                if self.logger:
                    self.logger.error(
                        f"Row {row_num}: Parent directory does not exist and --overwrite not specified: {parent_path}"
                    )
                return False

        return True

    def move_folder_contents(
        self, source_path: Path, target_path: Path, row_num: int
    ) -> Tuple[int, int]:
        """
        Move all files from source folder to target folder.

        Args:
            source_path: Source directory path
            target_path: Target directory path
            row_num: CSV row number for error reporting

        Returns:
            Tuple of (files_moved, errors)
        """
        files_moved = 0
        errors = 0

        try:
            # Create target directory if needed
            if not self.dry_run:
                # Check if directory exists before creating
                dir_existed = target_path.exists()
                target_path.mkdir(parents=self.overwrite, exist_ok=True)
                if self.logger:
                    if dir_existed:
                        self.logger.debug(
                            f"Row {row_num}: Using existing target directory: {target_path}"
                        )
                    else:
                        self.logger.debug(
                            f"Row {row_num}: Created target directory: {target_path}"
                        )
            else:
                # In dry-run mode, validate what would happen and log details
                if target_path.exists():
                    if self.logger:
                        self.logger.debug(
                            f"Row {row_num}: Target directory already exists: {target_path}"
                        )
                else:
                    # Check if we can create the target directory
                    parent_path = target_path.parent
                    if not parent_path.exists():
                        if self.overwrite:
                            if self.logger:
                                self.logger.debug(
                                    f"Row {row_num}: Would create target directory (with parents): {target_path}"
                                )
                        else:
                            if self.logger:
                                self.logger.error(
                                    f"Row {row_num}: Cannot create target directory - parent does not exist and --overwrite not specified: {parent_path}"
                                )
                            errors += 1
                            return 0, errors
                    else:
                        if self.logger:
                            self.logger.debug(
                                f"Row {row_num}: Would create target directory: {target_path}"
                            )

            # Get all files in source directory
            all_files = list(source_path.rglob("*"))
            file_items = [f for f in all_files if f.is_file()]

            if not file_items:
                if self.logger:
                    self.logger.debug(
                        f"Row {row_num}: No files found in source directory: {source_path}"
                    )
                return 0, 0

            if self.logger:
                self.logger.debug(
                    f"Row {row_num}: Moving {len(file_items)} files from {source_path} to {target_path}"
                )

            for file_path in file_items:
                try:
                    # Calculate relative path to preserve directory structure
                    rel_path = file_path.relative_to(source_path)
                    target_file = target_path / rel_path

                    # Create subdirectories if needed
                    target_file.parent.mkdir(parents=True, exist_ok=True)

                    # Check for existing file
                    if target_file.exists() and not self.overwrite:
                        if self.logger:
                            self.logger.error(
                                f"Row {row_num}: Target file exists and --overwrite not specified: {target_file}"
                            )
                        errors += 1
                        continue

                    if self.dry_run:
                        if self.logger:
                            self.logger.debug(
                                f"Row {row_num}: Would move {file_path} -> {target_file}"
                            )
                    else:
                        shutil.move(str(file_path), str(target_file))
                        if self.logger:
                            self.logger.debug(
                                f"Row {row_num}: Moved {file_path} -> {target_file}"
                            )

                    files_moved += 1

                except Exception as e:
                    if self.logger:
                        self.logger.error(
                            f"Row {row_num}: Error moving file {file_path}: {e}"
                        )
                    errors += 1

            # Remove empty source directory if all files were moved successfully
            if not self.dry_run and files_moved > 0 and errors == 0:
                try:
                    # Only remove if directory is empty
                    if not any(source_path.iterdir()):
                        source_path.rmdir()
                        if self.logger:
                            self.logger.debug(
                                f"Row {row_num}: Removed empty source directory: {source_path}"
                            )
                except Exception as e:
                    if self.logger:
                        self.logger.warning(
                            f"Row {row_num}: Could not remove source directory {source_path}: {e}"
                        )

            # Log summary of this operation
            if self.logger and files_moved > 0:
                if self.dry_run:
                    self.logger.debug(
                        f"Row {row_num}: COMPLETED - Would move {files_moved} files from {source_path.name} to {target_path.name} ({errors} errors)"
                    )
                else:
                    self.logger.debug(
                        f"Row {row_num}: COMPLETED - Moved {files_moved} files from {source_path.name} to {target_path.name} ({errors} errors)"
                    )
            elif self.logger:
                self.logger.debug(
                    f"Row {row_num}: SKIPPED - No files to move from {source_path.name}"
                )

        except Exception as e:
            if self.logger:
                self.logger.error(f"Row {row_num}: Error moving folder contents: {e}")
            errors += 1

        return files_moved, errors

    def process_moves(self) -> Dict[str, int]:
        """
        Process all move instructions from the CSV file.

        Returns:
            Statistics dictionary
        """
        if self.logger:
            self.logger.debug(f"Starting folder move processing from: {self.input_csv}")
            self.logger.debug(f"Overwrite mode: {self.overwrite}")
            self.logger.debug(f"Dry run mode: {self.dry_run}")

        # Validate CSV file
        if not self.validate_csv_file():
            raise ValueError("CSV file validation failed")

        # Read move instructions
        instructions = self.read_move_instructions()

        if not instructions:
            if self.logger:
                self.logger.warning("No valid move instructions found in CSV file")
            return self.stats

        if self.logger:
            self.logger.info(f"Processing {len(instructions)} folder move operations")

        # Progress tracking
        total_instructions = len(instructions)
        processed = 0

        # Process each instruction
        for instruction in instructions:
            row_num = instruction["row_num"]
            source_path = Path(instruction["source_folder"])
            target_path = Path(instruction["target_folder"])

            if self.logger:
                self.logger.debug(
                    f"Row {row_num}: PROCESSING - {source_path} -> {target_path}"
                )

            # Validate target path
            if not self.validate_target_path(target_path, row_num):
                self.stats["errors"] += 1
                if self.logger:
                    self.logger.info(
                        f"Row {row_num}: FAILED - Target path validation failed"
                    )
                continue

            # Move folder contents
            files_moved, errors = self.move_folder_contents(
                source_path, target_path, row_num
            )

            if files_moved > 0:
                self.stats["folders_moved"] += 1
                self.stats["files_moved"] += files_moved

            if errors > 0:
                self.stats["errors"] += errors

            # Progress indicator (only show every 10% or for small batches)
            processed += 1
            if total_instructions >= 10:
                if (
                    processed % max(1, total_instructions // 10) == 0
                    or processed == total_instructions
                ):
                    progress_pct = (processed / total_instructions) * 100
                    if self.logger:
                        self.logger.info(
                            f"Progress: {processed}/{total_instructions} operations ({progress_pct:.0f}%)"
                        )

        if self.logger:
            self.logger.info("Folder move processing completed")
            self.logger.debug(f"Final statistics: {self.stats}")

        return self.stats

    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics."""
        return self.stats.copy()
