#!/usr/bin/env python3
"""Unit tests for ImageAnalyzer class."""

import pytest
import os
import csv
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import our modules
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from exif import ImageAnalyzer, ImageData


class TestImageAnalyzer:
    """Test cases for ImageAnalyzer class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_folder = os.path.join(self.temp_dir, "test_images")
        os.makedirs(self.test_folder)

        # Create test image files
        self.test_files = [
            "2023-06-15_1230_IMG_001.jpg",
            "20240301_143045.CR2",
            "vacation_photo.png",
            "2022-12-25_family.tiff",
        ]

        for filename in self.test_files:
            filepath = os.path.join(self.test_folder, filename)
            Path(filepath).touch()

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        shutil.rmtree(self.temp_dir)

    def test_init_default(self):
        """Test ImageAnalyzer initialization with default parameters."""
        analyzer = ImageAnalyzer()
        assert analyzer.folder_path is None
        assert analyzer.csv_output is None
        assert analyzer.results == []

    def test_init_with_parameters(self):
        """Test ImageAnalyzer initialization with parameters."""
        folder_path = "/test/folder"
        csv_output = "/test/output.csv"

        analyzer = ImageAnalyzer(folder_path=folder_path, csv_output=csv_output)
        assert analyzer.folder_path == folder_path
        assert analyzer.csv_output == csv_output
        assert analyzer.results == []

    def test_analyze_images_no_folder_path(self):
        """Test analyze_images raises error when no folder path provided."""
        analyzer = ImageAnalyzer()

        with pytest.raises(ValueError, match="No folder path provided"):
            analyzer.analyze_images()

    def test_analyze_images_nonexistent_folder(self):
        """Test analyze_images raises error for nonexistent folder."""
        analyzer = ImageAnalyzer()
        nonexistent_path = "/nonexistent/folder"

        with pytest.raises(
            FileNotFoundError, match=f"Folder not found: {nonexistent_path}"
        ):
            analyzer.analyze_images(nonexistent_path)

    def test_analyze_images_uses_instance_folder_path(self):
        """Test analyze_images uses instance folder_path when no parameter provided."""
        analyzer = ImageAnalyzer(folder_path=self.test_folder)

        with patch.object(analyzer, "_analyze_single_image") as mock_analyze:
            mock_analyze.return_value = {"test": "result"}
            results = analyzer.analyze_images()

            # Should have been called for each test file
            assert mock_analyze.call_count == len(self.test_files)
            assert len(results) == len(self.test_files)

    def test_analyze_images_parameter_overrides_instance(self):
        """Test analyze_images parameter overrides instance folder_path."""
        analyzer = ImageAnalyzer(folder_path="/wrong/path")

        with patch.object(analyzer, "_analyze_single_image") as mock_analyze:
            mock_analyze.return_value = {"test": "result"}
            results = analyzer.analyze_images(self.test_folder)

            # Should have been called for each test file
            assert mock_analyze.call_count == len(self.test_files)
            assert len(results) == len(self.test_files)

    @patch.object(ImageData, "getImageDate")
    @patch.object(ImageData, "getFilenameDate")
    @patch.object(ImageData, "getParentName")
    @patch.object(ImageData, "normalize_parent_date")
    @patch.object(ImageData, "strip_time")
    @patch.object(ImageData, "get_condition")
    @patch.object(ImageData, "extract_alt_filename_date")
    @patch.object(ImageData, "getTrueExt")
    @patch.object(ImageData, "getImageSize")
    @patch.object(ImageData, "getTargetFilename")
    def test_analyze_single_image_success(
        self,
        mock_target,
        mock_size,
        mock_ext,
        mock_alt,
        mock_condition,
        mock_strip,
        mock_norm_parent,
        mock_parent,
        mock_filename_date,
        mock_image_date,
    ):
        """Test _analyze_single_image with successful analysis."""
        # Setup mocks
        mock_image_date.return_value = "2023-06-15 12:30:00"
        mock_filename_date.return_value = "2023-06-15 00:00:00"
        mock_parent.return_value = "2023-06"
        mock_norm_parent.return_value = "2023-06-01 00:00:00"
        mock_strip.side_effect = lambda x: x[:10]  # Return first 10 chars (date part)
        mock_condition.return_value = ("Match condition", "Match")
        mock_alt.return_value = "2023-06-15 12:30"
        mock_ext.return_value = "jpg"
        mock_size.return_value = ("1920", "1080")
        mock_target.return_value = (
            "/tmp/2023/2023-06/2023-06-15_1230_1920x1080_2023-06_IMG_001.jpg"
        )

        analyzer = ImageAnalyzer()
        test_file = os.path.join(self.test_folder, self.test_files[0])

        result = analyzer._analyze_single_image(test_file)

        # Verify result structure
        assert result["filepath"] == test_file
        assert result["filename"] == self.test_files[0]
        assert result["parent_name"] == "2023-06"
        assert result["image_date"] == "2023-06-15 12:30:00"
        assert result["filename_date"] == "2023-06-15 00:00:00"
        assert result["condition_category"] == "Match"
        assert result["true_ext"] == "jpg"
        assert result["width"] == "1920"
        assert result["height"] == "1080"
        assert "error" not in result

    def test_analyze_single_image_error(self):
        """Test _analyze_single_image handles errors gracefully."""
        analyzer = ImageAnalyzer()
        test_file = os.path.join(self.test_folder, self.test_files[0])

        with patch.object(
            ImageData, "getImageDate", side_effect=Exception("Test error")
        ):
            result = analyzer._analyze_single_image(test_file)

            assert result["filepath"] == test_file
            assert result["filename"] == self.test_files[0]
            assert result["error"] == "Test error"
            assert result["condition_category"] == "Error"

    def test_save_to_csv_no_path_provided(self):
        """Test save_to_csv raises error when no CSV path provided."""
        analyzer = ImageAnalyzer()

        with pytest.raises(ValueError, match="No CSV output path provided"):
            analyzer.save_to_csv()

    def test_save_to_csv_no_results(self):
        """Test save_to_csv raises error when no results to save."""
        analyzer = ImageAnalyzer()
        csv_path = os.path.join(self.temp_dir, "test.csv")

        with pytest.raises(ValueError, match="No results to save"):
            analyzer.save_to_csv(csv_path)

    def test_save_to_csv_uses_instance_path(self):
        """Test save_to_csv uses instance csv_output when no parameter provided."""
        csv_path = os.path.join(self.temp_dir, "test.csv")
        analyzer = ImageAnalyzer(csv_output=csv_path)
        analyzer.results = [{"filepath": "/test", "filename": "test.jpg"}]

        analyzer.save_to_csv()

        assert os.path.exists(csv_path)

    def test_save_to_csv_parameter_overrides_instance(self):
        """Test save_to_csv parameter overrides instance csv_output."""
        wrong_path = os.path.join(self.temp_dir, "wrong.csv")
        correct_path = os.path.join(self.temp_dir, "correct.csv")

        analyzer = ImageAnalyzer(csv_output=wrong_path)
        analyzer.results = [{"filepath": "/test", "filename": "test.jpg"}]

        analyzer.save_to_csv(correct_path)

        assert os.path.exists(correct_path)
        assert not os.path.exists(wrong_path)

    def test_save_to_csv_creates_directory(self):
        """Test save_to_csv creates output directory if it doesn't exist."""
        csv_dir = os.path.join(self.temp_dir, "new", "dir")
        csv_path = os.path.join(csv_dir, "test.csv")

        analyzer = ImageAnalyzer()
        analyzer.results = [{"filepath": "/test", "filename": "test.jpg"}]

        analyzer.save_to_csv(csv_path)

        assert os.path.exists(csv_path)
        assert os.path.exists(csv_dir)

    def test_save_to_csv_writes_correct_format(self):
        """Test save_to_csv writes CSV in correct format."""
        csv_path = os.path.join(self.temp_dir, "test.csv")

        test_results = [
            {
                "filepath": "/test/file1.jpg",
                "filename": "file1.jpg",
                "parent_name": "2023-06",
                "parent_date": "2023-06-01 00:00:00",
                "filename_date": "2023-06-15 00:00:00",
                "image_date": "2023-06-15 12:30:00",
                "alt_filename_date": "",
                "parent_date_norm": "2023-06-01",
                "filename_date_norm": "2023-06-15",
                "image_date_norm": "2023-06-15",
                "condition_desc": "Test condition",
                "condition_category": "Match",
                "true_ext": "jpg",
                "width": "1920",
                "height": "1080",
                "target_filename": "target.jpg",
            }
        ]

        analyzer = ImageAnalyzer()
        analyzer.save_to_csv(csv_path, test_results)

        # Read and verify CSV content
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            rows = list(reader)

        expected_headers = [
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

        assert headers == expected_headers
        assert len(rows) == 1
        assert rows[0]["filepath"] == "/test/file1.jpg"
        assert rows[0]["condition_category"] == "Match"

    def test_get_statistics_no_results(self):
        """Test get_statistics returns empty dict when no results."""
        analyzer = ImageAnalyzer()
        stats = analyzer.get_statistics()
        assert stats == {}

    def test_get_statistics_uses_instance_results(self):
        """Test get_statistics uses instance results when no parameter provided."""
        analyzer = ImageAnalyzer()
        analyzer.results = [
            {"condition_category": "Match"},
            {"condition_category": "Partial"},
            {"error": "Test error"},
        ]

        stats = analyzer.get_statistics()

        assert stats["total_images"] == 3
        assert stats["successful_analyses"] == 2
        assert stats["errors"] == 1
        assert stats["categories"]["Match"] == 1
        assert stats["categories"]["Partial"] == 1

    def test_get_statistics_parameter_overrides_instance(self):
        """Test get_statistics parameter overrides instance results."""
        analyzer = ImageAnalyzer()
        analyzer.results = [{"condition_category": "Wrong"}]

        test_results = [
            {"condition_category": "Match"},
            {"condition_category": "Match"},
        ]

        stats = analyzer.get_statistics(test_results)

        assert stats["total_images"] == 2
        assert stats["categories"]["Match"] == 2
        assert "Wrong" not in stats["categories"]

    def test_get_statistics_calculates_percentages(self):
        """Test get_statistics calculates category percentages correctly."""
        test_results = [
            {"condition_category": "Match"},
            {"condition_category": "Match"},
            {"condition_category": "Partial"},
            {"condition_category": "Mismatch"},
        ]

        analyzer = ImageAnalyzer()
        stats = analyzer.get_statistics(test_results)

        assert stats["total_images"] == 4
        assert stats["category_percentages"]["Match"] == 50.0
        assert stats["category_percentages"]["Partial"] == 25.0
        assert stats["category_percentages"]["Mismatch"] == 25.0

    def test_print_statistics_no_results(self, capsys):
        """Test print_statistics handles no results gracefully."""
        analyzer = ImageAnalyzer()
        analyzer.print_statistics()

        captured = capsys.readouterr()
        assert "No analysis results available" in captured.out

    def test_print_statistics_with_results(self, capsys):
        """Test print_statistics prints formatted statistics."""
        test_results = [
            {"condition_category": "Match"},
            {"condition_category": "Partial"},
            {"error": "Test error"},
        ]

        analyzer = ImageAnalyzer()
        analyzer.print_statistics(test_results)

        captured = capsys.readouterr()
        assert "Analysis Statistics:" in captured.out
        assert "Total images: 3" in captured.out
        assert "Successful analyses: 2" in captured.out
        assert "Errors: 1" in captured.out
        assert "Match: 1" in captured.out
        assert "Partial: 1" in captured.out

    def test_integration_analyze_and_save(self):
        """Integration test: analyze images and save to CSV."""
        csv_path = os.path.join(self.temp_dir, "integration_test.csv")

        # Mock ImageData methods for consistent results
        with patch.object(
            ImageData, "getImageDate", return_value="2023-06-15 12:30:00"
        ), patch.object(
            ImageData, "getFilenameDate", return_value="2023-06-15 00:00:00"
        ), patch.object(
            ImageData, "getParentName", return_value="2023-06"
        ), patch.object(
            ImageData, "normalize_parent_date", return_value="2023-06-01 00:00:00"
        ), patch.object(
            ImageData, "strip_time", side_effect=lambda x: x[:10]
        ), patch.object(
            ImageData, "get_condition", return_value=("Test condition", "Match")
        ), patch.object(
            ImageData, "extract_alt_filename_date", return_value=""
        ), patch.object(
            ImageData, "getTrueExt", return_value="jpg"
        ), patch.object(
            ImageData, "getImageSize", return_value=("1920", "1080")
        ), patch.object(
            ImageData, "getTargetFilename", return_value="/tmp/target.jpg"
        ):

            analyzer = ImageAnalyzer(folder_path=self.test_folder, csv_output=csv_path)
            results = analyzer.analyze_images()
            analyzer.save_to_csv()

            # Verify results
            assert len(results) == len(self.test_files)
            assert os.path.exists(csv_path)

            # Verify CSV content
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                csv_rows = list(reader)

            assert len(csv_rows) == len(self.test_files)
            for row in csv_rows:
                assert row["condition_category"] == "Match"

    # Additional tests for improved coverage

    def test_analyze_images_fast_no_folder_path(self):
        """Test analyze_images_fast with no folder path."""
        analyzer = ImageAnalyzer()
        with pytest.raises(ValueError, match="No folder path provided"):
            analyzer.analyze_images_fast()

    def test_analyze_images_fast_nonexistent_folder(self):
        """Test analyze_images_fast with nonexistent folder."""
        analyzer = ImageAnalyzer()
        with pytest.raises(FileNotFoundError, match="Folder not found"):
            analyzer.analyze_images_fast("/nonexistent/path")

    def test_analyze_images_fast_empty_folder(self):
        """Test analyze_images_fast with empty folder."""
        empty_folder = os.path.join(self.temp_dir, "empty")
        os.makedirs(empty_folder)
        analyzer = ImageAnalyzer()
        
        results = analyzer.analyze_images_fast(empty_folder)
        assert results == []

    @patch("exif.image_analyzer.ImageData.getImageDate")
    @patch("exif.image_analyzer.ImageData.getFilenameDate")
    @patch("exif.image_analyzer.ImageData.normalize_parent_date")
    def test_analyze_images_fast_with_progress_callback(
        self, mock_parent_date, mock_filename_date, mock_image_date
    ):
        """Test analyze_images_fast with progress callback."""
        # Mock return values
        mock_image_date.return_value = "2023-06-15 12:30"
        mock_filename_date.return_value = "2023-06-15 12:30"
        mock_parent_date.return_value = "2023-06-15 00:00"
        
        analyzer = ImageAnalyzer(batch_size=2)
        progress_calls = []
        
        def progress_callback(current, total):
            progress_calls.append((current, total))
            
        results = analyzer.analyze_images_fast(self.test_folder, progress_callback)
        
        assert len(results) == len(self.test_files)
        assert len(progress_calls) >= 1  # Should have at least one progress update
        # Check that progress values are reasonable
        for current, total in progress_calls:
            assert 0 < current <= total
            assert total == len(self.test_files)

    def test_find_image_files_fast(self):
        """Test _find_image_files_fast method."""
        analyzer = ImageAnalyzer()
        
        # Create additional non-image files
        non_image_files = ["document.txt", "video.mp4", "README.md"]
        for filename in non_image_files:
            filepath = os.path.join(self.test_folder, filename)
            Path(filepath).touch()
        
        image_files = analyzer._find_image_files_fast(self.test_folder)
        
        # Should only return image files (jpg, CR2, png, tiff from our test files)
        expected_extensions = {".jpg", ".cr2", ".png", ".tiff"}
        found_extensions = {Path(f).suffix.lower() for f in image_files}
        
        assert len(image_files) == len(self.test_files)
        assert found_extensions.issubset(expected_extensions)

    @patch("exif.image_analyzer.subprocess.run")
    def test_batch_extract_exif_success(self, mock_run):
        """Test _batch_extract_exif method with successful extraction."""
        # Mock successful ExifTool response
        mock_exif_data = [
            {
                "SourceFile": self.test_files[0],
                "DateTimeOriginal": "2023:06:15 12:30:00",
                "ImageWidth": 1920,
                "ImageHeight": 1080
            },
            {
                "SourceFile": self.test_files[1],
                "DateTimeOriginal": "2024:03:01 14:30:45",
                "ImageWidth": 4000,
                "ImageHeight": 3000
            }
        ]
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_exif_data)
        )
        
        analyzer = ImageAnalyzer()
        test_batch = [os.path.join(self.test_folder, f) for f in self.test_files[:2]]
        
        exif_data = analyzer._batch_extract_exif(test_batch)
        
        assert len(exif_data) == 2
        assert self.test_files[0] in exif_data
        assert self.test_files[1] in exif_data
        assert exif_data[self.test_files[0]]["ImageWidth"] == 1920
        assert exif_data[self.test_files[1]]["ImageHeight"] == 3000

    @patch("exif.image_analyzer.subprocess.run")
    def test_batch_extract_exif_failure(self, mock_run):
        """Test _batch_extract_exif method with ExifTool failure."""
        # Mock ExifTool failure
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="ExifTool error"
        )
        
        analyzer = ImageAnalyzer()
        test_batch = [os.path.join(self.test_folder, f) for f in self.test_files[:2]]
        
        exif_data = analyzer._batch_extract_exif(test_batch)
        
        assert exif_data == {}

    @patch("exif.image_analyzer.subprocess.run")
    def test_batch_extract_exif_json_error(self, mock_run):
        """Test _batch_extract_exif method with invalid JSON response."""
        # Mock invalid JSON response
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="invalid json"
        )
        
        analyzer = ImageAnalyzer()
        test_batch = [os.path.join(self.test_folder, f) for f in self.test_files[:1]]
        
        exif_data = analyzer._batch_extract_exif(test_batch)
        
        assert exif_data == {}

    @patch("exif.image_analyzer.ImageData.getImageDate")
    def test_analyze_single_image_cached_with_exif(self, mock_image_date):
        """Test _analyze_single_image_cached with EXIF data."""
        mock_image_date.return_value = "2023-06-15 12:30"
        
        analyzer = ImageAnalyzer()
        test_file = os.path.join(self.test_folder, self.test_files[0])
        
        # Mock cached EXIF data
        exif_data = {
            "DateTimeOriginal": "2023:06:15 12:30:00",
            "ImageWidth": 1920,
            "ImageHeight": 1080
        }
        
        result = analyzer._analyze_single_image_cached(test_file, exif_data)
        
        assert result["filepath"] == test_file
        assert result["filename"] == self.test_files[0]
        assert "condition_category" in result
        assert "width" in result
        assert "height" in result

    def test_analyze_single_image_cached_error(self):
        """Test _analyze_single_image_cached with error handling."""
        analyzer = ImageAnalyzer()
        
        # Use a non-existent file to trigger an error
        bad_file = "/nonexistent/file.jpg"
        
        result = analyzer._analyze_single_image_cached(bad_file)
        
        assert result["filepath"] == bad_file
        assert result["filename"] == "file.jpg"
        # The method should return valid structure even for non-existent files
        assert "condition_category" in result

    def test_analyze_with_progress(self):
        """Test analyze_with_progress method."""
        with patch.object(ImageAnalyzer, "analyze_images_fast") as mock_analyze:
            mock_analyze.return_value = ["result1", "result2"]
            
            analyzer = ImageAnalyzer()
            results = analyzer.analyze_with_progress(self.test_folder)
            
            # Should call analyze_images_fast with a progress callback
            mock_analyze.assert_called_once()
            call_args = mock_analyze.call_args
            assert call_args[0][0] == self.test_folder  # folder_path
            assert callable(call_args[0][1])  # progress_callback
            assert results == ["result1", "result2"]

    @patch("random.sample")
    def test_analyze_sample_large_dataset(self, mock_sample):
        """Test analyze_sample with dataset larger than sample size."""
        # Create more test files
        large_file_list = [f"image_{i}.jpg" for i in range(200)]
        for filename in large_file_list:
            filepath = os.path.join(self.test_folder, filename)
            Path(filepath).touch()
        
        # Mock random.sample to return a predictable subset
        sample_files = [os.path.join(self.test_folder, f"image_{i}.jpg") for i in range(50)]
        mock_sample.return_value = sample_files
        
        with patch.object(ImageAnalyzer, "_process_batch_parallel") as mock_process:
            mock_process.return_value = ["sample_result"] * 50
            
            analyzer = ImageAnalyzer()
            results = analyzer.analyze_sample(self.test_folder, sample_size=50)
            
            mock_sample.assert_called_once()
            assert len(results) == 50

    def test_analyze_sample_small_dataset(self):
        """Test analyze_sample with dataset smaller than sample size."""
        with patch.object(ImageAnalyzer, "analyze_images_fast") as mock_analyze:
            mock_analyze.return_value = ["result"] * len(self.test_files)
            
            analyzer = ImageAnalyzer()
            results = analyzer.analyze_sample(self.test_folder, sample_size=100)
            
            # Should call analyze_images_fast since dataset is smaller than sample
            mock_analyze.assert_called_once_with(self.test_folder)
            assert len(results) == len(self.test_files)

    def test_getImageDate_cached_with_exif_priority(self):
        """Test _getImageDate_cached method with EXIF priority order."""
        analyzer = ImageAnalyzer()
        
        # Test priority order - DateTimeOriginal should take precedence
        exif_data = {
            "FileModifyDate": "2020:01:01 10:00:00",
            "XMP-photoshop:DateCreated": "2021:02:02 11:00:00",
            "ExifIFD:DateTimeOriginal": "2022:03:03 12:00:00",
            "DateTimeOriginal": "2023:04:04 13:00:00"  # This should win
        }
        
        with patch.object(analyzer, 'normalize_date') as mock_normalize:
            mock_normalize.return_value = "2023-04-04 13:00"
            
            result = analyzer._getImageDate_cached("test.jpg", exif_data)
            
            # Should have called normalize_date with the DateTimeOriginal value
            mock_normalize.assert_called_with("2023-04-04 13:00:00")
            assert result == "2023-04-04 13:00"

    def test_getImageDate_cached_filename_fallback(self):
        """Test _getImageDate_cached fallback to filename date."""
        analyzer = ImageAnalyzer()
        
        # Empty EXIF data
        exif_data = {}
        
        with patch.object(analyzer, 'getFilenameDate') as mock_filename_date:
            mock_filename_date.return_value = "2023-06-15 12:30"
            
            result = analyzer._getImageDate_cached("2023-06-15_photo.jpg", exif_data)
            
            mock_filename_date.assert_called_once_with("2023-06-15_photo.jpg")
            assert result == "2023-06-15 12:30"

    def test_getImageDate_cached_default_fallback(self):
        """Test _getImageDate_cached default fallback."""
        analyzer = ImageAnalyzer()
        
        # Empty EXIF data and no filename date
        exif_data = {}
        
        with patch.object(analyzer, 'getFilenameDate') as mock_filename_date:
            mock_filename_date.return_value = "1900-01-01 00:00"
            
            result = analyzer._getImageDate_cached("random_photo.jpg", exif_data)
            
            assert result == "1900-01-01 00:00"


if __name__ == "__main__":
    pytest.main([__file__])
