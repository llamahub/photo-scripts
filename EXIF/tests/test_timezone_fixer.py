"""
Unit tests for timezone_fixer.py business logic
"""

import pytest
import csv
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from exif.timezone_fixer import TimezoneFixer


class TestTimezoneFixer:
    """Test TimezoneFixer business logic."""

    def test_calculate_new_datetime_offset_est_to_utc(self):
        """Test converting EST to UTC."""
        fixer = TimezoneFixer("dummy.csv", dry_run=True)

        # Winter date (EST = -05:00)
        new_date, new_offset = fixer.calculate_new_datetime_offset(
            "2024:01:15 14:30:00",
            "-05:00",
            "UTC"
        )

        assert new_date == "2024:01:15 19:30:00"
        assert new_offset == "+00:00"

    def test_calculate_new_datetime_offset_edt_to_utc(self):
        """Test converting EDT to UTC."""
        fixer = TimezoneFixer("dummy.csv", dry_run=True)

        # Summer date (EDT = -04:00)
        new_date, new_offset = fixer.calculate_new_datetime_offset(
            "2024:07:15 14:30:00",
            "-04:00",
            "UTC"
        )

        assert new_date == "2024:07:15 18:30:00"
        assert new_offset == "+00:00"

    def test_calculate_new_datetime_offset_utc_to_ny_winter(self):
        """Test converting UTC to New York timezone in winter (EST)."""
        fixer = TimezoneFixer("dummy.csv", dry_run=True)

        new_date, new_offset = fixer.calculate_new_datetime_offset(
            "2024:01:15 19:30:00",
            "+00:00",
            "America/New_York"
        )

        assert new_date == "2024:01:15 14:30:00"
        assert new_offset == "-05:00"

    def test_calculate_new_datetime_offset_utc_to_ny_summer(self):
        """Test converting UTC to New York timezone in summer (EDT)."""
        fixer = TimezoneFixer("dummy.csv", dry_run=True)

        new_date, new_offset = fixer.calculate_new_datetime_offset(
            "2024:07:15 18:30:00",
            "+00:00",
            "America/New_York"
        )

        assert new_date == "2024:07:15 14:30:00"
        assert new_offset == "-04:00"

    def test_calculate_new_datetime_offset_handles_iso_format(self):
        """Test that ISO format dates (YYYY-MM-DD) are handled correctly."""
        fixer = TimezoneFixer("dummy.csv", dry_run=True)

        # ISO format (from CSV output)
        new_date, new_offset = fixer.calculate_new_datetime_offset(
            "2024-01-15 19:30:00",
            "+00:00",
            "America/New_York"
        )

        assert new_date == "2024:01:15 14:30:00"
        assert new_offset == "-05:00"

    def test_run_skips_empty_fix_timezone(self, tmp_path):
        """Test that rows with empty fix_timezone are skipped."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['file', 'status', 'target_date', 'target_offset', 'target_timezone', 'fix_timezone', 'error_msg'])
            writer.writerow(['/path/to/image.jpg', 'updated', '2024-01-15 14:30:00', '-05:00', 'America/New_York', '', ''])

        fixer = TimezoneFixer(str(csv_file), dry_run=True)
        result = fixer.run()

        assert result['total'] == 1
        assert result['skipped'] == 1
        assert result['processed'] == 0

    def test_run_processes_with_fix_timezone(self, tmp_path):
        """Test that rows with fix_timezone are processed."""
        # Create test image file
        image_file = tmp_path / "test.jpg"
        image_file.write_bytes(b"fake image data")

        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['file', 'status', 'target_date', 'target_offset', 'target_timezone', 'fix_timezone', 'error_msg'])
            writer.writerow([str(image_file), 'updated', '2024-01-15 19:30:00', '+00:00', 'UTC', 'America/New_York', ''])

        with patch('exif.immich_extract_support.ExifToolManager') as mock_exiftool, \
             patch('exif.image_analyzer.ImageAnalyzer') as mock_analyzer:
            
            # Mock ImageAnalyzer
            mock_instance = MagicMock()
            mock_instance.get_exif.return_value = {
                'Description': 'Test photo',
                'Subject': ['tag1', 'tag2']
            }
            mock_analyzer.return_value = mock_instance

            fixer = TimezoneFixer(str(csv_file), dry_run=False)
            result = fixer.run()

            assert result['total'] == 1
            assert result['processed'] == 1
            assert result['skipped'] == 0
            assert result['errors'] == 0

            # Verify ExifToolManager.update_exif was called with correct parameters
            mock_exiftool.update_exif.assert_called_once()
            call_args = mock_exiftool.update_exif.call_args
            assert call_args[0][0] == str(image_file)  # file_path
            assert call_args[1]['date_exif'] == '2024:01:15 14:30:00'  # converted to NY time
            assert call_args[1]['date_exif_offset'] == '-05:00'  # NY winter offset

    def test_run_dry_run_mode(self, tmp_path):
        """Test that dry run mode doesn't modify files."""
        image_file = tmp_path / "test.jpg"
        image_file.write_bytes(b"fake image data")

        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['file', 'status', 'target_date', 'target_offset', 'target_timezone', 'fix_timezone', 'error_msg'])
            writer.writerow([str(image_file), 'updated', '2024-01-15 19:30:00', '+00:00', 'UTC', 'America/New_York', ''])

        with patch('exif.immich_extract_support.ExifToolManager') as mock_exiftool:
            fixer = TimezoneFixer(str(csv_file), dry_run=True)
            result = fixer.run()

            assert result['total'] == 1
            assert result['processed'] == 1

            # Verify ExifToolManager.update_exif was NOT called in dry run
            mock_exiftool.update_exif.assert_not_called()

    def test_run_handles_missing_file(self, tmp_path):
        """Test that missing files are logged as errors."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['file', 'status', 'target_date', 'target_offset', 'target_timezone', 'fix_timezone', 'error_msg'])
            writer.writerow(['/nonexistent/image.jpg', 'updated', '2024-01-15 19:30:00', '+00:00', 'UTC', 'America/New_York', ''])

        fixer = TimezoneFixer(str(csv_file), dry_run=True)
        result = fixer.run()

        assert result['total'] == 1
        assert result['errors'] == 1
        assert result['processed'] == 0

    def test_run_handles_missing_required_fields(self, tmp_path):
        """Test that rows with missing required fields are logged as errors."""
        csv_file = tmp_path / "test.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['file', 'status', 'target_date', 'target_offset', 'target_timezone', 'fix_timezone', 'error_msg'])
            writer.writerow(['', 'updated', '', '', '', 'America/New_York', ''])

        fixer = TimezoneFixer(str(csv_file), dry_run=True)
        result = fixer.run()

        assert result['total'] == 1
        assert result['errors'] == 1
        assert result['processed'] == 0


class TestCalculateTimezoneFromOffset:
    """Test calculate_timezone_from_offset helper function."""

    def test_utc_offset(self):
        """Test UTC offset returns UTC timezone."""
        from exif.immich_extractor import calculate_timezone_from_offset

        tz = calculate_timezone_from_offset("2024:01:15 12:00:00", "+00:00")
        assert tz == "UTC"

    def test_ny_winter_offset(self):
        """Test NY winter offset (EST = -05:00)."""
        from exif.immich_extractor import calculate_timezone_from_offset

        tz = calculate_timezone_from_offset("2024:01:15 12:00:00", "-05:00")
        assert tz == "America/New_York"

    def test_ny_summer_offset(self):
        """Test NY summer offset (EDT = -04:00)."""
        from exif.immich_extractor import calculate_timezone_from_offset

        tz = calculate_timezone_from_offset("2024:07:15 12:00:00", "-04:00")
        assert tz == "America/New_York"

    def test_empty_inputs(self):
        """Test empty inputs return empty string."""
        from exif.immich_extractor import calculate_timezone_from_offset

        assert calculate_timezone_from_offset("", "+00:00") == ""
        assert calculate_timezone_from_offset("2024:01:15 12:00:00", "") == ""

    def test_invalid_date(self):
        """Test invalid date returns empty string."""
        from exif.immich_extractor import calculate_timezone_from_offset

        tz = calculate_timezone_from_offset("invalid", "+00:00")
        assert tz == ""
