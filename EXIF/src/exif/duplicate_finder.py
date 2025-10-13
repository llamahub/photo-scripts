"""
Duplicate finder business logic for finding duplicate images between source and target directories.

This module provides the DuplicateFinder class that implements multiple strategies
for finding duplicates: Target Filename match, Exact match, and Partial Filename match.
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict
import csv

try:
    from .image_data import ImageData
except ImportError:
    # Fallback for direct execution
    from image_data import ImageData

# Import COMMON FileManager with fallback
try:
    import sys

    common_src_path = Path(__file__).parent.parent.parent.parent / "COMMON" / "src"
    sys.path.insert(0, str(common_src_path))
    from common.file_manager import FileManager
except ImportError:
    FileManager = None


class DuplicateFinder:
    """Handles duplicate detection between source and target directories."""

    def __init__(self, source_dir: Path, target_dir: Path, logger: logging.Logger):
        """Initialize the duplicate finder with source and target directories."""
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.logger = logger
        self.stats = {
            "total_processed": 0,
            "target_filename_matches": 0,
            "exact_matches": 0,
            "partial_matches": 0,
            "no_matches": 0,
            "errors": 0,
        }

        # Performance optimization caches
        self._target_files_cache = None
        self._target_name_index = {}  # filename -> Path mapping
        self._target_stem_index = {}  # stem -> [Path] mapping
        self._target_path_index = (
            set()
        )  # Set of all target file paths for O(1) exists check
        self._target_filename_cache = (
            {}
        )  # Cache getTargetFilename results to avoid EXIF reads
        self._indexes_built = False

    def get_image_files(self, directory: Path) -> List[Path]:
        """Get all image and video files from directory recursively (optimized for large datasets)."""
        # Get supported extensions from FileManager
        if FileManager:
            extensions = FileManager.get_all_media_extensions()
        else:
            # Fallback extensions if FileManager not available
            extensions = {
                # Images
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".bmp",
                ".tiff",
                ".tif",
                ".webp",
                ".heic",
                ".heif",
                ".raw",
                ".cr2",
                ".nef",
                ".arw",
                ".dng",
                ".orf",
                ".rw2",
                ".pef",
                ".srw",
                ".x3f",
                # Videos
                ".mp4",
                ".avi",
                ".mov",
                ".wmv",
                ".flv",
                ".webm",
                ".mkv",
                ".m4v",
                ".3gp",
                ".mpg",
                ".mpeg",
                ".mts",
                ".m2ts",
                ".ts",
            }

        files = []
        file_count = 0

        try:
            # Use iterator for memory efficiency with large directories
            for file_path in directory.rglob("*"):
                try:
                    if file_path.is_file() and file_path.suffix.lower() in extensions:
                        files.append(file_path)
                        file_count += 1

                        # Progress report for very large directories
                        if file_count % 10000 == 0:
                            self.logger.info(
                                f"Scanned {file_count} image/video files so far..."
                            )

                except (OSError, PermissionError) as e:
                    # Skip individual files that can't be accessed
                    self.logger.debug(f"Skipping file {file_path}: {e}")
                    continue

        except PermissionError as e:
            self.logger.warning(f"Permission denied accessing {directory}: {e}")
        except Exception as e:
            self.logger.error(f"Error scanning directory {directory}: {e}")

        return files

    def _get_target_files(self) -> List[Path]:
        """Get and cache target files for performance."""
        if self._target_files_cache is None:
            self._target_files_cache = self.get_image_files(self.target_dir)
        return self._target_files_cache

    def _build_target_indexes(self) -> None:
        """Build performance indexes for target files."""
        if self._indexes_built:
            return

        target_files = self._get_target_files()
        self.logger.info(
            f"Building performance indexes for {len(target_files)} target files..."
        )

        # Build multiple indexes for O(1) lookups
        for target_file in target_files:
            # Exact filename index
            filename_lower = target_file.name.lower()
            self._target_name_index[filename_lower] = target_file

            # Stem index for partial matching
            stem_lower = target_file.stem.lower()
            if stem_lower not in self._target_stem_index:
                self._target_stem_index[stem_lower] = []
            self._target_stem_index[stem_lower].append(target_file)

            # Path index for fast exists check
            self._target_path_index.add(str(target_file))

        self._indexes_built = True
        self.logger.info("Performance indexes built successfully")

    def find_target_filename_match(self, source_file: Path) -> Optional[Path]:
        """Find match using ImageData.getTargetFilename() with caching to avoid repeated EXIF reads."""
        source_str = str(source_file)

        # Check cache first to avoid expensive EXIF operations
        if source_str in self._target_filename_cache:
            expected_target = self._target_filename_cache[source_str]
        else:
            try:
                # This is expensive - calls exiftool multiple times!
                expected_target = ImageData.getTargetFilename(
                    source_str, str(self.target_dir)
                )
                self._target_filename_cache[source_str] = expected_target
            except Exception as e:
                self.logger.debug(
                    f"Error in target filename generation for {source_file}: {e}"
                )
                self._target_filename_cache[source_str] = None
                return None

        if expected_target and expected_target in self._target_path_index:
            expected_path = Path(expected_target)
            self.logger.debug(
                f"Target filename match: {source_file.name} -> {expected_path}"
            )
            return expected_path

        return None

    def find_exact_match(self, source_file: Path) -> Optional[Path]:
        """Find exact filename match using index for O(1) lookup."""
        source_name = source_file.name.lower()

        target_file = self._target_name_index.get(source_name)
        if target_file:
            self.logger.debug(f"Exact match: {source_file.name} -> {target_file}")
            return target_file

        return None

    def find_partial_match(self, source_file: Path) -> Optional[Path]:
        """Find partial filename match using optimized search."""
        source_stem = source_file.stem.lower()

        # Clean the source name - remove common prefixes/suffixes that might differ
        source_clean = (
            source_stem.replace("img_", "")
            .replace("dsc_", "")
            .replace("dscf", "")
            .replace("_(02)", "")
            .replace("_(03)", "")
            .replace("_(04)", "")
            .replace("_copy", "")
            .replace(" copy", "")
            .replace("__", "_")
        )

        # Only proceed if we have a reasonable base name
        if len(source_clean) < 4:
            return None

        # Strategy 1: Check if exact stem exists (fastest)
        if source_stem in self._target_stem_index:
            target_file = self._target_stem_index[source_stem][0]  # Take first match
            self.logger.debug(f"Exact stem match: {source_file.name} -> {target_file}")
            return target_file

        # Strategy 2: Check cleaned stem
        if source_clean != source_stem and source_clean in self._target_stem_index:
            target_file = self._target_stem_index[source_clean][0]
            self.logger.debug(
                f"Cleaned stem match: {source_file.name} -> {target_file}"
            )
            return target_file

        # Strategy 3: Partial matching (only for longer names to avoid false positives)
        if len(source_clean) > 8:
            for target_stem, target_files in self._target_stem_index.items():
                target_clean = (
                    target_stem.replace("img_", "")
                    .replace("dsc_", "")
                    .replace("dscf", "")
                    .replace("_(02)", "")
                    .replace("_(03)", "")
                    .replace("_(04)", "")
                    .replace("_copy", "")
                    .replace(" copy", "")
                    .replace("__", "_")
                )

                if source_clean in target_clean or target_clean in source_clean:
                    target_file = target_files[0]
                    self.logger.debug(
                        f"Partial match: {source_file.name} -> {target_file}"
                    )
                    return target_file

        return None

    def find_duplicate(self, source_file: Path) -> Tuple[Optional[Path], str]:
        """
        Find duplicate for source file using multiple strategies in order of performance.

        Returns:
            Tuple of (target_path, match_type)
        """
        # Strategy 1: Exact match (O(1) lookup - fastest)
        exact_match = self.find_exact_match(source_file)
        if exact_match:
            self.stats["exact_matches"] += 1
            return exact_match, "Exact match"

        # Strategy 2: Partial Filename match (optimized - fast)
        partial_match = self.find_partial_match(source_file)
        if partial_match:
            self.stats["partial_matches"] += 1
            return partial_match, "Partial Filename"

        # Strategy 3: Target Filename match (expensive EXIF reads - last resort)
        target_match = self.find_target_filename_match(source_file)
        if target_match:
            self.stats["target_filename_matches"] += 1
            return target_match, "Target Filename"

        # No match found
        self.stats["no_matches"] += 1
        return None, "none"

    def process_duplicates(self) -> List[Dict]:
        """Process all source files and find duplicates in target directory."""
        self.logger.info(f"Scanning source directory: {self.source_dir}")
        source_files = self.get_image_files(self.source_dir)
        self.logger.info(f"Found {len(source_files)} source files")

        self.logger.info(f"Scanning target directory: {self.target_dir}")
        target_files = self._get_target_files()
        self.logger.info(f"Found {len(target_files)} target files")

        if not source_files:
            self.logger.warning("No image/video files found in source directory")
            return []

        if not target_files:
            self.logger.warning("No image/video files found in target directory")
            return []

        # Build performance indexes before processing
        self._build_target_indexes()

        results = []
        batch_size = 1000  # Process in batches for better progress reporting

        for i, source_file in enumerate(source_files):
            self.stats["total_processed"] += 1

            # Progress reporting for large datasets
            if self.stats["total_processed"] % batch_size == 0 or self.stats[
                "total_processed"
            ] == len(source_files):
                percent = (self.stats["total_processed"] / len(source_files)) * 100
                self.logger.info(
                    f"Processed {self.stats['total_processed']}/{len(source_files)} files ({percent:.1f}%)"
                )

            try:
                target_path, match_type = self.find_duplicate(source_file)

                results.append(
                    {
                        "source_file_path": str(source_file),
                        "target_file_path": str(target_path) if target_path else "",
                        "match_type": match_type,
                    }
                )

            except Exception as e:
                self.logger.error(f"Error processing {source_file}: {e}")
                self.stats["errors"] += 1
                results.append(
                    {
                        "source_file_path": str(source_file),
                        "target_file_path": "",
                        "match_type": "error",
                    }
                )

        return results

    def save_results(self, results: List[Dict], output_file: Path) -> None:
        """Save results to CSV file (optimized for large datasets)."""
        try:
            with open(
                output_file, "w", newline="", encoding="utf-8", buffering=8192
            ) as csvfile:
                fieldnames = ["source_file_path", "target_file_path", "match_type"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()

                # Write in batches for better performance with large result sets
                batch_size = 5000
                for i in range(0, len(results), batch_size):
                    batch = results[i : i + batch_size]
                    for result in batch:
                        writer.writerow(result)

                    # Progress for very large result sets
                    if len(results) > 10000 and i + batch_size < len(results):
                        self.logger.info(
                            f"Saved {i + batch_size}/{len(results)} results..."
                        )

            self.logger.info(f"Results saved to: {output_file}")

        except Exception as e:
            self.logger.error(f"Error saving results to {output_file}: {e}")
            self.stats["errors"] += 1

    def get_stats(self) -> Dict:
        """Return processing statistics."""
        return self.stats.copy()

    def print_summary(self) -> None:
        """Print processing summary statistics."""
        self.logger.info("=" * 60)
        self.logger.info("DUPLICATE FINDER SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total files processed: {self.stats['total_processed']}")
        self.logger.info(
            f"Target Filename matches: {self.stats['target_filename_matches']}"
        )
        self.logger.info(f"Exact matches: {self.stats['exact_matches']}")
        self.logger.info(f"Partial matches: {self.stats['partial_matches']}")
        self.logger.info(f"No matches: {self.stats['no_matches']}")
        self.logger.info(f"Errors: {self.stats['errors']}")
        self.logger.info("=" * 60)
