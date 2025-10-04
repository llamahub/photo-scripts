"""
Image Generator for Test Data

This module provides functionality to generate test images from CSV data with EXIF metadata.
Used for creating realistic test datasets for photo organization testing.

The ImageGenerator class handles:
- Reading CSV data with image specifications
- Creating images with PIL/Pillow in various formats
- Setting EXIF metadata using exiftool
- Managing directory structures and file organization
- Progress reporting and statistics tracking
"""

import csv
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Try to import PIL for real image generation
try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Try to import logging from common framework
try:
    import sys
    from pathlib import Path as PathLib

    # Add COMMON src to path for logging
    current_file = PathLib(__file__)
    common_src = current_file.parent.parent.parent.parent / "COMMON" / "src"
    if common_src.exists() and str(common_src) not in sys.path:
        sys.path.insert(0, str(common_src))

    from common.logging import setup_logging

    HAS_COMMON_LOGGING = True
except ImportError:
    import logging

    HAS_COMMON_LOGGING = False


class ImageGenerator:
    """
    Generate test images from CSV data with EXIF metadata.

    This class reads CSV data containing image specifications and generates
    corresponding test images with proper directory structures and EXIF metadata.
    """

    def __init__(
        self,
        csv_path: Path,
        output_dir: Path,
        debug: bool = False,
        use_exiftool: bool = True,
    ):
        """
        Initialize the ImageGenerator.

        Args:
            csv_path: Path to CSV file containing image specifications
            output_dir: Directory where generated images will be saved
            debug: Enable debug logging
            use_exiftool: Whether to use exiftool for EXIF metadata (requires exiftool installed)
        """
        self.csv_path = Path(csv_path)
        self.output_dir = Path(output_dir)
        self.debug = debug
        self.use_exiftool = use_exiftool and shutil.which("exiftool") is not None

        # Initialize logging
        if HAS_COMMON_LOGGING:
            self.logger = setup_logging("image_generator", debug=debug)
        else:
            logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
            self.logger = logging.getLogger("image_generator")

        # Statistics tracking
        self.stats = {
            "total_rows": 0,
            "generated": 0,
            "errors": 0,
            "exif_set": 0,
            "formats": {},
        }

        # Validate inputs
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"ImageGenerator initialized")
        self.logger.info(f"CSV file: {self.csv_path}")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"PIL available: {HAS_PIL}")
        self.logger.info(f"Exiftool available: {self.use_exiftool}")

    def load_csv_data(self) -> List[Dict[str, str]]:
        """
        Load image specifications from CSV file.

        Returns:
            List of dictionaries containing image specifications
        """
        try:
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                data = list(reader)

            self.stats["total_rows"] = len(data)
            self.logger.info(f"Loaded {len(data)} image specifications from CSV")

            return data

        except Exception as e:
            self.logger.error(f"Failed to load CSV data: {e}")
            raise

    def create_test_image(
        self, width: int, height: int, format_name: str, output_path: Path
    ) -> bool:
        """
        Create a test image with specified dimensions and format.

        Args:
            width: Image width in pixels
            height: Image height in pixels
            format_name: Image format (JPEG, PNG, TIFF, HEIC)
            output_path: Path where image will be saved

        Returns:
            True if image was created successfully, False otherwise
        """
        try:
            # Handle zero or invalid dimensions
            width = max(width, 1)
            height = max(height, 1)

            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if HAS_PIL:
                # Create a real image with PIL
                if format_name == "JPEG":
                    mode = "RGB"
                    color = (128, 128, 255)  # Light blue
                elif format_name == "PNG":
                    mode = "RGBA"
                    color = (255, 128, 128, 255)  # Light red with alpha
                elif format_name == "TIFF":
                    mode = "RGB"
                    color = (128, 255, 128)  # Light green
                elif format_name == "HEIC":
                    # HEIC not supported by PIL, create as JPEG
                    mode = "RGB"
                    color = (255, 255, 128)  # Light yellow
                else:
                    mode = "RGB"
                    color = (192, 192, 192)  # Light gray

                # Create the image
                img = Image.new(mode, (width, height), color)

                # Save with appropriate format
                if format_name == "HEIC":
                    # Save as JPEG since PIL doesn't support HEIC
                    img.save(output_path, "JPEG", quality=95)
                else:
                    img.save(
                        output_path,
                        format_name,
                        quality=95 if format_name == "JPEG" else None,
                    )

                self.logger.debug(
                    f"Created PIL image: {output_path} ({width}x{height}, {format_name})"
                )
            else:
                # Create a dummy file without PIL
                content = f"# Test image file\n# Format: {format_name}\n# Dimensions: {width}x{height}\n"
                content += f"# This is a placeholder file created without PIL\n"
                content += "# " + "X" * (width // 10) + "\n" * (height // 10)

                with open(output_path, "w") as f:
                    f.write(content)

                self.logger.debug(
                    f"Created placeholder file: {output_path} ({width}x{height}, {format_name})"
                )

            # Track format statistics
            self.stats["formats"][format_name] = (
                self.stats["formats"].get(format_name, 0) + 1
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to create image {output_path}: {e}")
            return False

    def parse_date_string(self, date_str: str) -> Optional[datetime]:
        """
        Parse various date formats from CSV data.

        Args:
            date_str: Date string in various formats

        Returns:
            Parsed datetime object or None if parsing fails
        """
        if not date_str or date_str.strip() == "":
            return None

        date_str = date_str.strip()

        # Handle EXIF format: YYYY:MM:DD HH:MM:SS
        if ":" in date_str and len(date_str) > 10:
            try:
                return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
            except ValueError:
                pass

        # Handle M/D/YY format
        if "/" in date_str:
            try:
                # Try M/D/YY HH:MM format first
                if " " in date_str:
                    return datetime.strptime(date_str, "%m/%d/%y %H:%M")
                else:
                    # Just M/D/YY
                    return datetime.strptime(date_str, "%m/%d/%y")
            except ValueError:
                pass

        return None

    def set_exif_data(self, image_path: Path, row: Dict[str, str]) -> bool:
        """
        Set EXIF data using exiftool if available.

        Args:
            image_path: Path to the image file
            row: CSV row data containing EXIF information

        Returns:
            True if EXIF data was set successfully, False otherwise
        """
        if not self.use_exiftool:
            return False

        try:
            # Parse dates from CSV data
            dt_orig = self.parse_date_string(row.get("DateTimeOriginal", ""))
            exif_dt = self.parse_date_string(row.get("ExifIFD:DateTimeOriginal", ""))
            xmp_dt = self.parse_date_string(row.get("XMP-photoshop:DateCreated", ""))

            # Build exiftool command
            cmd = ["exiftool", "-overwrite_original"]

            if dt_orig:
                cmd.extend(
                    [f'-DateTimeOriginal={dt_orig.strftime("%Y:%m:%d %H:%M:%S")}']
                )

            if exif_dt:
                cmd.extend(
                    [
                        f'-ExifIFD:DateTimeOriginal={exif_dt.strftime("%Y:%m:%d %H:%M:%S")}'
                    ]
                )

            if xmp_dt:
                cmd.extend(
                    [f'-XMP-photoshop:DateCreated={xmp_dt.strftime("%Y-%m-%d")}']
                )

            cmd.append(str(image_path))

            # Run exiftool if we have any dates to set
            if len(cmd) > 3:  # More than just base command
                result = subprocess.run(
                    cmd, capture_output=True, check=False, text=True
                )

                if result.returncode == 0:
                    self.logger.debug(f"Set EXIF data for: {image_path}")
                    return True
                else:
                    self.logger.warning(
                        f"Exiftool failed for {image_path}: {result.stderr}"
                    )

        except Exception as e:
            self.logger.warning(f"Failed to set EXIF data for {image_path}: {e}")

        return False

    def generate_image_from_row(self, row: Dict[str, str]) -> bool:
        """
        Generate a single image from CSV row data.

        Args:
            row: Dictionary containing image specification data

        Returns:
            True if image was generated successfully, False otherwise
        """
        try:
            # Extract image specification from CSV row
            root_path = row.get("Root Path", "")
            parent_folder = row.get("Parent Folder", "")
            filename = row.get("Filename", "")
            source_ext = row.get("Source Ext", "jpg")

            if not filename:
                self.logger.warning(f"No filename in row: {row}")
                return False

            # Create directory structure
            full_dir = self.output_dir / root_path / parent_folder
            full_dir.mkdir(parents=True, exist_ok=True)

            # Create the image file path
            image_path = full_dir / f"{filename}.{source_ext}"

            # Get image dimensions and format
            width = int(row.get("Image Width", 100)) if row.get("Image Width") else 100
            height = (
                int(row.get("Image Height", 100)) if row.get("Image Height") else 100
            )
            format_name = row.get("Actual Format", "JPEG")

            # Create the image
            if not self.create_test_image(width, height, format_name, image_path):
                return False

            # Set EXIF data if possible
            if self.set_exif_data(image_path, row):
                self.stats["exif_set"] += 1

            # Verify file was created
            if not image_path.exists():
                self.logger.error(f"Image file was not created: {image_path}")
                return False

            if image_path.stat().st_size == 0:
                self.logger.error(f"Created image file is empty: {image_path}")
                return False

            self.logger.debug(f"Generated image: {image_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to generate image from row {row}: {e}")
            return False

    def generate_images(
        self, limit: Optional[int] = None, sample_size: Optional[int] = None
    ) -> bool:
        """
        Generate all images from CSV data.

        Args:
            limit: Maximum number of images to generate (None for all)
            sample_size: Generate only first N images as a sample (None for all)

        Returns:
            True if generation completed successfully, False otherwise
        """
        try:
            # Load CSV data
            csv_data = self.load_csv_data()

            if not csv_data:
                self.logger.error("No data loaded from CSV file")
                return False

            # Apply sample size or limit
            if sample_size is not None:
                csv_data = csv_data[:sample_size]
                self.logger.info(
                    f"Generating {len(csv_data)} sample images (sample_size={sample_size})"
                )
            elif limit is not None:
                csv_data = csv_data[:limit]
                self.logger.info(f"Generating {len(csv_data)} images (limit={limit})")
            else:
                self.logger.info(f"Generating all {len(csv_data)} images")

            # Reset generation statistics
            self.stats["generated"] = 0
            self.stats["errors"] = 0
            self.stats["exif_set"] = 0
            self.stats["formats"] = {}

            # Generate images
            for i, row in enumerate(csv_data, 1):
                if self.generate_image_from_row(row):
                    self.stats["generated"] += 1
                else:
                    self.stats["errors"] += 1

                # Progress reporting
                if i % 10 == 0 or i == len(csv_data):
                    self.logger.info(f"Progress: {i}/{len(csv_data)} images processed")

            # Final statistics
            success_rate = self.stats["generated"] / len(csv_data) if csv_data else 0

            self.logger.info("=" * 80)
            self.logger.info(" IMAGE GENERATION COMPLETE")
            self.logger.info("=" * 80)
            self.logger.info(f"Total rows processed: {len(csv_data)}")
            self.logger.info(f"Images generated: {self.stats['generated']}")
            self.logger.info(f"Generation errors: {self.stats['errors']}")
            self.logger.info(f"EXIF data set: {self.stats['exif_set']}")
            self.logger.info(f"Success rate: {success_rate:.1%}")

            # Format statistics
            if self.stats["formats"]:
                self.logger.info("Format breakdown:")
                for fmt, count in sorted(self.stats["formats"].items()):
                    self.logger.info(f"  {fmt}: {count} images")

            self.logger.info("=" * 80)

            return success_rate >= 0.8  # Success if at least 80% generated

        except Exception as e:
            self.logger.error(f"Failed to generate images: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get generation statistics.

        Returns:
            Dictionary containing generation statistics
        """
        return self.stats.copy()

    def run(
        self, limit: Optional[int] = None, sample_size: Optional[int] = None
    ) -> bool:
        """
        Main entry point to run image generation.

        Args:
            limit: Maximum number of images to generate
            sample_size: Generate sample of first N images

        Returns:
            True if generation successful, False otherwise
        """
        self.logger.info("Starting image generation...")

        try:
            success = self.generate_images(limit=limit, sample_size=sample_size)

            if success:
                self.logger.info("Image generation completed successfully")
            else:
                self.logger.error("Image generation failed or had low success rate")

            return success

        except Exception as e:
            self.logger.error(f"Image generation failed: {e}")
            return False
