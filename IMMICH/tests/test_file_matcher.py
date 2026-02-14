"""Tests for file_matcher module."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from file_matcher import ExifReader, FileMatcher
from datetime import datetime


class TestExifReader:
    """Tests for ExifReader class."""
    
    @patch('file_matcher.subprocess.run')
    def test_read_exif_success(self, mock_run):
        """Test successful EXIF reading."""
        mock_result = Mock()
        mock_result.stdout = json.dumps([{
            "DateTimeOriginal": "2025:06:15 18:30:00",
            "FileSize": "2048000"
        }])
        mock_run.return_value = mock_result
        
        exif_data = ExifReader.read_exif("/path/to/photo.jpg")
        
        assert exif_data["DateTimeOriginal"] == "2025:06:15 18:30:00"
        assert exif_data["FileSize"] == "2048000"
    
    @patch('file_matcher.subprocess.run')
    def test_read_exif_no_data(self, mock_run):
        """Test EXIF reading with no data."""
        mock_result = Mock()
        mock_result.stdout = "[]"
        mock_run.return_value = mock_result
        
        exif_data = ExifReader.read_exif("/path/to/photo.jpg")
        
        assert exif_data == {}
    
    @patch('file_matcher.subprocess.run')
    def test_read_exif_error(self, mock_run):
        """Test EXIF reading with error."""
        mock_run.side_effect = FileNotFoundError()
        
        exif_data = ExifReader.read_exif("/path/to/photo.jpg")
        
        assert exif_data == {}
    
    def test_parse_exif_datetime_colon_format(self):
        """Test parsing EXIF datetime with colons."""
        dt = ExifReader.parse_exif_datetime("2025:06:15 18:30:00")
        
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 6
        assert dt.day == 15
        assert dt.hour == 18
        assert dt.minute == 30
    
    def test_parse_exif_datetime_iso_format(self):
        """Test parsing ISO format datetime."""
        dt = ExifReader.parse_exif_datetime("2025-06-15T18:30:00Z")
        
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 6
        assert dt.day == 15
    
    def test_parse_exif_datetime_invalid(self):
        """Test parsing invalid datetime."""
        dt = ExifReader.parse_exif_datetime("invalid")
        
        assert dt is None
    
    def test_parse_exif_datetime_none(self):
        """Test parsing None datetime."""
        dt = ExifReader.parse_exif_datetime(None)
        
        assert dt is None


@pytest.fixture
def temp_target_dir():
    """Create a temporary target directory with test images."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir)
        
        # Create subdirectories
        (target / "2025" / "06").mkdir(parents=True)
        (target / "2025" / "07").mkdir(parents=True)
        
        # Create test files
        (target / "2025" / "06" / "IMG_001.jpg").touch()
        (target / "2025" / "06" / "IMG_002.jpg").touch()
        (target / "2025" / "07" / "IMG_001.jpg").touch()  # Duplicate filename
        (target / "2025" / "07" / "IMG_003.png").touch()
        
        yield target


class TestFileMatcher:
    """Tests for FileMatcher class."""
    
    def test_init(self, temp_target_dir):
        """Test initialization."""
        matcher = FileMatcher(str(temp_target_dir))
        
        assert matcher.target_path == temp_target_dir
        assert len(matcher.filename_index) > 0
    
    def test_build_filename_index(self, temp_target_dir):
        """Test building filename index."""
        matcher = FileMatcher(str(temp_target_dir))
        
        # Check that files are indexed
        assert "IMG_001.jpg" in matcher.filename_index
        assert "IMG_002.jpg" in matcher.filename_index
        assert "IMG_003.png" in matcher.filename_index
        
        # Check duplicate filenames
        assert len(matcher.filename_index["IMG_001.jpg"]) == 2
    
    def test_match_asset_unique_filename(self, temp_target_dir):
        """Test matching asset with unique filename."""
        matcher = FileMatcher(str(temp_target_dir))
        
        asset = {
            "originalFileName": "IMG_002.jpg"
        }
        
        path, confidence, method = matcher.match_asset(asset)
        
        assert path is not None
        assert "IMG_002.jpg" in path
        assert confidence == "exact"
        assert method == "unique_filename"
    
    def test_match_asset_no_filename(self, temp_target_dir):
        """Test matching asset without filename."""
        matcher = FileMatcher(str(temp_target_dir))
        
        asset = {}
        
        path, confidence, method = matcher.match_asset(asset)
        
        assert path is None
        assert confidence == "none"
        assert method == "no_filename"
    
    def test_match_asset_not_found(self, temp_target_dir):
        """Test matching asset with non-existent filename."""
        matcher = FileMatcher(str(temp_target_dir))
        
        asset = {
            "originalFileName": "nonexistent.jpg"
        }
        
        path, confidence, method = matcher.match_asset(asset)
        
        assert path is None
        assert confidence == "none"
        assert method == "no_file_found"
    
    @patch.object(ExifReader, 'read_exif')
    @patch.object(ExifReader, 'parse_exif_datetime')
    def test_match_asset_ambiguous_exact_exif(
        self, 
        mock_parse, 
        mock_read, 
        temp_target_dir
    ):
        """Test matching asset with ambiguous filename using exact EXIF match."""
        matcher = FileMatcher(str(temp_target_dir))
        
        # Mock EXIF reading
        immich_dt = datetime(2025, 6, 15, 18, 30, 0)
        file1_dt = datetime(2025, 6, 15, 18, 30, 0)  # Exact match
        file2_dt = datetime(2025, 7, 20, 10, 0, 0)
        
        mock_read.side_effect = [
            {"DateTimeOriginal": "2025:06:15 18:30:00"},
            {"DateTimeOriginal": "2025:07:20 10:00:00"}
        ]
        mock_parse.side_effect = [immich_dt, file1_dt, file2_dt]
        
        asset = {
            "originalFileName": "IMG_001.jpg",
            "dateTimeOriginal": "2025-06-15T18:30:00Z"
        }
        
        path, confidence, method = matcher.match_asset(asset)
        
        assert path is not None
        assert "2025/06" in path
        assert confidence == "exact"
        assert method == "exif_date_exact"
    
    @patch.object(ExifReader, 'read_exif')
    @patch.object(ExifReader, 'parse_exif_datetime')
    def test_match_asset_ambiguous_fuzzy_exif(
        self, 
        mock_parse, 
        mock_read, 
        temp_target_dir
    ):
        """Test matching asset with ambiguous filename using fuzzy EXIF match."""
        matcher = FileMatcher(str(temp_target_dir))
        
        # Mock EXIF reading with close but not exact match
        immich_dt = datetime(2025, 6, 15, 18, 30, 0)
        file1_dt = datetime(2025, 6, 15, 18, 35, 0)  # 5 minutes off
        file2_dt = datetime(2025, 7, 20, 10, 0, 0)
        
        mock_read.side_effect = [
            {"DateTimeOriginal": "2025:06:15 18:35:00"},
            {"DateTimeOriginal": "2025:07:20 10:00:00"}
        ]
        mock_parse.side_effect = [immich_dt, file1_dt, file2_dt]
        
        asset = {
            "originalFileName": "IMG_001.jpg",
            "dateTimeOriginal": "2025-06-15T18:30:00Z"
        }
        
        path, confidence, method = matcher.match_asset(asset)
        
        assert path is not None
        assert confidence == "fuzzy"
        assert "exif_date_fuzzy" in method
    
    @patch.object(ExifReader, 'read_exif')
    @patch.object(ExifReader, 'parse_exif_datetime')
    def test_match_asset_ambiguous_no_exif(
        self, 
        mock_parse, 
        mock_read, 
        temp_target_dir
    ):
        """Test matching asset with ambiguous filename and no EXIF data."""
        matcher = FileMatcher(str(temp_target_dir))
        
        # Mock no EXIF data
        mock_read.return_value = {}
        mock_parse.return_value = datetime(2025, 6, 15, 18, 30, 0)
        
        asset = {
            "originalFileName": "IMG_001.jpg",
            "dateTimeOriginal": "2025-06-15T18:30:00Z"
        }
        
        path, confidence, method = matcher.match_asset(asset)
        
        assert path is None
        assert confidence == "none"
        assert "ambiguous_2_files" in method
    
    @patch.object(ExifReader, 'read_exif')
    @patch.object(ExifReader, 'parse_exif_datetime')
    def test_match_asset_ambiguous_no_immich_date(
        self, 
        mock_parse, 
        mock_read, 
        temp_target_dir
    ):
        """Test matching asset with ambiguous filename and no Immich date."""
        matcher = FileMatcher(str(temp_target_dir))
        
        asset = {
            "originalFileName": "IMG_001.jpg"
        }
        
        path, confidence, method = matcher.match_asset(asset)
        
        assert path is None
        assert confidence == "none"
        assert "ambiguous_2_files" in method
    
    def test_nonexistent_target_dir(self):
        """Test matcher with non-existent target directory."""
        matcher = FileMatcher("/nonexistent/path")
        
        assert len(matcher.filename_index) == 0
