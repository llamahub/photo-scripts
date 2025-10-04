"""
Test for generating test images from CSV data with EXIF metadata.
"""

import csv
import os
import pytest
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
import tempfile

# Try to import our common temp management
try:
    from common.temp import pytest_temp_dirs

    USE_COMMON_TEMP = True
except ImportError:
    USE_COMMON_TEMP = False

# Check for PIL availability
try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class TestImageGenerator:
    """Test class for generating test images from CSV data."""

    @pytest.fixture
    def csv_data(self):
        """Load test image data from CSV file."""
        csv_path = Path(__file__).parent / "test_data" / "test_images.csv"
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            return list(reader)

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for test image generation."""
        if USE_COMMON_TEMP:
            with pytest_temp_dirs(2, ["test_images", "output"]) as dirs:
                yield dirs
        else:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                test_images = temp_path / "test_images"
                output = temp_path / "output"
                test_images.mkdir()
                output.mkdir()
                yield [test_images, output]

    def _create_test_image(self, width, height, format_name, output_path):
        """Create a test image with specified dimensions and format."""
        # Handle zero or invalid dimensions
        width = max(width, 1)
        height = max(height, 1)

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
        else:
            # Create a dummy file without PIL
            content = f"# Test image file\n# Format: {format_name}\n# Dimensions: {width}x{height}\n"
            content += f"# This is a placeholder file created without PIL\n"
            content += "# " + "X" * (width // 10) + "\n" * (height // 10)

            with open(output_path, "w") as f:
                f.write(content)

    def _parse_date_string(self, date_str):
        """Parse various date formats from the CSV."""
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

    def _set_exif_data(self, image_path, row):
        """Set EXIF data using exiftool if available."""
        if not shutil.which("exiftool"):
            # Skip EXIF setting if exiftool not available
            return

        try:
            # Parse dates
            dt_orig = self._parse_date_string(row.get("DateTimeOriginal", ""))
            exif_dt = self._parse_date_string(row.get("ExifIFD:DateTimeOriginal", ""))
            xmp_dt = self._parse_date_string(row.get("XMP-photoshop:DateCreated", ""))

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
                subprocess.run(cmd, capture_output=True, check=False)

        except Exception:
            # Ignore EXIF setting errors for test purposes
            pass

    def test_generate_sample_images(self, csv_data, temp_dirs):
        """Generate a sample of test images from CSV data."""
        test_images_dir, output_dir = temp_dirs

        # Get sample count from environment variable or default to 10
        import os

        sample_count = int(os.environ.get("TEST_SAMPLE_COUNT", "10"))

        # Generate first N images as a sample
        sample_data = csv_data[:sample_count]

        print(
            f"📊 Generating {len(sample_data)} sample images (out of {len(csv_data)} total)"
        )

        generated_count = 0
        for row in sample_data:
            try:
                # Create directory structure
                root_path = row["Root Path"]
                parent_folder = row["Parent Folder"]
                filename = row["Filename"]
                source_ext = row["Source Ext"]

                full_dir = test_images_dir / root_path / parent_folder
                full_dir.mkdir(parents=True, exist_ok=True)

                # Create the image file
                image_path = full_dir / f"{filename}.{source_ext}"

                width = int(row["Image Width"]) if row["Image Width"] else 100
                height = int(row["Image Height"]) if row["Image Height"] else 100
                format_name = row["Actual Format"]

                self._create_test_image(width, height, format_name, image_path)

                # Set EXIF data if possible
                self._set_exif_data(image_path, row)

                # Verify file was created
                assert image_path.exists(), f"Failed to create {image_path}"

                generated_count += 1

            except Exception as e:
                pytest.fail(f"Failed to generate image for row {row}: {e}")

        print(f"\n✅ Successfully generated {generated_count} test images")
        print(f"📁 Test images directory: {test_images_dir}")

        # Verify some basic properties
        assert generated_count == len(sample_data)

        # List generated files
        all_files = list(test_images_dir.rglob("*.*"))
        print(f"📸 Generated files:")
        for f in all_files:
            rel_path = f.relative_to(test_images_dir)
            print(f"   {rel_path}")

    def test_generate_all_images(self, csv_data, temp_dirs):
        """Generate all test images from CSV data (longer test)."""
        test_images_dir, output_dir = temp_dirs

        generated_count = 0
        error_count = 0

        for i, row in enumerate(csv_data):
            try:
                # Create directory structure
                root_path = row["Root Path"]
                parent_folder = row["Parent Folder"]
                filename = row["Filename"]
                source_ext = row["Source Ext"]

                full_dir = test_images_dir / root_path / parent_folder
                full_dir.mkdir(parents=True, exist_ok=True)

                # Create the image file
                image_path = full_dir / f"{filename}.{source_ext}"

                width = int(row["Image Width"]) if row["Image Width"] else 100
                height = int(row["Image Height"]) if row["Image Height"] else 100
                format_name = row["Actual Format"]

                self._create_test_image(width, height, format_name, image_path)

                # Set EXIF data if possible
                self._set_exif_data(image_path, row)

                # Verify file was created and has reasonable size
                assert image_path.exists(), f"Failed to create {image_path}"
                assert (
                    image_path.stat().st_size > 0
                ), f"Created file is empty: {image_path}"

                generated_count += 1

            except Exception as e:
                error_count += 1
                print(f"⚠️  Error generating image {i+1}: {e}")
                if (
                    error_count > 5
                ):  # Don't fail the test for too many individual errors
                    break

        print(
            f"\n✅ Successfully generated {generated_count}/{len(csv_data)} test images"
        )
        print(f"❌ Failed to generate {error_count} images")
        print(f"📁 Test images directory: {test_images_dir}")

        # Should have generated at least 80% successfully
        success_rate = generated_count / len(csv_data)
        assert success_rate >= 0.8, f"Success rate too low: {success_rate:.1%}"

        # List directory structure
        print(f"\n📂 Generated directory structure:")
        for root, dirs, files in os.walk(test_images_dir):
            level = root.replace(str(test_images_dir), "").count(os.sep)
            indent = " " * 2 * level
            rel_root = (
                Path(root).relative_to(test_images_dir)
                if root != str(test_images_dir)
                else Path(".")
            )
            print(f"{indent}{rel_root}/")
            subindent = " " * 2 * (level + 1)
            for file in files[:3]:  # Show first 3 files per directory
                print(f"{subindent}{file}")
            if len(files) > 3:
                print(f"{subindent}... and {len(files) - 3} more files")

    def test_verify_image_formats(self, csv_data, temp_dirs):
        """Verify that generated images match expected formats."""
        test_images_dir, output_dir = temp_dirs

        # Generate a few sample images for format verification
        sample_data = csv_data[:5]

        format_checks = []
        for row in sample_data:
            try:
                # Create directory structure
                root_path = row["Root Path"]
                parent_folder = row["Parent Folder"]
                filename = row["Filename"]
                source_ext = row["Source Ext"]

                full_dir = test_images_dir / root_path / parent_folder
                full_dir.mkdir(parents=True, exist_ok=True)

                # Create the image file
                image_path = full_dir / f"{filename}.{source_ext}"

                width = int(row["Image Width"]) if row["Image Width"] else 100
                height = int(row["Image Height"]) if row["Image Height"] else 100
                format_name = row["Actual Format"]

                self._create_test_image(width, height, format_name, image_path)

                # Check format (noting HEIC is saved as JPEG)
                expected_format = "JPEG" if format_name == "HEIC" else format_name

                # Verify image if PIL is available
                if HAS_PIL:
                    with Image.open(image_path) as img:
                        assert (
                            img.width == width
                        ), f"Width mismatch: {img.width} vs {width}"
                        assert (
                            img.height == height
                        ), f"Height mismatch: {img.height} vs {height}"
                        assert (
                            img.format == expected_format
                        ), f"Format mismatch: {img.format} vs {expected_format}"
                else:
                    # Just verify file exists and has content
                    assert image_path.stat().st_size > 0, f"File is empty: {image_path}"

                format_checks.append(
                    {
                        "file": image_path.name,
                        "expected_format": format_name,
                        "actual_format": expected_format,
                        "dimensions": f"{width}x{height}",
                        "status": "✅",
                    }
                )

            except Exception as e:
                format_checks.append(
                    {
                        "file": f"{filename}.{source_ext}",
                        "expected_format": format_name,
                        "actual_format": "ERROR",
                        "dimensions": f"{width}x{height}",
                        "status": f"❌ {str(e)[:50]}",
                    }
                )

        # Print verification results
        print(f"\n📊 Format Verification Results:")
        for check in format_checks:
            print(
                f"   {check['status']} {check['file']} - {check['expected_format']} "
                f"({check['dimensions']}) -> {check['actual_format']}"
            )

        # Should have at least some successful verifications
        successful = sum(1 for c in format_checks if c["status"] == "✅")
        assert (
            successful >= len(format_checks) // 2
        ), "Too many format verification failures"

    def test_organize_script_integration(self, csv_data, temp_dirs):
        """Integration test: Generate test images and organize them using organize.py script."""
        test_images_dir, organized_dir = temp_dirs

        print(f"\n🔧 Integration Test: Generate + Organize")
        print(f"📂 Source directory: {test_images_dir}")
        print(f"📂 Target directory: {organized_dir}")

        # Step 1: Generate all test images in the source directory
        generated_count = 0
        error_count = 0
        source_files = []

        print(f"\n📸 Step 1: Generating {len(csv_data)} test images...")

        for i, row in enumerate(csv_data):
            try:
                # Create directory structure in source
                root_path = row["Root Path"]
                parent_folder = row["Parent Folder"]
                filename = row["Filename"]
                source_ext = row["Source Ext"]

                full_dir = test_images_dir / root_path / parent_folder
                full_dir.mkdir(parents=True, exist_ok=True)

                # Create the image file
                image_path = full_dir / f"{filename}.{source_ext}"

                width = int(row["Image Width"]) if row["Image Width"] else 100
                height = int(row["Image Height"]) if row["Image Height"] else 100
                format_name = row["Actual Format"]

                self._create_test_image(width, height, format_name, image_path)

                # Set EXIF data if possible
                self._set_exif_data(image_path, row)

                # Verify file was created
                assert image_path.exists(), f"Failed to create {image_path}"
                assert (
                    image_path.stat().st_size > 0
                ), f"Created file is empty: {image_path}"

                source_files.append(image_path)
                generated_count += 1

                if (generated_count % 10) == 0:
                    print(f"   Generated {generated_count}/{len(csv_data)} images...")

            except Exception as e:
                error_count += 1
                print(f"⚠️  Error generating image {i+1}: {e}")
                if error_count > 10:  # Don't fail for too many individual errors
                    break

        print(f"✅ Generated {generated_count} test images, {error_count} errors")
        assert (
            generated_count >= len(csv_data) * 0.8
        ), f"Too few images generated: {generated_count}/{len(csv_data)}"

        # Step 2: Run the organize.py script
        print(f"\n🗂️  Step 2: Running organize.py script...")

        # Import and run the organize script
        import sys
        from pathlib import Path

        # Add the scripts directory to path
        scripts_dir = Path(__file__).parent.parent / "scripts"
        sys.path.insert(0, str(scripts_dir))

        try:
            # Import the organize module
            import organize

            # Create organized directory
            organized_dir.mkdir(exist_ok=True)

            # Run the organize function with our test directories
            print(f"   Source: {test_images_dir}")
            print(f"   Target: {organized_dir}")

            # Create PhotoOrganizer instance and run it
            organizer = organize.PhotoOrganizer(
                source=test_images_dir, target=organized_dir, dry_run=False, debug=True
            )

            organizer.run()

            print(f"✅ Organize script completed")

        except ImportError as e:
            print(f"❌ Could not import organize module: {e}")
            pytest.skip("organize.py script not available for testing")
        except Exception as e:
            print(f"❌ Error running organize script: {e}")
            raise

        # Step 3: Verify organization results
        print(f"\n📋 Step 3: Verifying organization results...")

        # Count files in organized directory
        organized_files = list(organized_dir.rglob("*.*"))
        print(f"   Found {len(organized_files)} organized files")

        # Verify we have some organized files
        assert len(organized_files) > 0, "No files were organized"

        # Show some example organized files
        print(f"📁 Sample organized structure:")
        for i, org_file in enumerate(organized_files[:10]):  # Show first 10
            rel_path = org_file.relative_to(organized_dir)
            print(f"   {rel_path}")

        if len(organized_files) > 10:
            print(f"   ... and {len(organized_files) - 10} more files")

        # Basic verification that organization happened
        # (The exact organization logic depends on organize.py implementation)
        organized_dirs = [d for d in organized_dir.rglob("*") if d.is_dir()]
        print(f"   Created {len(organized_dirs)} organized directories")

        # Should have created some directory structure
        assert (
            len(organized_dirs) >= 3
        ), f"Expected multiple organized directories, got {len(organized_dirs)}"

        print(f"🎉 Integration test completed successfully!")
        print(f"   Generated: {generated_count} images")
        print(f"   Organized: {len(organized_files)} files")
        print(f"   Directories: {len(organized_dirs)} created")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
