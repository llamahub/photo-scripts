"""
Tests for TakeoutProcessor class - Unit tests for Google Takeout processing logic.

These tests focus on testing the TakeoutProcessor class functionality including
ZIP extraction, sidecar file handling, and metadata processing.
"""

import tempfile
import zipfile
import json
from pathlib import Path
from unittest import mock
import pytest

# Try to import the TakeoutProcessor class
try:
    import sys

    # Add project src directory to path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root / "src"))

    from exif.takeout_processor import TakeoutProcessor

    HAS_TAKEOUT_PROCESSOR = True
except ImportError:
    HAS_TAKEOUT_PROCESSOR = False


# Skip all tests if TakeoutProcessor is not available
pytestmark = pytest.mark.skipif(
    not HAS_TAKEOUT_PROCESSOR, reason="TakeoutProcessor class not available for testing"
)


class TestTakeoutProcessor:
    """Test the TakeoutProcessor class directly."""

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
    def sample_zip(self, temp_dirs):
        """Create a sample ZIP file with images and sidecar files."""
        source_dir, target_dir = temp_dirs
        zip_path = source_dir / "test_takeout.zip"
        
        # Create a temporary structure for the ZIP
        with tempfile.TemporaryDirectory() as zip_temp:
            zip_temp_path = Path(zip_temp)
            
            # Create some test files
            (zip_temp_path / "Takeout").mkdir()
            (zip_temp_path / "Takeout" / "Google Photos").mkdir()
            photos_dir = zip_temp_path / "Takeout" / "Google Photos" / "Photos from 2024"
            photos_dir.mkdir(parents=True)
            
            # Create test image and sidecar
            test_image = photos_dir / "IMG_001.jpg"
            test_sidecar = photos_dir / "IMG_001.jpg.supplemental-metadata.json"
            test_image.write_text("fake image data")
            
            # Create realistic sidecar metadata
            metadata = {
                "title": "Test Image",
                "description": "A test image",
                "photoTakenTime": {
                    "timestamp": "1234567890",
                    "formatted": "Jan 1, 2024, 12:00:00 AM UTC"
                },
                "geoData": {
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "altitude": 0.0
                }
            }
            test_sidecar.write_text(json.dumps(metadata))
            
            # Create ZIP file
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                for file_path in zip_temp_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(zip_temp_path)
                        zip_ref.write(file_path, arcname)
        
        return zip_path, target_dir, metadata

    def test_init(self, temp_dirs):
        """Test TakeoutProcessor initialization."""
        source_dir, target_dir = temp_dirs
        zip_path = source_dir / "test.zip"
        zip_path.write_text("fake zip")
        
        processor = TakeoutProcessor(str(zip_path), str(target_dir))
        
        assert processor.source_zip == zip_path
        assert processor.target_dir == target_dir
        assert processor.create_subdir is False
        assert processor.stats["files_extracted"] == 0
        assert processor.stats["files_overwritten"] == 0

    def test_init_with_subdir(self, temp_dirs):
        """Test TakeoutProcessor initialization with subdirectory creation."""
        source_dir, target_dir = temp_dirs
        zip_path = source_dir / "test_takeout.zip"
        zip_path.write_text("fake zip")
        
        processor = TakeoutProcessor(str(zip_path), str(target_dir), create_subdir=True)
        
        assert processor.source_zip == zip_path
        assert processor.target_dir == target_dir / "test_takeout"
        assert processor.create_subdir is True

    def test_is_media_file(self, temp_dirs):
        """Test media file detection."""
        source_dir, target_dir = temp_dirs
        zip_path = source_dir / "test.zip"
        processor = TakeoutProcessor(str(zip_path), str(target_dir))
        
        # Test image files
        assert processor.is_media_file(Path("test.jpg")) is True
        assert processor.is_media_file(Path("test.JPG")) is True
        assert processor.is_media_file(Path("test.png")) is True
        assert processor.is_media_file(Path("test.heic")) is True
        
        # Test video files
        assert processor.is_media_file(Path("test.mp4")) is True
        assert processor.is_media_file(Path("test.mov")) is True
        
        # Test non-media files
        assert processor.is_media_file(Path("test.txt")) is False
        assert processor.is_media_file(Path("test.json")) is False

    def test_is_sidecar_file(self, temp_dirs):
        """Test sidecar file detection."""
        source_dir, target_dir = temp_dirs
        zip_path = source_dir / "test.zip"
        processor = TakeoutProcessor(str(zip_path), str(target_dir))
        
        # Test Google Takeout sidecar files
        assert processor.is_sidecar_file(Path("test.jpg.supplemental-metadata.json")) is True
        assert processor.is_sidecar_file(Path("test.json")) is True
        assert processor.is_sidecar_file(Path("test.JSON")) is True
        
        # Test non-sidecar files
        assert processor.is_sidecar_file(Path("test.jpg")) is False
        assert processor.is_sidecar_file(Path("test.txt")) is False
        assert processor.is_sidecar_file(Path("test.xmp")) is False

    def test_extract_zip_contents(self, sample_zip):
        """Test ZIP file extraction."""
        zip_path, target_dir, _ = sample_zip
        processor = TakeoutProcessor(str(zip_path), str(target_dir))
        
        # Mock logger
        processor.logger = mock.Mock()
        
        extracted_files = processor.extract_zip_contents()
        
        assert len(extracted_files) == 2  # Image + sidecar
        assert "Takeout/Google Photos/Photos from 2024/IMG_001.jpg" in extracted_files
        sidecar_key = "Takeout/Google Photos/Photos from 2024/IMG_001.jpg.supplemental-metadata.json"
        assert sidecar_key in extracted_files
        
        # Check files were actually extracted
        image_path = extracted_files["Takeout/Google Photos/Photos from 2024/IMG_001.jpg"]
        sidecar_path = extracted_files[sidecar_key]
        
        assert image_path.exists()
        assert sidecar_path.exists()
        assert processor.stats["files_extracted"] == 2

    def test_extract_zip_contents_with_overwrite(self, sample_zip):
        """Test ZIP file extraction with existing files (overwrite scenario)."""
        zip_path, target_dir, _ = sample_zip
        processor = TakeoutProcessor(str(zip_path), str(target_dir))
        
        # Mock logger
        processor.logger = mock.Mock()
        
        # Pre-create the target file to simulate overwrite
        existing_file = target_dir / "Takeout" / "Google Photos" / "Photos from 2024" / "IMG_001.jpg"
        existing_file.parent.mkdir(parents=True)
        existing_file.write_text("existing content")
        
        # Extract files first
        _ = processor.extract_zip_contents()
        
        assert processor.stats["files_overwritten"] == 1
        processor.logger.warning.assert_called()

    def test_parse_sidecar_metadata(self, sample_zip):
        """Test parsing sidecar metadata."""
        zip_path, target_dir, expected_metadata = sample_zip
        processor = TakeoutProcessor(str(zip_path), str(target_dir))
        
        # Mock logger
        processor.logger = mock.Mock()
        
        # Extract files first
        extracted_files = processor.extract_zip_contents()
        sidecar_key = "Takeout/Google Photos/Photos from 2024/IMG_001.jpg.supplemental-metadata.json"
        sidecar_path = extracted_files[sidecar_key]
        
        metadata = processor.parse_sidecar_metadata(sidecar_path)
        
        assert metadata is not None
        assert metadata["title"] == expected_metadata["title"]
        assert metadata["photoTakenTime"]["timestamp"] == expected_metadata["photoTakenTime"]["timestamp"]

    def test_parse_sidecar_metadata_invalid_json(self, temp_dirs):
        """Test parsing invalid sidecar metadata."""
        source_dir, target_dir = temp_dirs
        processor = TakeoutProcessor(str(source_dir / "test.zip"), str(target_dir))
        
        # Mock logger
        processor.logger = mock.Mock()
        
        # Create invalid JSON file
        invalid_json = target_dir / "invalid.json"
        invalid_json.write_text("{invalid json content")
        
        metadata = processor.parse_sidecar_metadata(invalid_json)
        
        assert metadata is None
        assert processor.stats["errors"] == 1
        processor.logger.error.assert_called()

    def test_find_sidecar_for_media(self, sample_zip):
        """Test finding sidecar files for media files."""
        zip_path, target_dir, _ = sample_zip
        processor = TakeoutProcessor(str(zip_path), str(target_dir))
        
        # Mock logger
        processor.logger = mock.Mock()
        
        # Extract files first
        extracted_files = processor.extract_zip_contents()
        media_file = extracted_files["Takeout/Google Photos/Photos from 2024/IMG_001.jpg"]
        
        sidecar = processor.find_sidecar_for_media(media_file, extracted_files)
        
        assert sidecar is not None
        assert sidecar.name == "IMG_001.jpg.supplemental-metadata.json"

    def test_find_sidecar_for_media_no_sidecar(self, temp_dirs):
        """Test finding sidecar when none exists."""
        source_dir, target_dir = temp_dirs
        processor = TakeoutProcessor(str(source_dir / "test.zip"), str(target_dir))
        
        # Mock logger
        processor.logger = mock.Mock()
        
        # Create media file without sidecar
        media_file = target_dir / "test.jpg"
        media_file.write_text("fake image")
        
        extracted_files = {"test.jpg": media_file}
        sidecar = processor.find_sidecar_for_media(media_file, extracted_files)
        
        assert sidecar is None

    @mock.patch('exif.takeout_processor.TakeoutProcessor.update_media_metadata')
    def test_process_takeout(self, mock_update_metadata, sample_zip):
        """Test full takeout processing."""
        zip_path, target_dir, _ = sample_zip
        processor = TakeoutProcessor(str(zip_path), str(target_dir))
        
        # Mock logger
        processor.logger = mock.Mock()
        mock_update_metadata.return_value = True
        
        processor.process_takeout()
        
        assert processor.stats["images_processed"] == 1
        assert processor.stats["sidecar_files_found"] == 1
        mock_update_metadata.assert_called_once()

    def test_print_summary(self, temp_dirs):
        """Test printing processing summary."""
        source_dir, target_dir = temp_dirs
        processor = TakeoutProcessor(str(source_dir / "test.zip"), str(target_dir))
        
        # Mock logger
        processor.logger = mock.Mock()
        
        # Set some test statistics
        processor.stats.update({
            "files_extracted": 100,
            "files_overwritten": 5,
            "images_processed": 80,
            "videos_processed": 15,
            "sidecar_files_found": 25,
            "metadata_updates": 20,
            "errors": 2
        })
        
        processor.print_summary()
        
        # Verify logger was called with expected content
        processor.logger.info.assert_called()
        calls = [call.args[0] for call in processor.logger.info.call_args_list]
        
        assert any("Files extracted: 100" in call for call in calls)
        assert any("Files overwritten: 5" in call for call in calls)
        assert any("Images processed: 80" in call for call in calls)
        assert any("Videos processed: 15" in call for call in calls)
        assert any("Sidecar files found: 25" in call for call in calls)
        assert any("Metadata updates applied: 20" in call for call in calls)
        
        # Check that warning was called for errors
        processor.logger.warning.assert_called_with("Errors encountered: 2")

    def test_file_extensions_fallback(self, temp_dirs):
        """Test file extension handling when FileManager is not available."""
        source_dir, target_dir = temp_dirs
        
        # Mock FileManager as None to test fallback
        with mock.patch('exif.takeout_processor.FileManager', None):
            processor = TakeoutProcessor(str(source_dir / "test.zip"), str(target_dir))
            
            # Test that fallback extensions work
            assert ".jpg" in processor.image_extensions
            assert ".mp4" in processor.video_extensions
            assert processor.is_media_file(Path("test.jpg")) is True
            assert processor.is_media_file(Path("test.mp4")) is True