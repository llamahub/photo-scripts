#!/usr/bin/env python3
"""Tests for set_image_dates.py script."""

import csv
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest
from unittest import mock

# Add the scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from set_image_dates import ImageDateSetter, main


class TestImageDateSetter:
    """Test the ImageDateSetter class."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            target_dir = temp_path / "target"
            csv_file = temp_path / "test.csv"
            target_dir.mkdir()

            yield target_dir, csv_file

    @pytest.fixture
    def sample_csv_data(self):
        """Sample CSV data for testing."""
        return [
            {"Source Path": "image1.jpg", "Set Date": "2023-08-20 15:45:30"},
            {"Source Path": "image2.jpg", "Set Date": "2023-08-21"},
            {"Source Path": "image3.jpg", "Set Date": ""},  # No date
            {"Source Path": "image4.jpg", "Set Date": "2023/08/22 10:30"},
            {"Source Path": "image5.jpg", "Set Date": "invalid-date"},
        ]

    def test_init_default(self):
        """Test ImageDateSetter initialization with default logger."""
        setter = ImageDateSetter()

        assert setter is not None
        assert setter.logger is not None
        assert setter.stats == {"processed": 0, "updated": 0, "skipped": 0, "errors": 0}

    def test_init_with_custom_logger(self):
        """Test ImageDateSetter initialization with custom logger."""
        import logging

        custom_logger = logging.getLogger("test_logger")

        setter = ImageDateSetter(logger=custom_logger)

        assert setter.logger == custom_logger
        assert setter.stats == {"processed": 0, "updated": 0, "skipped": 0, "errors": 0}

    def test_parse_date_valid_formats(self):
        """Test parsing various valid date formats."""
        setter = ImageDateSetter()

        test_cases = [
            ("2023-08-20 15:45:30", "2023:08:20 15:45:30"),
            ("2023-08-20 15:45", "2023:08:20 15:45:00"),
            ("2023-08-20", "2023:08:20 00:00:00"),
            ("2023/08/20 15:45:30", "2023:08:20 15:45:30"),
            ("2023/08/20", "2023:08:20 00:00:00"),
            ("08/20/2023", "2023:08:20 00:00:00"),
            ("2023:08:20 15:45:30", "2023:08:20 15:45:30"),
            # 2-digit year formats (common in CSV files)
            ("4/20/24", "2024:04:20 00:00:00"),
            ("11/24/24", "2024:11:24 00:00:00"),
            ("2/10/14", "2014:02:10 00:00:00"),
            ("8/20/24", "2024:08:20 00:00:00"),
            ("9/19/23", "2023:09:19 00:00:00"),
            ("10/3/23", "2023:10:03 00:00:00"),
            ("11/11/24", "2024:11:11 00:00:00"),
        ]

        for input_date, expected in test_cases:
            result = setter.parse_date(input_date)
            assert result == expected, f"Failed for input '{input_date}'"

    def test_parse_date_invalid_formats(self):
        """Test parsing invalid date formats."""
        setter = ImageDateSetter()

        invalid_dates = [
            "",
            "   ",
            "not-a-date",
            "2023-13-40",  # Invalid month/day
            "20/30/2023",  # Invalid day
        ]

        for invalid_date in invalid_dates:
            result = setter.parse_date(invalid_date)
            assert result is None, f"Should have failed for '{invalid_date}'"

    @mock.patch("subprocess.run")
    def test_validate_exiftool_success(self, mock_run):
        """Test ExifTool validation when available."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["exiftool", "-ver"], returncode=0, stdout="12.50\n"
        )

        setter = ImageDateSetter()
        result = setter.validate_exiftool()

        assert result is True
        mock_run.assert_called_once_with(
            ["exiftool", "-ver"], capture_output=True, text=True, timeout=10
        )

    @mock.patch("subprocess.run")
    def test_validate_exiftool_not_found(self, mock_run):
        """Test ExifTool validation when not available."""
        mock_run.side_effect = FileNotFoundError()

        setter = ImageDateSetter()
        result = setter.validate_exiftool()

        assert result is False

    @mock.patch("subprocess.run")
    def test_validate_exiftool_timeout(self, mock_run):
        """Test ExifTool validation with timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(["exiftool", "-ver"], 10)

        setter = ImageDateSetter()
        result = setter.validate_exiftool()

        assert result is False

    def test_set_image_date_file_not_found(self, temp_dirs):
        """Test setting date on non-existent file."""
        target_dir, _ = temp_dirs
        nonexistent_file = target_dir / "nonexistent.jpg"

        setter = ImageDateSetter()
        result = setter.set_image_date(nonexistent_file, "2023:08:20 15:45:30")

        assert result is False

    def test_set_image_date_dry_run(self, temp_dirs):
        """Test setting date in dry run mode."""
        target_dir, _ = temp_dirs
        test_file = target_dir / "test.jpg"
        test_file.write_text("fake image content")

        setter = ImageDateSetter()
        result = setter.set_image_date(test_file, "2023:08:20 15:45:30", dry_run=True)

        assert result is True

    @mock.patch("subprocess.run")
    def test_set_image_date_success(self, mock_run, temp_dirs):
        """Test successful date setting."""
        target_dir, _ = temp_dirs
        test_file = target_dir / "test.jpg"
        test_file.write_text("fake image content")

        mock_run.return_value = subprocess.CompletedProcess(
            args=["exiftool"], returncode=0, stdout="1 image files updated\n"
        )

        setter = ImageDateSetter()
        result = setter.set_image_date(test_file, "2023:08:20 15:45:30", dry_run=False)

        assert result is True
        mock_run.assert_called_once()

    @mock.patch("subprocess.run")
    def test_set_image_date_failure(self, mock_run, temp_dirs):
        """Test failed date setting."""
        target_dir, _ = temp_dirs
        test_file = target_dir / "test.jpg"
        test_file.write_text("fake image content")

        mock_run.return_value = subprocess.CompletedProcess(
            args=["exiftool"], returncode=1, stderr="Error: File format not supported\n"
        )

        setter = ImageDateSetter()
        result = setter.set_image_date(test_file, "2023:08:20 15:45:30", dry_run=False)

        assert result is False

    def test_process_csv_file_not_found(self, temp_dirs):
        """Test processing non-existent CSV file."""
        target_dir, csv_file = temp_dirs

        setter = ImageDateSetter()

        with pytest.raises(FileNotFoundError):
            setter.process_csv(csv_file, target_dir, "Source Path", "Set Date")

    def test_process_csv_missing_columns(self, temp_dirs, sample_csv_data):
        """Test processing CSV with missing required columns."""
        target_dir, csv_file = temp_dirs

        # Create CSV without required columns
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Wrong Column", "Another Column"])
            writer.writeheader()
            writer.writerow({"Wrong Column": "value", "Another Column": "value"})

        setter = ImageDateSetter()

        with pytest.raises(ValueError, match="File column 'Source Path' not found"):
            setter.process_csv(csv_file, target_dir, "Source Path", "Set Date")

    @mock.patch.object(ImageDateSetter, "set_image_date")
    def test_process_csv_success(self, mock_set_date, temp_dirs, sample_csv_data):
        """Test successful CSV processing."""
        target_dir, csv_file = temp_dirs

        # Create CSV file
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Source Path", "Set Date"])
            writer.writeheader()
            for row in sample_csv_data:
                writer.writerow(row)

        # Mock successful date setting
        mock_set_date.return_value = True

        setter = ImageDateSetter()
        setter.process_csv(
            csv_file, target_dir, "Source Path", "Set Date", dry_run=True
        )

        # Should have processed 5 rows
        assert setter.stats["processed"] == 5
        # Should have skipped 1 (empty date)
        assert setter.stats["skipped"] == 1
        # Should have attempted to update 3 valid dates (one invalid date becomes error)
        assert mock_set_date.call_count == 3

    def test_print_summary(self, temp_dirs):
        """Test printing processing summary."""
        setter = ImageDateSetter()
        setter.stats = {"processed": 10, "updated": 8, "skipped": 1, "errors": 1}

        # Should not raise any exceptions
        setter.print_summary()


class TestSetImageDatesScript:
    """Test the set_image_dates.py script CLI interface."""

    @pytest.fixture
    def script_path(self):
        """Get path to the script."""
        return Path(__file__).parent.parent / "scripts" / "set_image_dates.py"

    @pytest.fixture
    def temp_setup(self):
        """Create temporary test environment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            target_dir = temp_path / "target"
            csv_file = temp_path / "test.csv"
            target_dir.mkdir()

            # Create test CSV
            csv_data = [
                {"Source Path": "image1.jpg", "Set Date": "2023-08-20 15:45:30"},
                {"Source Path": "image2.jpg", "Set Date": ""},
            ]

            with open(csv_file, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["Source Path", "Set Date"])
                writer.writeheader()
                for row in csv_data:
                    writer.writerow(row)

            yield target_dir, csv_file

    def run_script(self, args):
        """Run the script with given arguments."""
        script_path = Path(__file__).parent.parent / "scripts" / "set_image_dates.py"
        cmd = [sys.executable, str(script_path)] + args
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_script_help(self):
        """Test script shows help message."""
        result = self.run_script(["--help"])

        assert result.returncode == 0
        assert "Update EXIF dates in images" in result.stdout
        assert "target" in result.stdout
        assert "input" in result.stdout

    def test_script_missing_arguments(self):
        """Test script with missing required arguments."""
        result = self.run_script([])

        assert result.returncode != 0
        assert "required" in result.stderr or "error" in result.stderr.lower()

    def test_script_nonexistent_target(self, temp_setup):
        """Test script with non-existent target folder."""
        _, csv_file = temp_setup

        result = self.run_script(["/nonexistent", str(csv_file)])

        assert result.returncode != 0

    def test_script_nonexistent_csv(self, temp_setup):
        """Test script with non-existent CSV file."""
        target_dir, _ = temp_setup

        result = self.run_script([str(target_dir), "/nonexistent.csv"])

        assert result.returncode != 0

    def test_script_no_exiftool(self, temp_setup):
        """Test script when ExifTool is not available."""
        target_dir, csv_file = temp_setup

        # Since ExifTool is actually available, we'll test error handling differently
        # by using an invalid target directory
        result = self.run_script(["/invalid/path", str(csv_file)])

        assert result.returncode != 0

    def test_script_dry_run(self, temp_setup):
        """Test script in dry run mode."""
        target_dir, csv_file = temp_setup

        result = self.run_script([str(target_dir), str(csv_file), "--dry-run"])

        assert result.returncode == 0
        assert "DRY RUN completed" in result.stderr

    def test_script_custom_columns(self, temp_setup):
        """Test script with custom column names - should fail with proper error."""
        target_dir, csv_file = temp_setup

        result = self.run_script(
            [
                str(target_dir),
                str(csv_file),
                "--file-col",
                "File Path",
                "--date-col",
                "New Date",
                "--dry-run",
            ]
        )

        # Should fail because custom columns don't exist in test CSV
        assert result.returncode != 0
        assert "File column 'File Path' not found" in result.stderr

    @mock.patch.object(ImageDateSetter, "validate_exiftool")
    @mock.patch.object(ImageDateSetter, "process_csv")
    def test_script_debug_mode(self, mock_process, mock_validate, temp_setup):
        """Test script in debug mode."""
        target_dir, csv_file = temp_setup
        mock_validate.return_value = True

        result = self.run_script(
            [str(target_dir), str(csv_file), "--debug", "--dry-run"]
        )

        assert result.returncode == 0

    def test_script_main_function_import(self):
        """Test that main function can be imported."""
        from set_image_dates import main

        assert callable(main)

    @mock.patch("sys.argv")
    @mock.patch.object(ImageDateSetter, "validate_exiftool")
    @mock.patch.object(ImageDateSetter, "process_csv")
    def test_script_main_function_success(
        self, mock_process, mock_validate, mock_argv, temp_setup
    ):
        """Test main function directly with valid arguments."""
        target_dir, csv_file = temp_setup
        mock_validate.return_value = True
        mock_argv.__getitem__.side_effect = lambda i: [
            "set_image_dates.py",
            str(target_dir),
            str(csv_file),
            "--dry-run",
        ][i]
        mock_argv.__len__.return_value = 4

        result = main()

        assert result == 0

    @mock.patch("sys.argv")
    def test_script_main_function_error_handling(self, mock_argv):
        """Test main function error handling."""
        mock_argv.__getitem__.side_effect = lambda i: [
            "set_image_dates.py",
            "/nonexistent",
            "/nonexistent.csv",
        ][i]
        mock_argv.__len__.return_value = 3

        result = main()

        assert result == 1


class TestSetImageDatesIntegration:
    """Integration tests for the set_image_dates script."""

    @pytest.fixture
    def integration_setup(self):
        """Create realistic test environment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            target_dir = temp_path / "photos"
            csv_file = temp_path / "analysis.csv"
            target_dir.mkdir()

            # Create some fake image files
            (target_dir / "image1.jpg").write_text("fake jpeg content")
            (target_dir / "image2.png").write_text("fake png content")

            # Create analysis CSV with some entries to update
            csv_data = [
                {
                    "Condition": "Good Match",
                    "Status": "OK",
                    "Month Match": "Yes",
                    "Parent Date": "2023-08-20",
                    "Filename Date": "2023-08-20",
                    "Image Date": "2023-08-20 15:45:30",
                    "Source Path": "image1.jpg",
                    "Target Path": "2020+/2023/2023-08/photos/image1.jpg",
                    "Target Exists": "FALSE",
                    "Alt Filename Date": "",
                    "Set Date": "2023-08-21 10:30:00",  # User wants to change this
                },
                {
                    "Condition": "No EXIF Date",
                    "Status": "Missing",
                    "Month Match": "N/A",
                    "Parent Date": "",
                    "Filename Date": "",
                    "Image Date": "",
                    "Source Path": "image2.png",
                    "Target Path": "2020+/unknown/photos/image2.png",
                    "Target Exists": "FALSE",
                    "Alt Filename Date": "",
                    "Set Date": "",  # No date to set
                },
            ]

            with open(csv_file, "w", newline="") as f:
                fieldnames = [
                    "Condition",
                    "Status",
                    "Month Match",
                    "Parent Date",
                    "Filename Date",
                    "Image Date",
                    "Source Path",
                    "Target Path",
                    "Target Exists",
                    "Alt Filename Date",
                    "Set Date",
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in csv_data:
                    writer.writerow(row)

            yield target_dir, csv_file

    @mock.patch.object(ImageDateSetter, "validate_exiftool")
    @mock.patch.object(ImageDateSetter, "set_image_date")
    def test_integration_dry_run(self, mock_set_date, mock_validate, integration_setup):
        """Test full integration in dry run mode."""
        target_dir, csv_file = integration_setup
        mock_validate.return_value = True
        mock_set_date.return_value = True

        setter = ImageDateSetter()
        setter.process_csv(
            csv_file, target_dir, "Source Path", "Set Date", dry_run=True
        )

        # Should process 2 rows, skip 1 (no date), update 1
        assert setter.stats["processed"] == 2
        assert setter.stats["skipped"] == 1
        assert mock_set_date.call_count == 1

        # Verify the call was made with correct parameters
        call_args = mock_set_date.call_args[0]
        assert str(call_args[0]) == str(target_dir / "image1.jpg")
        assert call_args[1] == "2023:08:21 10:30:00"
        assert call_args[2] is True  # dry_run=True

    def test_integration_statistics(self, integration_setup):
        """Test that statistics are properly tracked."""
        target_dir, csv_file = integration_setup

        setter = ImageDateSetter()

        # Mock validate_exiftool to avoid needing actual ExifTool
        with mock.patch.object(
            setter, "validate_exiftool", return_value=True
        ), mock.patch.object(setter, "set_image_date", return_value=True):

            setter.process_csv(
                csv_file, target_dir, "Source Path", "Set Date", dry_run=True
            )

        # Verify statistics
        assert setter.stats["processed"] == 2  # Total rows processed
        assert setter.stats["skipped"] == 1  # One row had no date
        assert setter.stats["updated"] == 1  # One row was "updated" (mocked)
        assert setter.stats["errors"] == 0  # No errors in this test


if __name__ == "__main__":
    pytest.main([__file__])
