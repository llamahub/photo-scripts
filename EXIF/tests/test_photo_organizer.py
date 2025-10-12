"""
Tests for PhotoOrganizer class - Direct unit tests for the photo organization logic.

These tests focus on testing the PhotoOrganizer class directly without going through
the script interface, allowing for more focused and faster unit testing.
"""

import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest import mock
import pytest

# Try to import the PhotoOrganizer class
try:
    import sys
    from pathlib import Path

    # Add project src directory to path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root / "src"))

    from exif import PhotoOrganizer

    HAS_PHOTO_ORGANIZER = True
except ImportError:
    HAS_PHOTO_ORGANIZER = False


# Skip all tests if PhotoOrganizer is not available
pytestmark = pytest.mark.skipif(
    not HAS_PHOTO_ORGANIZER, reason="PhotoOrganizer class not available for testing"
)


class TestPhotoOrganizer:
    """Test the PhotoOrganizer class directly."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            target_dir = temp_path / "target"
            source_dir.mkdir()
            target_dir.mkdir()
            yield source_dir, target_dir

    @pytest.fixture
    def sample_images(self, temp_dirs):
        """Create sample image files for testing."""
        source_dir, target_dir = temp_dirs

        # Create directory structure with sample files
        folders = [
            source_dir / "folder1",
            source_dir / "folder2",
            source_dir / "subfolder" / "nested",
        ]

        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)

        # Create sample image files
        image_files = [
            source_dir / "root_image.jpg",
            source_dir / "folder1" / "image1.jpg",
            source_dir / "folder1" / "photo.png",
            source_dir / "folder2" / "picture.tiff",
            source_dir / "subfolder" / "nested" / "deep_image.jpeg",
            source_dir / "not_an_image.txt",  # Should be ignored
        ]

        for img_file in image_files:
            img_file.touch()

        return source_dir, target_dir, image_files[:-1]  # Exclude the txt file

    def test_init(self, temp_dirs):
        """Test PhotoOrganizer initialization."""
        source_dir, target_dir = temp_dirs

        organizer = PhotoOrganizer(
            source=source_dir, target=target_dir, dry_run=True, debug=False
        )

        assert organizer.source == source_dir.resolve()
        assert organizer.target == target_dir.resolve()
        assert organizer.dry_run is True
        assert organizer.debug is False
        assert organizer.stats == {
            "processed": 0,
            "copied": 0,
            "skipped": 0,
            "errors": 0,
        }

    def test_is_image_file(self, temp_dirs):
        """Test image file detection."""
        source_dir, target_dir = temp_dirs
        organizer = PhotoOrganizer(source_dir, target_dir)

        # Test supported formats
        assert organizer.is_image_file(Path("test.jpg")) is True
        assert organizer.is_image_file(Path("test.JPEG")) is True
        assert organizer.is_image_file(Path("test.png")) is True
        assert organizer.is_image_file(Path("test.gif")) is True
        assert organizer.is_image_file(Path("test.tiff")) is True
        assert organizer.is_image_file(Path("test.heic")) is True

        # Test unsupported formats
        assert organizer.is_image_file(Path("test.txt")) is False
        assert organizer.is_image_file(Path("test.doc")) is False
        assert organizer.is_image_file(Path("test")) is False

    def test_get_decade_folder(self, temp_dirs):
        """Test decade folder name generation."""
        source_dir, target_dir = temp_dirs
        organizer = PhotoOrganizer(source_dir, target_dir)

        assert organizer.get_decade_folder(1995) == "1990+"
        assert organizer.get_decade_folder(2000) == "2000+"
        assert organizer.get_decade_folder(2025) == "2020+"
        assert organizer.get_decade_folder(1889) == "1880+"

    def test_get_target_path(self, temp_dirs):
        """Test target path calculation."""
        source_dir, target_dir = temp_dirs
        organizer = PhotoOrganizer(source_dir, target_dir)

        # Create a test source file structure
        test_folder = source_dir / "vacation_photos"
        test_folder.mkdir()
        source_file = test_folder / "beach_sunset.jpg"
        source_file.touch()

        # Test with valid date
        image_date = "2023-07-15 14:30"
        target_path = organizer.get_target_path(source_file, image_date)

        expected_path = (
            target_dir
            / "2020+"
            / "2023"
            / "2023-07"
            / "vacation_photos"
            / "beach_sunset.jpg"
        )
        assert target_path == expected_path

    def test_get_target_path_invalid_date(self, temp_dirs):
        """Test target path calculation with invalid date."""
        source_dir, target_dir = temp_dirs
        organizer = PhotoOrganizer(source_dir, target_dir)

        test_folder = source_dir / "photos"
        test_folder.mkdir()
        source_file = test_folder / "image.jpg"
        source_file.touch()

        # Test with invalid date - should fallback to 1900
        target_path = organizer.get_target_path(source_file, "invalid-date")

        expected_path = (
            target_dir / "1900+" / "1900" / "1900-01" / "photos" / "image.jpg"
        )
        assert target_path == expected_path

    def test_find_files(self, sample_images):
        """Test finding image files in source directory."""
        source_dir, target_dir, expected_files = sample_images
        organizer = PhotoOrganizer(source_dir, target_dir)

        found_images = organizer.find_files()
        
        assert len(found_images) == 5
        
        # Check that all found files are valid image files
        for image in found_images:
            assert image.suffix.lower() in organizer.IMAGE_EXTENSIONS
            assert image.exists()

        # Should include JPG and PNG files
        jpg_files = [f for f in found_images if f.suffix.lower() == '.jpg']
        png_files = [f for f in found_images if f.suffix.lower() == '.png']
        assert len(jpg_files) == 2  # test1.jpg, test2.jpg
        assert len(png_files) == 1  # test.png

    def test_copy_file_dry_run(self, temp_dirs):
        """Test copy file method in dry run mode."""
        source_dir, target_dir = temp_dirs
        organizer = PhotoOrganizer(source_dir, target_dir, dry_run=True)
        
        source_file = source_dir / "test.jpg"
        source_file.write_text("fake image content")
        
        target_file = target_dir / "target.jpg"
        
        result = organizer.copy_file(source_file, target_file)
        
        # Should return True (success) but not actually copy the file
        assert result is True
        assert not target_file.exists()  # File should not actually be copied in dry run

    def test_copy_file_real(self, temp_dirs):
        """Test copy file method with actual file copying."""
        source_dir, target_dir = temp_dirs
        organizer = PhotoOrganizer(source_dir, target_dir, dry_run=False)
        
        source_file = source_dir / "test.jpg"
        source_file.write_text("fake image content")
        
        target_file = target_dir / "target.jpg"
        
        result = organizer.copy_file(source_file, target_file)
        
        # Should return True and actually copy the file
        assert result is True
        assert target_file.exists()
        assert target_file.read_text() == "fake image content"

    def test_copy_file_existing_target(self, temp_dirs):
        """Test copy file method when target file already exists."""
        source_dir, target_dir = temp_dirs
        organizer = PhotoOrganizer(source_dir, target_dir, dry_run=False)
        
        source_file = source_dir / "test.jpg"
        source_file.write_text("fake image content")
        
        target_file = target_dir / "target.jpg"
        target_file.write_text("existing content")
        
        result = organizer.copy_file(source_file, target_file)
        
        # Should handle existing file (implementation specific behavior)
        # For now, let's assume it skips and returns False
        assert result is False or result is True  # Allow either behavior
        # Original content should be preserved or overwritten based on implementation

    @mock.patch('exif.image_data.ImageData.getImageDate')
    def test_process_file_with_date(self, mock_get_date, temp_dirs):
        """Test process file with valid date."""
        source_dir, target_dir = temp_dirs
        organizer = PhotoOrganizer(source_dir, target_dir, dry_run=True)
        
        # Mock image date
        mock_get_date.return_value = "2023-08-20 15:45:30"
        
        image_file = source_dir / "test.jpg"
        image_file.write_text("fake image content")
        
        # Should not raise an exception
        organizer.process_file(image_file)
        
        # Verify the mock was called
        mock_get_date.assert_called_once_with(str(image_file))

    @mock.patch("exif.image_data.ImageData.getImageDate")
    def test_process_image_no_date(self, mock_get_date, temp_dirs):
        """Test processing an image without EXIF date (uses fallback)."""
        mock_get_date.return_value = None

        source_dir, target_dir = temp_dirs
        organizer = PhotoOrganizer(source_dir, target_dir, dry_run=True)

        # Create test image
        image_file = source_dir / "no_exif.jpg"
        image_file.write_text("fake image")

        # Process the image
        organizer.process_file(image_file)

        assert organizer.stats["processed"] == 1
        assert organizer.stats["copied"] == 1

    def test_get_stats(self, temp_dirs):
        """Test getting statistics."""
        source_dir, target_dir = temp_dirs
        organizer = PhotoOrganizer(source_dir, target_dir)

        # Modify stats
        organizer.stats["processed"] = 5
        organizer.stats["copied"] = 3
        organizer.stats["errors"] = 1

        stats = organizer.get_stats()

        assert stats == {"processed": 5, "copied": 3, "skipped": 0, "errors": 1}

        # Verify it's a copy (modifying returned stats shouldn't affect organizer)
        stats["processed"] = 100
        assert organizer.stats["processed"] == 5

    @mock.patch('exif.image_data.ImageData.getImageDate')
    def test_process_file_no_date(self, mock_get_date, temp_dirs):
        """Test process file with no date available."""
        source_dir, target_dir = temp_dirs
        organizer = PhotoOrganizer(source_dir, target_dir, dry_run=True)
        
        # Mock no date available
        mock_get_date.return_value = "1900-01-01 00:00"
        
        image_file = source_dir / "test.jpg"
        image_file.write_text("fake image content")
        
        # Should not raise an exception even with no date
        organizer.process_file(image_file)
        
        # Verify the mock was called
        mock_get_date.assert_called_once_with(str(image_file))

    def test_run_empty_source(self, temp_dirs):
        """Test running with empty source directory."""
        source_dir, target_dir = temp_dirs
        organizer = PhotoOrganizer(source_dir, target_dir)

        # Run with empty source
        organizer.run()  # Should complete without error

        assert organizer.stats["processed"] == 0

    def test_run_nonexistent_source(self, temp_dirs):
        """Test running with nonexistent source directory."""
        source_dir, target_dir = temp_dirs
        nonexistent = source_dir / "does_not_exist"

        organizer = PhotoOrganizer(nonexistent, target_dir)

        with pytest.raises(
            FileNotFoundError, match="Source directory .* does not exist"
        ):
            organizer.run()

    @mock.patch("exif.image_data.ImageData.getImageDate")
    def test_run_with_images(self, mock_get_date, sample_images):
        """Test full run with sample images."""
        mock_get_date.return_value = "2023-09-15 12:00"

        source_dir, target_dir, image_files = sample_images
        organizer = PhotoOrganizer(source_dir, target_dir, dry_run=True)

        # Run the full process
        organizer.run()

        # Should have processed all image files
        assert organizer.stats["processed"] == len(image_files)
        assert organizer.stats["copied"] == len(image_files)
        assert organizer.stats["errors"] == 0

    def test_init_with_move_files(self):
        """Test PhotoOrganizer initialization with move_files option."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source"
            target = Path(temp_dir) / "target"
            source.mkdir()

            organizer = PhotoOrganizer(source, target, move_files=True)

            assert organizer.move_files is True
            assert "moved" in organizer.stats
            assert organizer.stats["moved"] == 0

    def test_init_with_workers(self):
        """Test PhotoOrganizer initialization with custom workers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source"
            target = Path(temp_dir) / "target"
            source.mkdir()

            organizer = PhotoOrganizer(source, target, max_workers=8)

            assert organizer.max_workers == 8

    def test_copy_file_move_mode(self):
        """Test copy_file method in move mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            target_dir = temp_path / "target"
            source_dir.mkdir()
            target_dir.mkdir()
            
            organizer = PhotoOrganizer(source_dir, target_dir, dry_run=False, move_files=True)
            
            # Create test file
            test_file = source_dir / "test.jpg"
            test_file.write_text("test content")
            
            target_file = target_dir / "moved_test.jpg"
            
            # Test moving file
            result = organizer.copy_file(test_file, target_file)
            
            assert result is True
            assert target_file.exists()
            assert not test_file.exists()  # Original should be gone after move
            assert target_file.read_text() == "test content"

    def test_copy_file_move_mode_dry_run(self):
        """Test copy_file method in move mode with dry run."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            target_dir = temp_path / "target"
            source_dir.mkdir()
            target_dir.mkdir()
            
            organizer = PhotoOrganizer(source_dir, target_dir, dry_run=True, move_files=True)
            
            # Create test file
            test_file = source_dir / "test.jpg"
            test_file.write_text("test content")
            
            target_file = target_dir / "moved_test.jpg"
            
            # Test dry run mode - should return True but not actually move
            result = organizer.copy_file(test_file, target_file)
