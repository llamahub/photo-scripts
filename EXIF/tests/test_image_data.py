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
