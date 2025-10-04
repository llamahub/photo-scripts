"""
Tests for ImageGenerator class - Direct unit tests for test image generation logic.

These tests focus on testing the ImageGenerator class directly without going through
the script interface, allowing for more focused and faster unit testing.
"""

import pytest
import tempfile
import csv
from pathlib import Path
from datetime import datetime
from unittest import mock

# Try to import the ImageGenerator class
try:
    import sys
    from pathlib import Path as PathLib

    # Add project src directory to path
    project_root = PathLib(__file__).parent.parent
    sys.path.insert(0, str(project_root / "src"))

    from exif import ImageGenerator

    HAS_IMAGE_GENERATOR = True
except ImportError:
    HAS_IMAGE_GENERATOR = False

# Check for PIL availability
try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# Skip all tests if ImageGenerator is not available
pytestmark = pytest.mark.skipif(
    not HAS_IMAGE_GENERATOR, reason="ImageGenerator class not available for testing"
)


class TestImageGenerator:
    """Test the ImageGenerator class directly."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            csv_dir = temp_path / "csv"
            output_dir = temp_path / "output"
            csv_dir.mkdir()
            output_dir.mkdir()
            yield csv_dir, output_dir

    @pytest.fixture
    def sample_csv_data(self):
        """Sample CSV data for testing."""
        return [
            {
                "Root Path": "photos",
                "Parent Folder": "vacation",
                "Filename": "beach_sunset",
                "Source Ext": "jpg",
                "Image Width": "1920",
                "Image Height": "1080",
                "Actual Format": "JPEG",
                "DateTimeOriginal": "2023:07:15 18:30:00",
                "ExifIFD:DateTimeOriginal": "2023:07:15 18:30:00",
                "XMP-photoshop:DateCreated": "2023-07-15",
            },
            {
                "Root Path": "photos",
                "Parent Folder": "family",
                "Filename": "birthday_party",
                "Source Ext": "png",
                "Image Width": "800",
                "Image Height": "600",
                "Actual Format": "PNG",
                "DateTimeOriginal": "2023:08:20 15:45:00",
                "ExifIFD:DateTimeOriginal": "",
                "XMP-photoshop:DateCreated": "2023-08-20",
            },
            {
                "Root Path": "photos",
                "Parent Folder": "pets",
                "Filename": "dog_playing",
                "Source Ext": "tiff",
                "Image Width": "1024",
                "Image Height": "768",
                "Actual Format": "TIFF",
                "DateTimeOriginal": "",
                "ExifIFD:DateTimeOriginal": "",
                "XMP-photoshop:DateCreated": "",
            },
        ]

    @pytest.fixture
    def sample_csv_file(self, temp_dirs, sample_csv_data):
        """Create a sample CSV file for testing."""
        csv_dir, _ = temp_dirs
        csv_file = csv_dir / "test_images.csv"

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            if sample_csv_data:
                writer = csv.DictWriter(f, fieldnames=sample_csv_data[0].keys())
                writer.writeheader()
                writer.writerows(sample_csv_data)

        return csv_file

    def test_init(self, sample_csv_file, temp_dirs):
        """Test ImageGenerator initialization."""
        _, output_dir = temp_dirs

        generator = ImageGenerator(
            csv_path=sample_csv_file,
            output_dir=output_dir,
            debug=True,
            use_exiftool=False,
        )

        assert generator.csv_path == sample_csv_file
        assert generator.output_dir == output_dir
        assert generator.debug is True
        assert generator.use_exiftool is False
        assert generator.stats["generated"] == 0
        assert generator.stats["errors"] == 0

    def test_init_nonexistent_csv(self, temp_dirs):
        """Test initialization with nonexistent CSV file."""
        _, output_dir = temp_dirs
        nonexistent_csv = output_dir / "nonexistent.csv"

        with pytest.raises(FileNotFoundError, match="CSV file not found"):
            ImageGenerator(csv_path=nonexistent_csv, output_dir=output_dir)

    def test_load_csv_data(self, sample_csv_file, temp_dirs, sample_csv_data):
        """Test loading CSV data."""
        _, output_dir = temp_dirs

        generator = ImageGenerator(sample_csv_file, output_dir)
        data = generator.load_csv_data()

        assert len(data) == len(sample_csv_data)
        assert generator.stats["total_rows"] == len(sample_csv_data)

        # Check first row data
        assert data[0]["Filename"] == "beach_sunset"
        assert data[0]["Source Ext"] == "jpg"
        assert data[0]["Actual Format"] == "JPEG"

    def test_parse_date_string(self, sample_csv_file, temp_dirs):
        """Test date string parsing."""
        _, output_dir = temp_dirs
        generator = ImageGenerator(sample_csv_file, output_dir)

        # Test EXIF format
        date1 = generator.parse_date_string("2023:07:15 18:30:00")
        assert date1 == datetime(2023, 7, 15, 18, 30, 0)

        # Test M/D/YY format
        date2 = generator.parse_date_string("7/15/23 18:30")
        assert date2 == datetime(2023, 7, 15, 18, 30, 0)

        # Test M/D/YY format without time
        date3 = generator.parse_date_string("7/15/23")
        assert date3 == datetime(2023, 7, 15, 0, 0, 0)

        # Test empty string
        assert generator.parse_date_string("") is None
        assert generator.parse_date_string("   ") is None

        # Test invalid format
        assert generator.parse_date_string("invalid-date") is None

    def test_create_test_image_with_pil(self, sample_csv_file, temp_dirs):
        """Test image creation with PIL (if available)."""
        _, output_dir = temp_dirs
        generator = ImageGenerator(sample_csv_file, output_dir)

        image_path = output_dir / "test_image.jpg"

        success = generator.create_test_image(800, 600, "JPEG", image_path)

        assert success is True
        assert image_path.exists()
        assert image_path.stat().st_size > 0

        if HAS_PIL:
            # Verify image properties
            with Image.open(image_path) as img:
                assert img.width == 800
                assert img.height == 600
                assert img.format == "JPEG"

    def test_create_test_image_heic_fallback(self, sample_csv_file, temp_dirs):
        """Test HEIC format fallback to JPEG."""
        _, output_dir = temp_dirs
        generator = ImageGenerator(sample_csv_file, output_dir)

        image_path = output_dir / "test_image.heic"

        success = generator.create_test_image(400, 300, "HEIC", image_path)

        assert success is True
        assert image_path.exists()
        assert image_path.stat().st_size > 0

    def test_create_test_image_invalid_dimensions(self, sample_csv_file, temp_dirs):
        """Test image creation with invalid dimensions."""
        _, output_dir = temp_dirs
        generator = ImageGenerator(sample_csv_file, output_dir)

        image_path = output_dir / "test_image.jpg"

        # Test zero dimensions (should be corrected to 1x1)
        success = generator.create_test_image(0, 0, "JPEG", image_path)

        assert success is True
        assert image_path.exists()

    def test_create_test_image_nested_directory(self, sample_csv_file, temp_dirs):
        """Test image creation in nested directory structure."""
        _, output_dir = temp_dirs
        generator = ImageGenerator(sample_csv_file, output_dir)

        nested_path = output_dir / "level1" / "level2" / "level3" / "test_image.png"

        success = generator.create_test_image(200, 150, "PNG", nested_path)

        assert success is True
        assert nested_path.exists()
        assert nested_path.parent.exists()

    @mock.patch("shutil.which")
    def test_set_exif_data_no_exiftool(
        self, mock_which, sample_csv_file, temp_dirs, sample_csv_data
    ):
        """Test EXIF setting when exiftool is not available."""
        mock_which.return_value = None  # Simulate exiftool not found

        _, output_dir = temp_dirs
        generator = ImageGenerator(sample_csv_file, output_dir, use_exiftool=True)

        # use_exiftool should be False because exiftool is not available
        assert generator.use_exiftool is False

        image_path = output_dir / "test.jpg"
        image_path.write_text("fake image")

        result = generator.set_exif_data(image_path, sample_csv_data[0])
        assert result is False

    @mock.patch("subprocess.run")
    @mock.patch("shutil.which")
    def test_set_exif_data_success(
        self, mock_which, mock_run, sample_csv_file, temp_dirs, sample_csv_data
    ):
        """Test successful EXIF data setting."""
        mock_which.return_value = "/usr/bin/exiftool"  # Simulate exiftool available
        mock_run.return_value.returncode = 0
        mock_run.return_value.stderr = ""

        _, output_dir = temp_dirs
        generator = ImageGenerator(sample_csv_file, output_dir, use_exiftool=True)

        image_path = output_dir / "test.jpg"
        image_path.write_text("fake image")

        result = generator.set_exif_data(image_path, sample_csv_data[0])

        assert result is True
        mock_run.assert_called_once()

        # Check that exiftool was called with correct arguments
        call_args = mock_run.call_args[0][0]  # First positional argument
        assert "exiftool" in call_args
        assert "-overwrite_original" in call_args
        assert any("DateTimeOriginal=2023:07:15 18:30:00" in arg for arg in call_args)

    def test_generate_image_from_row(self, sample_csv_file, temp_dirs, sample_csv_data):
        """Test generating a single image from CSV row."""
        _, output_dir = temp_dirs
        generator = ImageGenerator(sample_csv_file, output_dir, use_exiftool=False)

        row = sample_csv_data[0]
        success = generator.generate_image_from_row(row)

        assert success is True

        # Check that image was created in correct location
        expected_path = output_dir / "photos" / "vacation" / "beach_sunset.jpg"
        assert expected_path.exists()
        assert expected_path.stat().st_size > 0

        # Check statistics
        assert generator.stats["formats"]["JPEG"] == 1

    def test_generate_image_from_row_missing_filename(self, sample_csv_file, temp_dirs):
        """Test generating image with missing filename."""
        _, output_dir = temp_dirs
        generator = ImageGenerator(sample_csv_file, output_dir)

        row = {"Root Path": "test", "Parent Folder": "folder"}  # No filename
        success = generator.generate_image_from_row(row)

        assert success is False

    def test_generate_images_sample(self, sample_csv_file, temp_dirs, sample_csv_data):
        """Test generating a sample of images."""
        _, output_dir = temp_dirs
        generator = ImageGenerator(sample_csv_file, output_dir, use_exiftool=False)

        success = generator.generate_images(sample_size=2)

        assert success is True
        assert generator.stats["generated"] == 2
        assert generator.stats["errors"] == 0

        # Check that only 2 images were created
        all_images = list(output_dir.rglob("*.*"))
        assert len(all_images) == 2

    def test_generate_images_limit(self, sample_csv_file, temp_dirs, sample_csv_data):
        """Test generating images with limit."""
        _, output_dir = temp_dirs
        generator = ImageGenerator(sample_csv_file, output_dir, use_exiftool=False)

        success = generator.generate_images(limit=1)

        assert success is True
        assert generator.stats["generated"] == 1
        assert generator.stats["errors"] == 0

    def test_generate_images_all(self, sample_csv_file, temp_dirs, sample_csv_data):
        """Test generating all images."""
        _, output_dir = temp_dirs
        generator = ImageGenerator(sample_csv_file, output_dir, use_exiftool=False)

        success = generator.generate_images()

        assert success is True
        assert generator.stats["generated"] == len(sample_csv_data)
        assert generator.stats["errors"] == 0

        # Check that all images were created
        all_images = list(output_dir.rglob("*.*"))
        assert len(all_images) == len(sample_csv_data)

    def test_get_stats(self, sample_csv_file, temp_dirs):
        """Test getting statistics."""
        _, output_dir = temp_dirs
        generator = ImageGenerator(sample_csv_file, output_dir)

        # Modify stats
        generator.stats["generated"] = 5
        generator.stats["errors"] = 1
        generator.stats["exif_set"] = 3

        stats = generator.get_stats()

        assert stats == {
            "total_rows": 0,
            "generated": 5,
            "errors": 1,
            "exif_set": 3,
            "formats": {},
        }

        # Verify it's a copy (modifying returned stats shouldn't affect generator)
        stats["generated"] = 100
        assert generator.stats["generated"] == 5

    def test_run(self, sample_csv_file, temp_dirs, sample_csv_data):
        """Test the main run method."""
        _, output_dir = temp_dirs
        generator = ImageGenerator(sample_csv_file, output_dir, use_exiftool=False)

        success = generator.run(sample_size=2)

        assert success is True
        assert generator.stats["generated"] == 2

        # Verify images were created
        all_images = list(output_dir.rglob("*.*"))
        assert len(all_images) == 2

    def test_run_empty_csv(self, temp_dirs):
        """Test run with empty CSV file."""
        csv_dir, output_dir = temp_dirs
        empty_csv = csv_dir / "empty.csv"

        # Create empty CSV with headers only
        with open(empty_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Root Path", "Parent Folder", "Filename"])

        generator = ImageGenerator(empty_csv, output_dir)
        success = generator.run()

        # Should fail when no data is available
        assert success is False  # Empty file should be considered a failure
        assert generator.stats["generated"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
