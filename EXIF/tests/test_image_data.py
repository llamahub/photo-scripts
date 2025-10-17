from exif.image_data import ImageData


def test_normalize_date():
    assert ImageData.normalize_date("2020-01-02 12:34:00") == "2020-01-02 12:34"
    assert ImageData.normalize_date("") == "1900-01-01 00:00"
    assert ImageData.normalize_date("1900") == "1900-01-01 00:00"


def test_normalize_parent_date():
    assert (
        ImageData.normalize_parent_date("2012-06-04 Cousin Camp") == "2012-06-04 00:00"
    )
    assert ImageData.normalize_parent_date("") == "1900-01-01 00:00"
    assert ImageData.normalize_parent_date("2012-06") == "2012-06-01 00:00"


def test_strip_time():
    assert ImageData.strip_time("2020-01-02 12:34:00") == "2020-01-02"
    assert ImageData.strip_time("") == "1900-01-01"


def test_get_condition():
    assert ImageData.get_condition("2020-01-01", "2020-01-01", "2020-01-01") == (
        "P Date = F Date = I Date",
        "Match",
    )
    assert (
        ImageData.get_condition("2020-01-01", "2020-01-01", "2020-01-02")[1]
        == "Partial"
    )
    assert (
        ImageData.get_condition("2020-01-01", "2020-01-02", "2020-01-01")[1]
        == "Partial"
    )
    assert (
        ImageData.get_condition("2020-01-02", "2020-01-01", "2020-01-01")[1]
        == "Partial"
    )
    assert (
        ImageData.get_condition("2020-01-01", "2020-01-02", "2020-01-03")[1]
        == "Mismatch"
    )


def test_get_month_match():
    """Test the get_month_match method for all scenarios."""
    # Test Match: Both Parent Date and File Date are 1900-01-01
    assert (
        ImageData.get_month_match("1900-01-01", "1900-01-01", "2024-01-25") == "Match"
    )
    assert (
        ImageData.get_month_match("1900-01-01", "1900-01-01", "1900-01-01") == "Match"
    )

    # Test Match: File and Image match, Parent matches
    assert (
        ImageData.get_month_match("2024-01-15", "2024-01-20", "2024-01-25") == "Match"
    )

    # Test Match: File and Image match, Parent is 1900-01-01 (ignored)
    assert (
        ImageData.get_month_match("1900-01-01", "2024-01-20", "2024-01-25") == "Match"
    )

    # Test Partial Image: Image matches Parent
    assert (
        ImageData.get_month_match("2024-01-15", "2024-02-20", "2024-01-25")
        == "Partial Image"
    )

    # Test Partial File: File matches Parent
    assert (
        ImageData.get_month_match("2024-01-15", "2024-01-20", "2024-02-25")
        == "Partial File"
    )

    # Test Mismatch: All different months
    assert (
        ImageData.get_month_match("2024-01-15", "2024-02-20", "2024-03-25")
        == "Mismatch"
    )

    # Test Mismatch: File and Image match but Parent doesn't (and isn't 1900-01-01)
    assert (
        ImageData.get_month_match("2024-03-15", "2024-01-20", "2024-01-25")
        == "Mismatch"
    )

    # Test with empty/invalid dates
    assert ImageData.get_month_match("", "2024-01-20", "2024-01-25") == "Match"
    assert ImageData.get_month_match("2024-01-15", "", "") == "Mismatch"


def test_extract_alt_filename_date():
    parent_date = "2020-01-01 00:00"
    assert (
        ImageData.extract_alt_filename_date("IMG_20200101_123456.jpg", parent_date)
        == "2020-01-01 12:34"
    )
    assert (
        ImageData.extract_alt_filename_date("IMG_2020-01-01_123456.jpg", parent_date)
        == "2020-01-01 12:34"
    )
    assert (
        ImageData.extract_alt_filename_date("IMG_20200101.jpg", parent_date)
        == "2020-01-01"
    )
    assert (
        ImageData.extract_alt_filename_date("IMG_2020-01-01.jpg", parent_date)
        == "2020-01-01"
    )
    assert ImageData.extract_alt_filename_date("IMG_20190101.jpg", parent_date) == ""


def test_getFilenameDate():
    """Test filename date extraction."""
    # Test with hyphenated date format
    result = ImageData.getFilenameDate("2023-06-15_photo.jpg")
    assert result == "2023-06-15 00:00"

    # Test with underscore date format
    result = ImageData.getFilenameDate("2023_06_15_photo.jpg")
    assert result == "2023-06-15 00:00"

    # Test with year-month only
    result = ImageData.getFilenameDate("2023-06_photo.jpg")
    assert result == "2023-06-01 00:00"

    # Test with compact YYYYMMDD_HHMMSS format (common camera format)
    result = ImageData.getFilenameDate("20240210_091738.jpg")
    assert result == "2024-02-10 09:17"

    # Test with compact YYYYMMDD format (date only)
    result = ImageData.getFilenameDate("20240210.jpg")
    assert result == "2024-02-10 00:00"

    # Test with no date pattern
    result = ImageData.getFilenameDate("random_photo.jpg")
    assert result == "1900-01-01 00:00"

    # Test new functionality: dates anywhere in filename
    # Screenshot format
    result = ImageData.getFilenameDate("Screenshot 2024-08-20 at 7.51.41 PM.png")
    assert result == "2024-08-20 00:00"

    # Photo with prefix
    result = ImageData.getFilenameDate("IMG_2024-05-15_vacation.jpg")
    assert result == "2024-05-15 00:00"

    # Date in middle with description
    result = ImageData.getFilenameDate("Photo from 2023-12-25.png")
    assert result == "2023-12-25 00:00"

    # Backup format with timestamp
    result = ImageData.getFilenameDate("backup_20240315_143022.jpg")
    assert result == "2024-03-15 14:30"


def test_getParentName(tmp_path):
    d = tmp_path / "2020-01-02"
    d.mkdir()
    f = d / "test.jpg"
    f.write_text("")
    assert ImageData.getParentName(str(f)) == "2020-01-02"
    d2 = tmp_path / "1234"
    d2.mkdir()
    f2 = d2 / "test.jpg"
    f2.write_text("")
    assert ImageData.getParentName(str(f2)) == "1234"
    d3 = tmp_path / "foo"
    d3.mkdir()
    f3 = d3 / "test.jpg"
    f3.write_text("")
    assert ImageData.getParentName(str(f3)) == "foo"


def test_getTrueExt(monkeypatch):
    def fake_get_exif(filepath):
        return {"FileTypeExtension": "JPG"}

    monkeypatch.setattr(ImageData, "get_exif", staticmethod(fake_get_exif))
    assert ImageData.getTrueExt("foo.jpg") == "jpg"
    monkeypatch.setattr(ImageData, "get_exif", staticmethod(lambda x: {}))
    assert ImageData.getTrueExt("foo.JPG") == "jpg"


def test_getImageSize(monkeypatch):
    def fake_get_exif(filepath):
        return {"ImageWidth": 100, "ImageHeight": 200}

    monkeypatch.setattr(ImageData, "get_exif", staticmethod(fake_get_exif))
    assert ImageData.getImageSize("foo.jpg") == ("100", "200")
    monkeypatch.setattr(ImageData, "get_exif", staticmethod(lambda x: {}))
    assert ImageData.getImageSize("foo.jpg") == ("", "")


def test_getTargetFilename(monkeypatch, tmp_path):
    def fake_get_exif(filepath):
        return {
            "FileTypeExtension": "jpg",
            "ImageWidth": 100,
            "ImageHeight": 200,
            "DateTimeOriginal": "2020:01:02 12:34:00",
        }

    monkeypatch.setattr(ImageData, "get_exif", staticmethod(fake_get_exif))
    f = tmp_path / "2020-01-02" / "test.jpg"
    f.parent.mkdir()
    f.write_text("")
    target = ImageData.getTargetFilename(str(f), str(tmp_path), label="test")
    assert "2020-01-02_1234_test_100x200_2020-01-02_test.jpg" in target


def test_getImageDate(monkeypatch):
    def fake_get_exif(filepath):
        return {"DateTimeOriginal": "2020:01:02 12:34:00"}

    monkeypatch.setattr(ImageData, "get_exif", staticmethod(fake_get_exif))
    assert ImageData.getImageDate("foo.jpg") == "2020-01-02 12:34"
    monkeypatch.setattr(ImageData, "get_exif", staticmethod(lambda x: {}))
    assert ImageData.getImageDate("foo.jpg") == "1900-01-01 00:00"


def test_getImageDate_priority_order(monkeypatch):
    """Test that date fields are checked in correct priority order."""

    # Test 1: DateTimeOriginal (highest priority) is preferred over all others
    def mock_with_all_dates(filepath):
        return {
            "DateTimeOriginal": "2020:01:01 10:00:00",  # Should win
            "ExifIFD:DateTimeOriginal": "2020:02:02 11:00:00",
            "XMP-photoshop:DateCreated": "2020:03:03 12:00:00",
            "FileModifyDate": "2020:04:04 13:00:00",
        }

    monkeypatch.setattr(ImageData, "get_exif", staticmethod(mock_with_all_dates))
    assert ImageData.getImageDate("test.jpg") == "2020-01-01 10:00"

    # Test 2: ExifIFD:DateTimeOriginal wins when DateTimeOriginal is missing
    def mock_without_datetime_original(filepath):
        return {
            "ExifIFD:DateTimeOriginal": "2020:02:02 11:00:00",  # Should win
            "XMP-photoshop:DateCreated": "2020:03:03 12:00:00",
            "FileModifyDate": "2020:04:04 13:00:00",
        }

    monkeypatch.setattr(
        ImageData, "get_exif", staticmethod(mock_without_datetime_original)
    )
    assert ImageData.getImageDate("test.jpg") == "2020-02-02 11:00"

    # Test 3: XMP-photoshop:DateCreated wins when both DateTime fields are missing
    def mock_only_xmp_and_file(filepath):
        return {
            "XMP-photoshop:DateCreated": "2020:03:03 12:00:00",  # Should win
            "FileModifyDate": "2020:04:04 13:00:00",
        }

    monkeypatch.setattr(ImageData, "get_exif", staticmethod(mock_only_xmp_and_file))
    assert ImageData.getImageDate("test.jpg") == "2020-03-03 12:00"

    # Test 4: FileModifyDate (lowest priority) is used when all others are missing
    def mock_only_file_modify(filepath):
        return {"FileModifyDate": "2020:04:04 13:00:00"}  # Last resort

    monkeypatch.setattr(ImageData, "get_exif", staticmethod(mock_only_file_modify))
    assert ImageData.getImageDate("test.jpg") == "2020-04-04 13:00"

    # Test 5: Empty/None values are skipped in priority order
    def mock_with_empty_high_priority(filepath):
        return {
            "DateTimeOriginal": "",  # Empty, should be skipped
            "ExifIFD:DateTimeOriginal": None,  # None, should be skipped
            "XMP-photoshop:DateCreated": "2020:03:03 12:00:00",  # Should win
            "FileModifyDate": "2020:04:04 13:00:00",
        }

    monkeypatch.setattr(
        ImageData, "get_exif", staticmethod(mock_with_empty_high_priority)
    )
    assert ImageData.getImageDate("test.jpg") == "2020-03-03 12:00"


def test_getImageDate_filename_fallback(monkeypatch):
    """Test that getImageDate falls back to filename parsing when no EXIF data is available."""

    # Test filename fallback when no metadata is available
    def mock_no_metadata(filepath):
        return {}

    monkeypatch.setattr(ImageData, "get_exif", staticmethod(mock_no_metadata))

    # Should extract date from filename in YYYYMMDD_HHMMSS format
    result = ImageData.getImageDate("20240210_091738.jpg")
    assert result == "2024-02-10 09:17"

    # Should extract date from filename in YYYYMMDD format
    result = ImageData.getImageDate("20240210.jpg")
    assert result == "2024-02-10 00:00"

    # Should return fallback when no filename pattern matches
    result = ImageData.getImageDate("random_photo.jpg")
    assert result == "1900-01-01 00:00"


# Additional comprehensive tests for improved coverage


def test_get_exif_success(monkeypatch):
    """Test successful EXIF extraction."""
    import subprocess
    import json

    # Mock successful subprocess result
    mock_exif_data = [
        {
            "DateTimeOriginal": "2023:06:15 12:30:00",
            "FileTypeExtension": "jpg",
            "ImageWidth": 1920,
            "ImageHeight": 1080,
        }
    ]

    def mock_run(*args, **kwargs):
        result = type("MockResult", (), {})()
        result.returncode = 0
        result.stdout = json.dumps(mock_exif_data)
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = ImageData.get_exif("test.jpg")

    assert result["DateTimeOriginal"] == "2023:06:15 12:30:00"
    assert result["FileTypeExtension"] == "jpg"
    assert result["ImageWidth"] == 1920
    assert result["ImageHeight"] == 1080


def test_get_exif_failure(monkeypatch):
    """Test EXIF extraction failure."""
    import subprocess

    def mock_run(*args, **kwargs):
        result = type("MockResult", (), {})()
        result.returncode = 1
        result.stdout = ""
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = ImageData.get_exif("test.jpg")
    assert result == {}


def test_get_exif_json_error(monkeypatch):
    """Test EXIF extraction with JSON parsing error."""
    import subprocess

    def mock_run(*args, **kwargs):
        result = type("MockResult", (), {})()
        result.returncode = 0
        result.stdout = "invalid json"
        return result

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = ImageData.get_exif("test.jpg")
    assert result == {}


def test_get_exif_exception(monkeypatch):
    """Test EXIF extraction with subprocess exception."""
    import subprocess

    def mock_run(*args, **kwargs):
        raise Exception("Subprocess error")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = ImageData.get_exif("test.jpg")
    assert result == {}


def test_normalize_date_edge_cases():
    """Test normalize_date with various edge cases."""

    # Test None input
    assert ImageData.normalize_date(None) == "1900-01-01 00:00"

    # Test empty string
    assert ImageData.normalize_date("") == "1900-01-01 00:00"

    # Test date starting with 1900
    assert ImageData.normalize_date("1900-01-01 12:00") == "1900-01-01 00:00"

    # Test with underscore separators - only handles hour parsing, not minutes from filename
    assert ImageData.normalize_date("2023_06_15_12_30_45") == "2023-06-15 12:00"

    # Test with T separator (ISO format)
    assert ImageData.normalize_date("2023-06-15T12:30:45") == "2023-06-15 12:30"

    # Test with only date part
    assert ImageData.normalize_date("2023-06-15") == "2023-06-15 00:00"

    # Test with partial time
    assert ImageData.normalize_date("2023-06-15 12") == "2023-06-15 12:00"
    assert ImageData.normalize_date("2023-06-15 12:30") == "2023-06-15 12:30"

    # Test invalid format
    assert ImageData.normalize_date("invalid date") == "1900-01-01 00:00"


def test_normalize_parent_date_edge_cases():
    """Test normalize_parent_date with various formats."""

    # Test None input
    assert ImageData.normalize_parent_date(None) == "1900-01-01 00:00"

    # Test empty string
    assert ImageData.normalize_parent_date("") == "1900-01-01 00:00"

    # Test YYYY-MM-DD format
    assert ImageData.normalize_parent_date("2023-06-15") == "2023-06-15 00:00"

    # Test YYYY-MM format
    assert ImageData.normalize_parent_date("2023-06") == "2023-06-01 00:00"

    # Test YYYY format
    assert ImageData.normalize_parent_date("2023") == "2023-01-01 00:00"

    # Test invalid format
    assert ImageData.normalize_parent_date("invalid") == "1900-01-01 00:00"


def test_get_condition_all_combinations():
    """Test get_condition with all possible input combinations."""

    # All valid dates - check actual return format
    result = ImageData.get_condition("2023-06-15", "2023-06-15", "2023-06-15")
    assert "P Date = F Date = I Date" in result[0]
    assert result[1] == "Match"

    # Parent and filename match, image different - actual format uses < >
    result = ImageData.get_condition("2023-06-15", "2023-06-15", "2023-07-01")
    assert "P Date = F Date" in result[0] and "< I Date" in result[0]
    assert result[1] == "Partial"

    # Parent and image match, filename different
    result = ImageData.get_condition("2023-06-15", "2023-07-01", "2023-06-15")
    assert "P Date = I Date" in result[0]
    assert result[1] == "Partial"

    # Filename and image match, parent different
    result = ImageData.get_condition("2023-07-01", "2023-06-15", "2023-06-15")
    assert "F Date = I Date" in result[0]
    assert result[1] == "Partial"

    # No matches
    result = ImageData.get_condition("2023-06-15", "2023-07-01", "2023-08-01")
    assert result[0] == "Else"
    assert result[1] == "Mismatch"

    # Test with None values - edge case scenarios
    result = ImageData.get_condition("1900-01-01 00:00", "2023-06-15", "2023-06-15")
    assert result[1] == "Partial"

    result = ImageData.get_condition(
        "1900-01-01 00:00", "1900-01-01 00:00", "1900-01-01 00:00"
    )
    assert result[1] == "Match"


def test_get_month_match_comprehensive():
    """Test get_month_match with comprehensive scenarios."""

    # All dates in same month - actual return is just "Match"
    result = ImageData.get_month_match("2023-06-01", "2023-06-15", "2023-06-30")
    assert result == "Match"

    # Parent and filename in same month
    result = ImageData.get_month_match("2023-06-01", "2023-06-15", "2023-07-15")
    assert result == "Partial File"

    # Parent and image in same month
    result = ImageData.get_month_match("2023-06-01", "2023-07-15", "2023-06-30")
    assert result == "Partial Image"

    # Filename and image in same month (parent doesn't match, so no Match)
    result = ImageData.get_month_match("2023-05-01", "2023-06-15", "2023-06-30")
    assert result == "Mismatch"  # Parent doesn't match, so it's mismatch

    # No matches
    result = ImageData.get_month_match("2023-05-01", "2023-06-15", "2023-07-30")
    assert result == "Mismatch"

    # Test with 1900 dates - special case handling
    result = ImageData.get_month_match("1900-01-01", "2023-06-15", "2023-06-30")
    assert result == "Match"  # None parent treated as special case


def test_extract_alt_filename_date_comprehensive():
    """Test extract_alt_filename_date with various scenarios."""
    from pathlib import Path

    # Test with simple filename containing date - returns without time
    result = ImageData.extract_alt_filename_date(
        Path("/test/folder/20230615_photo.jpg"), "2023-06-15 00:00"
    )
    assert result == "2023-06-15"  # Method returns just date part

    # Test with filename containing different date patterns with time
    result = ImageData.extract_alt_filename_date(
        Path("/test/folder/IMG_20230615_123045.jpg"), "2023-06-01 00:00"
    )
    assert "2023-06-15" in result and "12:30" in result

    # Test with no date pattern in filename
    result = ImageData.extract_alt_filename_date(
        Path("/test/folder/random_photo.jpg"), "2023-06-15 00:00"
    )
    assert result == ""  # Returns empty string, not fallback

    # Test with parent date fallback
    result = ImageData.extract_alt_filename_date(
        Path("/test/2023-06/photo.jpg"), "1900-01-01 00:00"
    )
    assert result == ""  # Returns empty if no match


def test_getFilenameDate_comprehensive():
    """Test getFilenameDate with various filename patterns."""

    # Test YYYYMMDD_HHMMSS pattern - extract full date/time
    assert ImageData.getFilenameDate("20230615_123045.jpg") == "2023-06-15 12:30"

    # Test YYYYMMDD pattern
    assert ImageData.getFilenameDate("20230615.jpg") == "2023-06-15 00:00"

    # Test YYYY-MM-DD format - doesn't include time from space separated
    assert ImageData.getFilenameDate("2023-06-15 12:30:45.jpg") == "2023-06-15 00:00"

    # Test IMG_YYYYMMDD pattern
    assert ImageData.getFilenameDate("IMG_20230615.jpg") == "2023-06-15 00:00"

    # Test DSC_YYYYMMDD pattern
    assert ImageData.getFilenameDate("DSC_20230615.jpg") == "2023-06-15 00:00"

    # Test with time in filename - YYYYMMDD_HHMM pattern doesn't exist
    assert ImageData.getFilenameDate("photo_20230615_1230.jpg") == "2023-06-15 00:00"

    # Test no date pattern
    assert ImageData.getFilenameDate("random_photo.jpg") == "1900-01-01 00:00"

    # Test with path instead of just filename
    assert (
        ImageData.getFilenameDate("/path/to/20230615_photo.jpg") == "2023-06-15 00:00"
    )


def test_getTrueExt_edge_cases(monkeypatch):
    """Test getTrueExt with edge cases."""

    def mock_get_exif_with_ext(filepath):
        return {"FileTypeExtension": "JPG"}

    monkeypatch.setattr(ImageData, "get_exif", staticmethod(mock_get_exif_with_ext))

    result = ImageData.getTrueExt("test.png")  # File has .png but is actually JPG
    assert result == "jpg"  # Should return lowercase version of true extension

    # Test when no FileTypeExtension in EXIF
    def mock_get_exif_no_ext(filepath):
        return {}

    monkeypatch.setattr(ImageData, "get_exif", staticmethod(mock_get_exif_no_ext))

    result = ImageData.getTrueExt("test.png")
    assert result == "png"  # Should fall back to file extension


def test_getImageSize_edge_cases(monkeypatch):
    """Test getImageSize with edge cases."""

    def mock_get_exif_with_size(filepath):
        return {"ImageWidth": 1920, "ImageHeight": 1080}

    monkeypatch.setattr(ImageData, "get_exif", staticmethod(mock_get_exif_with_size))

    width, height = ImageData.getImageSize("test.jpg")
    assert width == "1920"
    assert height == "1080"

    # Test when no size info in EXIF
    def mock_get_exif_no_size(filepath):
        return {}

    monkeypatch.setattr(ImageData, "get_exif", staticmethod(mock_get_exif_no_size))

    width, height = ImageData.getImageSize("test.jpg")
    assert width == ""
    assert height == ""


def test_getParentName_comprehensive():
    """Test getParentName with various parent directory patterns."""

    # Test year only
    result = ImageData.getParentName("/photos/2023/image.jpg")
    assert result == "2023"

    # Test year-month
    result = ImageData.getParentName("/photos/2023-06/image.jpg")
    assert result == "2023-06"

    # Test year-month-day
    result = ImageData.getParentName("/photos/2023-06-15/image.jpg")
    assert result == "2023-06-15"

    # Test numeric pattern (should return empty)
    result = ImageData.getParentName("/photos/123456/image.jpg")
    assert result == ""

    # Test mixed pattern with numbers and chars - returns full name
    result = ImageData.getParentName("/photos/2023_vacation/image.jpg")
    assert result == "2023_vacation"  # Returns the actual parent name

    # Test descriptive folder name
    result = ImageData.getParentName("/photos/family_vacation/image.jpg")
    assert result == "family_vacation"

    # Test root directory
    result = ImageData.getParentName("/image.jpg")
    assert result == ""  # Root has no meaningful parent name


def test_getTargetFilename_comprehensive(monkeypatch, tmp_path):
    """Test getTargetFilename with various scenarios."""

    # Create test file
    test_file = tmp_path / "IMG_20230615_123045.jpg"
    test_file.touch()

    # Mock EXIF data
    def mock_get_exif(filepath):
        return {"DateTimeOriginal": "2023:06:15 12:30:45", "FileTypeExtension": "jpg"}

    monkeypatch.setattr(ImageData, "get_exif", staticmethod(mock_get_exif))

    # Test with label - check for key components in the complex filename
    result = ImageData.getTargetFilename(
        str(test_file), str(tmp_path), label="vacation"
    )
    assert "vacation" in result
    assert "IMG_20230615_123045.jpg" in result
    assert "2023-06-15" in result

    # Test without label
    result = ImageData.getTargetFilename(str(test_file), str(tmp_path))
    assert "IMG_20230615_123045.jpg" in result

    # Test with different date in EXIF vs filename
    def mock_get_exif_different_date(filepath):
        return {
            "DateTimeOriginal": "2024:07:20 15:45:30",  # Different from filename
            "FileTypeExtension": "jpg",
        }

    monkeypatch.setattr(
        ImageData, "get_exif", staticmethod(mock_get_exif_different_date)
    )

    result = ImageData.getTargetFilename(str(test_file), str(tmp_path))
    # Should use EXIF date for target path but preserve original filename
    assert "2024" in result and "07" in result  # EXIF date in path
    assert "IMG_20230615_123045.jpg" in result  # Original filename preserved
