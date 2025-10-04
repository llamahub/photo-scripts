"""
Integration tests for image generation functionality.

These tests focus on integration workflows using the ImageGenerator class
and integration with the PhotoOrganizer for complete end-to-end testing.
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
    import sys
    from pathlib import Path

    # Add COMMON src directory to path if not already present
    common_src = Path(__file__).parent.parent.parent / "COMMON" / "src"
    if str(common_src) not in sys.path:
        sys.path.insert(0, str(common_src))

    from common.temp import pytest_temp_dirs

    USE_COMMON_TEMP = True
except ImportError:
    USE_COMMON_TEMP = False

# Add project src directory to path for ImageGenerator and PhotoOrganizer
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from exif import ImageGenerator, PhotoOrganizer

# Check for PIL availability
try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class TestImageGenerationIntegration:
    """Integration tests for image generation workflows."""

    @pytest.fixture
    def csv_path(self):
        """Get path to the test CSV file."""
        return Path(__file__).parent / "test_data" / "test_images.csv"

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

    def test_generate_sample_images(self, csv_path, temp_dirs):
        """Generate a sample of test images from CSV data using ImageGenerator."""
        test_images_dir, output_dir = temp_dirs

        # Get sample count from environment variable or default to 10
        sample_count = int(os.environ.get("TEST_SAMPLE_COUNT", "10"))

        print(f"📊 Generating sample of {sample_count} images using ImageGenerator")

        # Create ImageGenerator instance
        generator = ImageGenerator(
            csv_path=csv_path,
            output_dir=test_images_dir,
            debug=False,
            use_exiftool=False,  # Skip exiftool for faster testing
        )

        # Generate sample images
        success = generator.run(sample_size=sample_count)

        assert success, "Image generation should succeed"

        # Get statistics
        stats = generator.get_stats()

        print(f"\n✅ Successfully generated {stats['generated']} test images")
        print(f"📁 Test images directory: {test_images_dir}")

        # Verify generation succeeded
        assert (
            stats["generated"] >= sample_count * 0.8
        ), "Should generate at least 80% of requested images"
        assert stats["errors"] <= sample_count * 0.2, "Should have few errors"

        # List generated files
        all_files = list(test_images_dir.rglob("*.*"))
        print(f"📸 Generated files:")
        for f in all_files:
            rel_path = f.relative_to(test_images_dir)
            print(f"   {rel_path}")

        # Should have generated some files
        assert len(all_files) > 0, "Should have generated at least some images"

    def test_generate_all_images(self, csv_path, temp_dirs):
        """Generate all test images from CSV data using ImageGenerator (longer test)."""
        test_images_dir, output_dir = temp_dirs

        print("📊 Generating all images from CSV using ImageGenerator")

        # Create ImageGenerator instance
        generator = ImageGenerator(
            csv_path=csv_path,
            output_dir=test_images_dir,
            debug=False,
            use_exiftool=False,  # Skip exiftool for faster testing
        )

        # Generate all images
        success = generator.run()

        # Get statistics
        stats = generator.get_stats()

        print(
            f"\n✅ Successfully generated {stats['generated']}/{stats['total_rows']} test images"
        )
        print(f"❌ Failed to generate {stats['errors']} images")
        print(f"📁 Test images directory: {test_images_dir}")

        # Should have generated at least 80% successfully
        success_rate = (
            stats["generated"] / stats["total_rows"] if stats["total_rows"] > 0 else 0
        )
        assert success_rate >= 0.8, f"Success rate too low: {success_rate:.1%}"

        # Verify we actually generated images
        assert stats["generated"] > 0, "Should have generated at least some images"

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

    def test_verify_image_formats(self, csv_path, temp_dirs):
        """Verify that generated images match expected formats using ImageGenerator."""
        test_images_dir, output_dir = temp_dirs

        print("📊 Verifying image formats using ImageGenerator")

        # Create ImageGenerator instance
        generator = ImageGenerator(
            csv_path=csv_path,
            output_dir=test_images_dir,
            debug=False,
            use_exiftool=False,
        )

        # Generate first 5 images for format verification
        success = generator.run(sample_size=5)
        assert success, "Image generation should succeed"

        # Get generated files
        all_images = list(test_images_dir.rglob("*.*"))

        format_checks = []
        for image_path in all_images:
            try:
                # Determine expected format from extension
                ext = image_path.suffix.lower().lstrip(".")
                if ext == "jpg" or ext == "jpeg":
                    expected_format = "JPEG"
                elif ext == "png":
                    expected_format = "PNG"
                elif ext == "tiff" or ext == "tif":
                    expected_format = "TIFF"
                elif ext == "heic":
                    expected_format = "JPEG"  # HEIC saved as JPEG
                else:
                    expected_format = "UNKNOWN"

                # Verify image if PIL is available
                if HAS_PIL and image_path.stat().st_size > 0:
                    try:
                        with Image.open(image_path) as img:
                            width, height = img.size
                            actual_format = img.format

                            format_checks.append(
                                {
                                    "file": image_path.name,
                                    "expected_format": expected_format,
                                    "actual_format": actual_format,
                                    "dimensions": f"{width}x{height}",
                                    "status": (
                                        "✅"
                                        if actual_format == expected_format
                                        else f"❌ Format mismatch"
                                    ),
                                }
                            )
                    except Exception as e:
                        format_checks.append(
                            {
                                "file": image_path.name,
                                "expected_format": expected_format,
                                "actual_format": "ERROR",
                                "dimensions": "unknown",
                                "status": f"❌ {str(e)[:30]}",
                            }
                        )
                else:
                    # Just verify file exists and has content (when PIL not available)
                    file_size = image_path.stat().st_size
                    format_checks.append(
                        {
                            "file": image_path.name,
                            "expected_format": expected_format,
                            "actual_format": "FILE" if file_size > 0 else "EMPTY",
                            "dimensions": f"size={file_size}",
                            "status": "✅" if file_size > 0 else "❌ Empty file",
                        }
                    )

            except Exception as e:
                format_checks.append(
                    {
                        "file": image_path.name,
                        "expected_format": "UNKNOWN",
                        "actual_format": "ERROR",
                        "dimensions": "unknown",
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
        assert len(format_checks) > 0, "Should have verified at least some images"

    def test_image_generation_and_organization_integration(self, csv_path, temp_dirs):
        """Integration test: Generate test images and organize them using ImageGenerator + PhotoOrganizer."""
        test_images_dir, organized_dir = temp_dirs

        print(f"\n🔧 Integration Test: ImageGenerator + PhotoOrganizer")
        print(f"📂 Source directory: {test_images_dir}")
        print(f"📂 Target directory: {organized_dir}")

        # Step 1: Generate test images using ImageGenerator
        print(f"\n📸 Step 1: Generating test images using ImageGenerator...")

        generator = ImageGenerator(
            csv_path=csv_path,
            output_dir=test_images_dir,
            debug=False,
            use_exiftool=False,  # Skip exiftool for faster testing
        )

        # Generate images
        success = generator.run()
        assert success, "Image generation should succeed"

        stats = generator.get_stats()
        print(
            f"✅ Generated {stats['generated']} test images, {stats['errors']} errors"
        )

        # Verify we generated some images
        assert stats["generated"] > 0, "Should have generated at least some images"
        source_files = list(test_images_dir.rglob("*.*"))
        assert len(source_files) > 0, "Should have created image files"

        # Step 2: Organize images using PhotoOrganizer
        print(f"\n🗂️  Step 2: Organizing images using PhotoOrganizer...")

        try:
            # Create organized directory
            organized_dir.mkdir(exist_ok=True)

            # Run the organize function with our test directories
            print(f"   Source: {test_images_dir}")
            print(f"   Target: {organized_dir}")

            # Create PhotoOrganizer instance and run it
            organizer = PhotoOrganizer(
                source=test_images_dir,
                target=organized_dir,
                dry_run=False,
                debug=False,  # Reduce noise in test output
            )

            organizer.run()

            print(f"✅ PhotoOrganizer completed")

        except Exception as e:
            print(f"❌ Error running PhotoOrganizer: {e}")
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
        organized_dirs = [d for d in organized_dir.rglob("*") if d.is_dir()]
        print(f"   Created {len(organized_dirs)} organized directories")

        # Should have created some directory structure
        assert (
            len(organized_dirs) >= 3
        ), f"Expected multiple organized directories, got {len(organized_dirs)}"

        # Verify that we organized a reasonable number of files
        organization_ratio = len(organized_files) / len(source_files)
        assert (
            organization_ratio >= 0.8
        ), f"Too few files organized: {len(organized_files)}/{len(source_files)}"

        print(f"🎉 Integration test completed successfully!")
        print(f"   Generated: {stats['generated']} images")
        print(f"   Organized: {len(organized_files)} files")
        print(f"   Directories: {len(organized_dirs)} created")
        print(f"   Organization ratio: {organization_ratio:.1%}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
