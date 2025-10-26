import os
import csv
import json
import subprocess
import concurrent.futures
from pathlib import Path
from .image_data import ImageData


class ImageAnalyzer(ImageData):
    def get_exif(self, image_path):
        """Public method to extract EXIF data for a single image file using exiftool -j."""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"File not found: {image_path}")
        cmd = ["exiftool", "-j", image_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0 and result.stdout:
                data_list = json.loads(result.stdout)
                if data_list:
                    return data_list[0]
            return {}
        except Exception as e:
            self.logger.error(f"EXIF extraction failed for {image_path}: {e}")
            return {}

    """High-performance image analyzer with batch processing and parallel execution."""

    def __init__(
        self,
        folder_path=None,
        csv_output=None,
        max_workers=None,
        batch_size=100,
        target_path=None,
        output_path=None,
        label=None,
    ):
        """Initialize ImageAnalyzer with performance tuning options.

        Args:
            folder_path: Path to analyze
            csv_output: CSV output path (backward compatibility)
            max_workers: Number of parallel workers (default: CPU count)
            batch_size: Number of files to process in each ExifTool batch
            target_path: Optional target path for consistency analysis
            output_path: Output path (takes precedence over csv_output)
            label: Optional label for target filenames
        """
        self.folder_path = folder_path
        self.csv_output = output_path or csv_output
        self.target_path = Path(target_path) if target_path else None
        self.label = label
        self.results = []
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.batch_size = batch_size
        self._dimensions_cache = {}

        # Add logger for backward compatibility
        import logging

        self.logger = logging.getLogger(__name__)

    def analyze_images_fast(self, folder_path=None, progress_callback=None):
        """High-performance image analysis with batch ExifTool calls and parallel processing.

        Args:
            folder_path: Path to analyze
            progress_callback: Optional callback function for progress updates

        Returns:
            List of analysis results
        """
        if folder_path is None:
            folder_path = self.folder_path

        if not folder_path:
            raise ValueError("No folder path provided")

        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        # Find all image files
        image_files = self._find_image_files_fast(folder_path)

        if not image_files:
            return []

        print(f"Found {len(image_files)} images to analyze...")

        # Process in batches with parallel execution
        self.results = []
        total_files = len(image_files)

        for i in range(0, total_files, self.batch_size):
            batch = image_files[i : i + self.batch_size]
            batch_results = self._process_batch_parallel(batch)
            self.results.extend(batch_results)

            if progress_callback:
                progress = min(i + self.batch_size, total_files)
                progress_callback(progress, total_files)
            else:
                print(
                    f"Processed {min(i + self.batch_size, total_files)}/{total_files} images..."
                )

        return self.results

    def _find_image_files_fast(self, folder_path):
        """Fast image file discovery using pathlib."""
        image_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".tiff",
            ".tif",
            ".raw",
            ".cr2",
            ".nef",
            ".orf",
            ".raf",
            ".rw2",
        }
        image_files = []

        # Use pathlib for faster directory traversal
        path = Path(folder_path)
        for ext in image_extensions:
            # Use glob patterns for each extension (case insensitive)
            image_files.extend(path.rglob(f"*{ext}"))
            image_files.extend(path.rglob(f"*{ext.upper()}"))

        return [str(f) for f in image_files]

    def _process_batch_parallel(self, file_batch):
        """Process a batch of files with parallel ExifTool calls and analysis."""
        # Step 1: Batch ExifTool extraction for all files
        exif_data = self._batch_extract_exif(file_batch)

        # Step 2: Parallel analysis using the cached EXIF data
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            future_to_file = {
                executor.submit(
                    self._analyze_single_image_cached,
                    filepath,
                    exif_data.get(filepath, {}),
                ): filepath
                for filepath in file_batch
            }

            results = []
            for future in concurrent.futures.as_completed(future_to_file):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    filepath = future_to_file[future]
                    results.append(
                        {
                            "filepath": filepath,
                            "filename": os.path.basename(filepath),
                            "error": str(e),
                            "condition_category": "Error",
                        }
                    )

            return results

    def _batch_extract_exif(self, file_batch):
        """Extract EXIF data for multiple files in a single ExifTool call."""
        if not file_batch:
            return {}

        try:
            # Build exiftool command with all date fields from centralized priority
            cmd = ["exiftool", "-j"]

            # Add all date fields from centralized priority
            for field in self.get_date_field_priority():
                cmd.append(f"-{field}")

            # Add other metadata fields
            cmd.extend(
                [
                    "-FileTypeExtension",
                    "-ImageWidth",
                    "-ImageHeight",
                ]
            )

            # Add file paths
            cmd.extend(file_batch)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                data_list = json.loads(result.stdout)
                # Create filepath -> exif_data mapping
                exif_map = {}
                for item in data_list:
                    source_file = item.get("SourceFile", "")
                    if source_file:
                        exif_map[source_file] = item
                return exif_map

        except Exception as e:
            print(f"Batch EXIF extraction failed: {e}")

        return {}

    def _analyze_single_image_cached(self, image_path, exif_data=None):
        """Analyze a single image with full backward compatibility format."""
        try:
            # Get basic file info
            filename = os.path.basename(image_path)
            parent_name = ImageData.getParentName(image_path)

            # Get dates from different sources
            image_date = ImageData.getImageDate(image_path)
            filename_date = ImageData.getFilenameDate(image_path)
            parent_date = ImageData.normalize_parent_date(parent_name)

            # Extract alternative filename date if available
            alt_filename_date = ImageData.extract_alt_filename_date(
                image_path, parent_date
            )

            # Normalize dates for comparison
            parent_date_norm = ImageData.strip_time(parent_date)
            filename_date_norm = ImageData.strip_time(filename_date)
            image_date_norm = ImageData.strip_time(image_date)

            # Get condition analysis
            condition_desc, condition_category = ImageData.get_condition(
                parent_date_norm, filename_date_norm, image_date_norm
            )

            # Get month match analysis
            month_match = ImageData.get_month_match(
                parent_date_norm, filename_date_norm, image_date_norm
            )

            # Get image properties
            true_ext = ImageData.getTrueExt(image_path)

            # Get dimensions (cached from batch extraction or direct extraction)
            if (
                hasattr(self, "_dimensions_cache")
                and image_path in self._dimensions_cache
            ):
                width, height = self._dimensions_cache[image_path]
                width, height = str(width), str(
                    height
                )  # Convert to string format for compatibility
            else:
                # Fallback to direct dimension extraction
                width, height = ImageData.getImageSize(image_path)

            # Generate target filename for comparison
            target_filename = ImageData.getTargetFilename(
                image_path, "/tmp"
            )  # Use temp root for analysis

            return {
                "filepath": image_path,
                "filename": filename,
                "parent_name": parent_name,
                "parent_date": parent_date,
                "filename_date": filename_date,
                "image_date": image_date,
                "alt_filename_date": alt_filename_date,
                "parent_date_norm": parent_date_norm,
                "filename_date_norm": filename_date_norm,
                "image_date_norm": image_date_norm,
                "condition_desc": condition_desc,
                "condition_category": condition_category,
                "month_match": month_match,
                "true_ext": true_ext,
                "width": width,
                "height": height,
                "target_filename": os.path.basename(target_filename),
            }
        except Exception as e:
            self.logger.error(f"Error analyzing {image_path}: {str(e)}")
            return {
                "filepath": image_path,
                "filename": os.path.basename(image_path),
                "error": str(e),
                "condition_category": "Error",
                "true_ext": "",
                "width": "",
                "height": "",
                "target_filename": "",
            }

    def analyze_single_summary(self, image_path):
        """Public helper: return a compact summary for a single image.

        Fields returned:
            filepath, filename, target_filename, tags, true_ext,
            description, image_date, filename_date, parent_date

        This uses ImageData.get_exif() to request the canonical date fields
        and other basic metadata (FileTypeExtension, ImageWidth, ImageHeight).
        """
        from .image_data import ImageData

        if not image_path:
            raise ValueError("image_path is required")

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"File not found: {image_path}")

        # Use ImageData.get_exif to ensure prioritized date fields are requested
        exif_meta = ImageData.get_exif(image_path) or {}

        # Description (match existing ExifToolManager logic)
        description = str(exif_meta.get("Description", "")).strip()

        # Determine tags similar to ExifToolManager.norm_tags
        def _norm_tags(val):
            if isinstance(val, list):
                return sorted([str(t).strip() for t in val])
            if isinstance(val, str):
                return sorted([t.strip() for t in val.split(",") if t.strip()])
            return []

        true_ext = ImageData.getTrueExt(image_path)
        is_heic = true_ext.lower() in ["heic", "heif"]

        if is_heic:
            tags = _norm_tags(exif_meta.get("Subject", []))
        else:
            tags = _norm_tags(exif_meta.get("Keywords", []))

        # Dates
        image_date = ImageData.getImageDate(image_path)
        filename_date = ImageData.getFilenameDate(image_path)
        parent_name = ImageData.getParentName(image_path)
        parent_date = ImageData.normalize_parent_date(parent_name)

        # Target filename generation (use temp root for analysis consistency)
        target_full = ImageData.getTargetFilename(image_path, "/tmp")
        target_filename = os.path.basename(target_full)

        # Include a small set of extracted fields for width/height if present
        width = str(exif_meta.get("ImageWidth", ""))
        height = str(exif_meta.get("ImageHeight", ""))

        return {
            "filepath": str(image_path),
            "filename": os.path.basename(image_path),
            "target_filename": target_filename,
            "tags": tags,
            "true_ext": true_ext,
            "description": description,
            "image_date": image_date,
            "filename_date": filename_date,
            "parent_date": parent_date,
            # Raw EXIF date fields (returned in the requested order even if missing)
            "DateTimeOriginal": exif_meta.get("DateTimeOriginal", ""),
            "ExifIFD:DateTimeOriginal": exif_meta.get("ExifIFD:DateTimeOriginal", ""),
            "XMP-photoshop:DateCreated": exif_meta.get("XMP-photoshop:DateCreated", ""),
            "CreateDate": exif_meta.get("CreateDate", ""),
            "ModifyDate": exif_meta.get("ModifyDate", ""),
            "MediaCreateDate": exif_meta.get("MediaCreateDate", ""),
            "MediaModifyDate": exif_meta.get("MediaModifyDate", ""),
            "TrackCreateDate": exif_meta.get("TrackCreateDate", ""),
            "TrackModifyDate": exif_meta.get("TrackModifyDate", ""),
            "FileModifyDate": exif_meta.get("FileModifyDate", ""),
            "FileTypeExtension": exif_meta.get("FileTypeExtension", ""),
            "ImageWidth": width,
            "ImageHeight": height,
        }

    # Backward compatibility methods for test compatibility
    def _analyze_single_image(self, image_path):
        """Backward compatibility method for tests."""
        return self._analyze_single_image_cached(image_path)

    def analyze_images(self, folder_path=None):
        """Backward compatibility method for tests that calls individual _analyze_single_image for each file."""
        if folder_path is None:
            folder_path = self.folder_path

        if not folder_path:
            raise ValueError("No folder path provided")

        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        # Find all image files
        image_files = self._find_image_files_fast(folder_path)

        if not image_files:
            return []

        print(f"Found {len(image_files)} images to analyze...")

        # Process each file individually (for test compatibility)
        results = []
        for image_file in image_files:
            result = self._analyze_single_image(image_file)
            results.append(result)

        print(f"Processed {len(results)}/{len(image_files)} images...")

        self.results = results
        return results

    def _getImageDate_cached(self, filepath, exif_data):
        """Get image date using cached EXIF data with same priority as ImageData.getImageDate()."""
        import re

        # Use centralized date field priority from ImageData
        for key in self.get_date_field_priority():
            if key in exif_data and exif_data[key]:
                dt = exif_data[key]
                dt = re.sub(
                    r"^(\d{4})[:_-](\d{2})[:_-](\d{2})[ T_]?(\d{2})?:?(\d{2})?:?(\d{2})?",
                    r"\1-\2-\3 \4:\5:\6",
                    dt,
                )
                return self.normalize_date(dt)

        # Fallback to filename date
        filename_date = self.getFilenameDate(filepath)
        if filename_date != "1900-01-01 00:00":
            return filename_date

        return "1900-01-01 00:00"

    def analyze_with_progress(self, folder_path=None):
        """Analyze with progress reporting."""

        def progress_callback(current, total):
            percentage = (current / total) * 100
            print(f"Progress: {current}/{total} ({percentage:.1f}%)")

        return self.analyze_images_fast(folder_path, progress_callback)

    def analyze_sample(self, folder_path=None, sample_size=100):
        """Analyze a random sample for quick overview."""
        import random

        if folder_path is None:
            folder_path = self.folder_path

        image_files = self._find_image_files_fast(folder_path)

        if len(image_files) <= sample_size:
            return self.analyze_images_fast(folder_path)

        # Random sample
        sample_files = random.sample(image_files, sample_size)
        print(
            f"Analyzing sample of {sample_size} images from {len(image_files)} total..."
        )

        batch_results = self._process_batch_parallel(sample_files)
        self.results = batch_results
        return batch_results

    # Inherit all other methods from ImageAnalyzer
    def save_to_csv(self, csv_path=None, results=None):
        """Save analysis results to CSV file."""
        if csv_path is None:
            csv_path = self.csv_output

        if results is None:
            results = self.results

        if not csv_path:
            raise ValueError("No CSV output path provided")

        if not results:
            raise ValueError("No results to save")

        os.makedirs(os.path.dirname(csv_path), exist_ok=True)

        headers = [
            "filepath",
            "filename",
            "parent_name",
            "parent_date",
            "filename_date",
            "image_date",
            "alt_filename_date",
            "parent_date_norm",
            "filename_date_norm",
            "image_date_norm",
            "condition_desc",
            "condition_category",
            "true_ext",
            "width",
            "height",
            "target_filename",
            "error",
        ]

        with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()

            for result in results:
                row = {header: result.get(header, "") for header in headers}
                writer.writerow(row)

    def get_statistics(self, results=None):
        """Get statistics about the analysis results."""
        if results is None:
            results = self.results

        if not results:
            return {}

        total_images = len(results)
        categories = {}
        errors = 0

        for result in results:
            if "error" in result:
                errors += 1
                continue

            category = result.get("condition_category", "Unknown")
            categories[category] = categories.get(category, 0) + 1

        stats = {
            "total_images": total_images,
            "successful_analyses": total_images - errors,
            "errors": errors,
            "categories": categories,
        }

        if total_images > 0:
            stats["category_percentages"] = {
                cat: round((count / total_images) * 100, 2)
                for cat, count in categories.items()
            }

        return stats

    def print_statistics(self, results=None):
        """Print analysis statistics to console."""
        stats = self.get_statistics(results)

        if not stats:
            print("No analysis results available")
            return

        print(f"\nAnalysis Statistics:")
        print(f"Total images: {stats['total_images']}")
        print(f"Successful analyses: {stats['successful_analyses']}")

        if stats["errors"] > 0:
            print(f"Errors: {stats['errors']}")

        print(f"\nCondition Categories:")
        for category, count in stats["categories"].items():
            percentage = stats["category_percentages"].get(category, 0)
            print(f"  {category}: {count} ({percentage}%)")
