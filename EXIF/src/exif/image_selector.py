#!/usr/bin/env python3
"""
Image Selector Module

Handles sampling and copying of image files with their sidecars. Creates a random sample
of image files from a source directory, copying them to a target directory while preserving
folder structure and including associated metadata files.
"""

import os
import shutil
import random
from pathlib import Path
from collections import defaultdict
from typing import List, Set, Dict

# Import COMMON logging
import sys

common_src_path = Path(__file__).parent.parent.parent.parent / "COMMON" / "src"
sys.path.insert(0, str(common_src_path))

try:
    from common.logging import ScriptLogging
except ImportError:
    # Fallback if COMMON module is not available
    import logging

    ScriptLogging = None


class ImageSelector:
    """Handles sampling and copying of image files with their sidecars."""

    # Supported image file extensions
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".heic"}

    # Sidecar file extensions
    SIDECAR_EXTENSIONS = {".xmp", ".yml", ".yaml"}

    def __init__(
        self,
        source: Path,
        target: Path,
        max_files: int = 10,
        max_folders: int = 3,
        max_depth: int = 2,
        max_per_folder: int = 2,
        clean_target: bool = False,
        debug: bool = False,
    ):
        """
        Initialize ImageSelector with configuration parameters.

        Args:
            source: Source directory to sample from
            target: Target directory to copy files to
            max_files: Maximum number of files to select (default: 10)
            max_folders: Maximum number of subfolders to sample from (default: 3)
            max_depth: Maximum depth of subfolders to explore (default: 2)
            max_per_folder: Maximum files per subfolder (default: 2)
            clean_target: Whether to clean target directory first (default: False)
            debug: Enable debug logging (default: False)
        """
        self.source = Path(source).resolve()
        self.target = Path(target).resolve()
        self.max_files = max_files
        self.max_folders = max_folders
        self.max_depth = max_depth
        self.max_per_folder = max_per_folder
        self.clean_target = clean_target
        self.debug = debug

        # Setup logging using COMMON ScriptLogging (auto-detects script name and uses .log dir)
        if ScriptLogging:
            self.logger = ScriptLogging.get_script_logger(debug=debug)
        else:
            # Fallback to basic logging if COMMON is not available
            self.logger = self._setup_logger_fallback(
                name="image_selector", debug=debug
            )

        # Track files per folder
        self.folder_counts: Dict[str, int] = defaultdict(int)

        # Statistics tracking
        self.stats = {
            "total_images_found": 0,
            "selected_files": 0,
            "copied_files": 0,
            "copied_sidecars": 0,
            "errors": 0,
            "folders_processed": 0,
        }

    def _setup_logger_fallback(self, name: str, debug: bool = False):
        """Fallback logger setup if COMMON ScriptLogging is not available."""
        import logging

        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG if debug else logging.INFO)

        # Simple console handler
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        logger.info(f"Fallback logging initialized for {name}")
        return logger

    def is_image_file(self, file_path: Path) -> bool:
        """
        Check if file is a supported image format.

        Args:
            file_path: Path to check

        Returns:
            True if file has supported image extension
        """
        return file_path.suffix.lower() in self.IMAGE_EXTENSIONS

    def find_images(self, directory: Path, max_depth: int) -> List[Path]:
        """
        Find all image files in directory up to max_depth.

        Args:
            directory: Directory to search
            max_depth: Maximum depth to recurse

        Returns:
            List of image file paths found
        """
        images = []
        try:
            for root, dirs, files in os.walk(directory):
                root_path = Path(root)
                # Calculate depth relative to the starting directory
                try:
                    relative_parts = root_path.relative_to(directory).parts
                    depth = len(relative_parts)
                except ValueError:
                    # If relative_to fails, skip this directory
                    continue

                if depth > max_depth:
                    continue

                for file in files:
                    file_path = root_path / file
                    if self.is_image_file(file_path):
                        images.append(file_path)
        except PermissionError as e:
            self.logger.warning(f"Permission denied accessing {directory}: {e}")

        self.stats["total_images_found"] += len(images)
        return images

    def get_subfolders(self, directory: Path, max_depth: int) -> List[Path]:
        """
        Get all subfolders up to max_depth.

        Args:
            directory: Directory to search for subfolders
            max_depth: Maximum depth to recurse

        Returns:
            List of subfolder paths
        """
        subfolders = []
        try:
            for root, dirs, _ in os.walk(directory):
                root_path = Path(root)
                depth = len(root_path.relative_to(directory).parts)
                if 0 < depth <= max_depth:
                    subfolders.append(root_path)
        except PermissionError as e:
            self.logger.warning(f"Permission denied accessing {directory}: {e}")

        return subfolders

    def select_files(self) -> List[Path]:
        """
        Select image files using the multi-stage sampling strategy.

        Returns:
            List of selected image file paths
        """
        selected_files = []
        seen_files: Set[Path] = set()

        # Stage 1: Sample from subfolders
        subfolders = self.get_subfolders(self.source, self.max_depth)
        random.shuffle(subfolders)
        selected_subfolders = subfolders[: self.max_folders]

        self.logger.debug(
            f"Found {len(subfolders)} subfolders, selected {len(selected_subfolders)}"
        )

        for folder in selected_subfolders:
            images_in_folder = self.find_images(folder, 1)  # Only direct children
            random.shuffle(images_in_folder)

            # Get relative path for tracking folder counts
            try:
                rel_folder = folder.relative_to(self.source)
                folder_key = str(rel_folder)
            except ValueError:
                folder_key = str(folder)

            for img in images_in_folder:
                if img in seen_files:
                    continue

                if (
                    self.folder_counts[folder_key] < self.max_per_folder
                    and len(selected_files) < self.max_files
                ):
                    selected_files.append(img)
                    seen_files.add(img)
                    self.folder_counts[folder_key] += 1

                if len(selected_files) >= self.max_files:
                    break

            if len(selected_files) >= self.max_files:
                break

        # Stage 2: Fill from root directory if needed
        if len(selected_files) < self.max_files:
            self.logger.debug("Filling from root directory")
            root_images = self.find_images(self.source, 1)  # Only direct children
            random.shuffle(root_images)

            for img in root_images:
                if img not in seen_files and len(selected_files) < self.max_files:
                    selected_files.append(img)
                    seen_files.add(img)

        # Stage 3: Fill from entire tree if still needed
        if len(selected_files) < self.max_files:
            self.logger.debug("Filling from entire tree")
            all_images = self.find_images(self.source, self.max_depth)
            random.shuffle(all_images)

            for img in all_images:
                if img not in seen_files and len(selected_files) < self.max_files:
                    selected_files.append(img)
                    seen_files.add(img)

        final_selection = selected_files[
            : self.max_files
        ]  # Ensure we don't exceed limit
        self.stats["selected_files"] = len(final_selection)
        return final_selection

    def find_sidecars(self, image_path: Path) -> List[Path]:
        """
        Find sidecar files associated with an image.

        Args:
            image_path: Path to the image file

        Returns:
            List of associated sidecar file paths
        """
        sidecars = []
        image_stem = image_path.stem
        image_dir = image_path.parent

        # Standard sidecars (same base name)
        for ext in self.SIDECAR_EXTENSIONS:
            sidecar = image_dir / f"{image_stem}{ext}"
            if sidecar.exists():
                sidecars.append(sidecar)

        # Google Takeout style JSON files (contains image base name)
        try:
            for json_file in image_dir.glob("*.json"):
                if image_stem in json_file.stem:
                    sidecars.append(json_file)
        except PermissionError:
            pass

        return sidecars

    def copy_file_with_metadata(self, source_file: Path) -> bool:
        """
        Copy an image file and its sidecars to the target directory.

        Args:
            source_file: Source image file path

        Returns:
            True if copy was successful, False otherwise
        """
        try:
            # Calculate relative path and create target directory structure
            rel_path = source_file.relative_to(self.source)
            target_file = self.target / rel_path
            target_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy the main file
            shutil.copy2(source_file, target_file)
            self.stats["copied_files"] += 1
            message = f"Copied '{source_file}' to '{target_file.parent}/'"
            self.logger.debug(message)

            # Copy sidecars
            sidecars = self.find_sidecars(source_file)
            for sidecar in sidecars:
                target_sidecar = target_file.parent / sidecar.name
                shutil.copy2(sidecar, target_sidecar)
                self.stats["copied_sidecars"] += 1
                sidecar_msg = f"Copied sidecar '{sidecar}' to '{target_file.parent}/'"
                self.logger.debug(sidecar_msg)

            return True

        except Exception as e:
            self.stats["errors"] += 1
            error_msg = f"Error copying {source_file}: {e}"
            self.logger.error(error_msg)
            return False

    def get_statistics(self) -> Dict:
        """
        Get processing statistics.

        Returns:
            Dictionary containing processing statistics
        """
        return self.stats.copy()

    def run(self) -> Dict:
        """
        Execute the image sampling process.

        Returns:
            Dictionary containing processing statistics
        """
        # Log header
        header = [
            "=" * 80,
            " [ImageSelector] Select a random sample of image files from source",
            "=" * 80,
            f"SOURCE={self.source}",
            f"TARGET={self.target}",
            f"MAX_FILES={self.max_files}",
            f"MAX_FOLDERS={self.max_folders}",
            f"MAX_DEPTH={self.max_depth}",
            f"MAX_PER_FOLDER={self.max_per_folder}",
        ]

        if self.clean_target:
            header.append("CLEAN mode enabled")
        if self.debug:
            header.append("DEBUG mode enabled")

        for line in header:
            self.logger.info(line)

        # Validate source directory
        if not self.source.exists():
            raise FileNotFoundError(f"Source directory '{self.source}' does not exist")
        if not self.source.is_dir():
            raise NotADirectoryError(f"Source '{self.source}' is not a directory")

        # Clean target if requested
        if self.clean_target:
            msg = f"Cleaning target folder: {self.target}"
            self.logger.info(msg)
            if self.target.exists():
                shutil.rmtree(self.target)

        # Create target directory
        self.target.mkdir(parents=True, exist_ok=True)

        # Select and copy files
        selected_files = self.select_files()

        if not selected_files:
            self.logger.info("No image files found to copy")
            return self.get_statistics()

        for file_path in selected_files:
            self.copy_file_with_metadata(file_path)

        # Final statistics
        summary = f"Copied {self.stats['copied_files']} files and {self.stats['copied_sidecars']} sidecars to {self.target}"
        self.logger.info(summary)

        if self.stats["errors"] > 0:
            self.logger.warning(
                f"Encountered {self.stats['errors']} errors during processing"
            )

        return self.get_statistics()
