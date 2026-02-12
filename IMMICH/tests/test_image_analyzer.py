#!/usr/bin/env python3
"""Tests for IMMICH ImageAnalyzer business logic."""

from pathlib import Path

import csv
import pytest

from image_analyzer import ImageAnalyzer


def test_extract_filename_date_priority():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    assert analyzer._extract_filename_date("2024-01-02_event_2020-01-01.jpg") == "2024-01-02"
    assert analyzer._extract_filename_date("event_2020-03-04.jpg") == "2020-03-04"
    assert analyzer._extract_filename_date("2024_event.jpg") == "2024-00-00"
    assert analyzer._extract_filename_date("_DSC1944.NEF") == ""


def test_split_datetime_offset_and_timezone():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    date, offset = analyzer._split_datetime_offset("2025:10:16 12:13:20+00:00")
    assert date == "2025:10:16 12:13:20"
    assert offset == "+00:00"
    assert analyzer._format_timezone(date, offset) == "UTC"


def test_split_datetime_offset_no_offset():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    date, offset = analyzer._split_datetime_offset("2025:10:16 12:13:20")
    assert date == "2025:10:16 12:13:20"
    assert offset == ""


def test_parse_offset_minutes_variants():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    assert analyzer._parse_offset_minutes("+05:30") == 330
    assert analyzer._parse_offset_minutes("-0700") == -420
    assert analyzer._parse_offset_minutes("9") == 540
    assert analyzer._parse_offset_minutes(0) == 0
    assert analyzer._parse_offset_minutes(2) == 120
    assert analyzer._parse_offset_minutes("") is None
    assert analyzer._parse_offset_minutes(None) is None


def test_extract_folder_date_variants():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    assert analyzer._extract_folder_date("2024-03") == "2024-03-00"
    assert analyzer._extract_folder_date("2024") == "2024-00-00"
    assert analyzer._extract_folder_date("no-date") == ""


def test_extract_filename_time():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    assert analyzer._extract_filename_time("2024-10-15_1430_photo.jpg") == "1430"
    assert analyzer._extract_filename_time("20241015_1430_photo.jpg") == "1430"
    assert analyzer._extract_filename_time("20241015-1430_photo.jpg") == "1430"
    assert analyzer._extract_filename_time("0000-00-00_0000_photo.jpg") == ""
    assert analyzer._extract_filename_time("photo.jpg") == ""


def test_get_first_exif_value_list():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    exif = {"Keywords": ["A", "B"]}
    assert analyzer._get_first_exif_value(exif, ["Keywords"]) == "A; B"


def test_extract_xmp_tags(tmp_path):
    xmp_content = """
    <x:xmpmeta xmlns:x='adobe:ns:meta/'>
      <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
        <rdf:Description xmlns:digiKam='http://www.digikam.org/ns/1.0/'>
          <digiKam:TagsList>
            <rdf:Seq>
              <rdf:li>ARCHIVE_MISC</rdf:li>
              <rdf:li>SCREENSHOT</rdf:li>
            </rdf:Seq>
          </digiKam:TagsList>
        </rdf:Description>
      </rdf:RDF>
    </x:xmpmeta>
    """
    xmp_path = tmp_path / "sample.xmp"
    xmp_path.write_text(xmp_content)

    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    tags = analyzer._extract_xmp_tags(xmp_path)
    assert "ARCHIVE_MISC" in tags
    assert "SCREENSHOT" in tags


def test_analyze_to_csv_writes_rows(tmp_path, monkeypatch):
    source_dir = tmp_path / "photos"
    source_dir.mkdir()
    image_path = source_dir / "2024-01-02_test.jpg"
    image_path.write_text("data")

    sidecar_path = source_dir / "2024-01-02_test.xmp"
    sidecar_path.write_text(
        "<x:xmpmeta xmlns:x='adobe:ns:meta/'>"
        "<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>"
        "<rdf:Description xmlns:digiKam='http://www.digikam.org/ns/1.0/'>"
        "<digiKam:TagsList><rdf:Seq><rdf:li>TAG1</rdf:li></rdf:Seq></digiKam:TagsList>"
        "</rdf:Description></rdf:RDF></x:xmpmeta>"
    )

    analyzer = ImageAnalyzer(str(source_dir), logger=_DummyLogger(), detect_true_ext=False, max_workers=1)

    def fake_read_exif(path):
        if path and path.suffix.lower() == ".xmp":
            return {"DateTimeOriginal": "2025:10:16 12:13:20+00:00"}
        return {"DateTimeOriginal": "2024:01:02 10:20:30+00:00"}

    monkeypatch.setattr(analyzer, "_read_exif", fake_read_exif)

    output_csv = tmp_path / "out.csv"
    rows = analyzer.analyze_to_csv(str(output_csv))
    assert rows == 1

    with output_csv.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        data = list(reader)

    assert data[0]["EXIF Date"] == "2024:01:02 10:20:30"
    assert data[0]["Sidecar Date"] == "2025:10:16 12:13:20"
    assert "TAG1" in data[0]["Sidecar Tags"]


def test_iter_image_files_filters(tmp_path):
    source_dir = tmp_path / "photos"
    source_dir.mkdir()
    (source_dir / "image.jpg").write_text("data")
    (source_dir / "image.PNG").write_text("data")
    (source_dir / "sidecar.xmp").write_text("xmp")
    (source_dir / "note.txt").write_text("text")

    analyzer = ImageAnalyzer(str(source_dir), logger=_DummyLogger())
    files = [p.name for p in analyzer._iter_image_files()]
    assert "image.jpg" in files
    assert "image.PNG" in files
    assert "sidecar.xmp" not in files
    assert "note.txt" not in files


def test_get_true_extension_skip(tmp_path):
    image_path = tmp_path / "photo.jpeg"
    image_path.write_text("data")
    analyzer = ImageAnalyzer(str(tmp_path), logger=_DummyLogger(), detect_true_ext=False)
    assert analyzer._get_true_extension(image_path) == "jpeg"


def test_retry_exif_timeouts(monkeypatch, tmp_path):
    source_dir = tmp_path / "photos"
    source_dir.mkdir()
    file_a = source_dir / "a.jpg"
    file_b = source_dir / "b.jpg"
    file_a.write_text("data")
    file_b.write_text("data")

    logger = _ListLogger()
    analyzer = ImageAnalyzer(str(source_dir), logger=logger)
    analyzer.exif_timeout_files = [file_a, file_b]

    def fake_read(path, timeout, track_timeouts):
        if path == file_a:
            return {"DateTimeOriginal": "2024:01:02 10:20:30"}
        return {}

    monkeypatch.setattr(analyzer, "_read_exif_with_timeout", fake_read)
    analyzer._retry_exif_timeouts()

    assert any("Retrying EXIF timeouts" in msg for msg in logger.infos)
    assert any(str(file_a) in msg for msg in logger.infos)
    assert any(str(file_b) in msg for msg in logger.errors)


# Tests for Calc Date Logic
def test_is_date_only():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    assert analyzer._is_date_only("2024-10-15") is True
    assert analyzer._is_date_only("2024-10") is True
    assert analyzer._is_date_only("2024") is True
    assert analyzer._is_date_only("2024_10_15") is True
    assert analyzer._is_date_only("2024-10-15_01") is True
    assert analyzer._is_date_only("2024_10_15_02") is True
    assert analyzer._is_date_only("2024-10-Vacation") is False
    assert analyzer._is_date_only("2024-10-15_Event") is False
    assert analyzer._is_date_only("Vacation") is False
    assert analyzer._is_date_only("") is True


def test_extract_descriptive_parent_folder():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    assert analyzer._extract_descriptive_parent_folder("2024-10") == ""
    assert analyzer._extract_descriptive_parent_folder("2024-10-15") == ""
    assert analyzer._extract_descriptive_parent_folder("2024-10-15_01") == ""
    assert analyzer._extract_descriptive_parent_folder("2024-10-Vacation") == "2024-10-Vacation"
    assert analyzer._extract_descriptive_parent_folder("MyEvent") == "MyEvent"
    assert analyzer._extract_descriptive_parent_folder("") == ""


def test_strip_duplicate_info_from_basename():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    # Remove leading date-time-dimension prefix from normalized filenames
    result = analyzer._strip_duplicate_info_from_basename(
        "2024-10-15_1430_1920x1080_MyEvent_IMG_4120", "MyEvent", "1920x1080"
    )
    assert result == "IMG_4120"
    # Remove parent folder name if it appears
    result = analyzer._strip_duplicate_info_from_basename(
        "MyEvent_IMG_4120", "MyEvent", "0x0"
    )
    assert result == "IMG_4120"
    # Handle date-only parent folders (should return just the basename)
    result = analyzer._strip_duplicate_info_from_basename(
        "2024-10-15_1430_1920x1080_IMG_4120", "2024-10", "1920x1080"
    )
    assert result == "IMG_4120"
    # Handle parent folders with version suffixes (strip the _01, _02, etc.)
    result = analyzer._strip_duplicate_info_from_basename(
        "2008-10-19 Cub Scout Camp_DSCN5110", "2008-10-19 Cub Scout Camp_01", "3072x2304"
    )
    assert result == "DSCN5110"


def test_get_image_dimensions():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    # With dimensions
    exif = {"ImageWidth": 1920, "ImageHeight": 1080}
    assert analyzer._get_image_dimensions(exif) == "1920x1080"
    # Missing dimensions
    assert analyzer._get_image_dimensions({}) == "0x0"
    # String dimensions (from EXIF)
    exif = {"ImageWidth": "1920", "ImageHeight": "1080"}
    assert analyzer._get_image_dimensions(exif) == "1920x1080"


def test_get_year_month():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    assert analyzer._get_year_month("2024-10-15") == "2024-10"
    assert analyzer._get_year_month("2024-10-15 14:30:45") == "2024-10"
    assert analyzer._get_year_month("2011:05:28 13:59:34") == "2011-05"
    assert analyzer._get_year_month("0624-00-00") is None
    assert analyzer._get_year_month("1900-01-01") is None
    assert analyzer._get_year_month("0000-00-00") is None
    assert analyzer._get_year_month("") is None
    assert analyzer._get_year_month("invalid") is None


def test_calculate_name_date():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    # Same month and year: use filename_date
    assert analyzer._calculate_name_date("2024-10-00", "2024-10-15") == "2024-10-15"
    # Folder year < filename year: use folder_date
    assert analyzer._calculate_name_date("2020-10-01", "2024-10-15") == "2020-10-01"
    # Different month, same year: use filename_date
    assert analyzer._calculate_name_date("2024-05-01", "2024-10-15") == "2024-10-15"
    # Invalid folder date: use filename_date
    assert analyzer._calculate_name_date("", "2024-10-15") == "2024-10-15"
    # Invalid filename date: use folder_date
    assert analyzer._calculate_name_date("2024-10-01", "") == "2024-10-01"
    # Both invalid: return empty
    assert analyzer._calculate_name_date("", "") == ""


def test_calculate_calc_date():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    # EXIF date <= Name date: use EXIF date
    assert analyzer._calculate_calc_date("2024-10-10", "2024-10-15") == "2024-10-10"
    # EXIF date > Name date: use Name date
    assert analyzer._calculate_calc_date("2024-10-20", "2024-10-15") == "2024-10-15"
    # Same date: use EXIF date
    assert analyzer._calculate_calc_date("2024-10-15", "2024-10-15") == "2024-10-15"
    # Invalid EXIF date: use Name date
    assert analyzer._calculate_calc_date("1900-01-01", "2024-10-15") == "2024-10-15"
    # Invalid Name date: use EXIF date
    assert analyzer._calculate_calc_date("2024-10-15", "1900-01-01") == "2024-10-15"
    # Both invalid: return Name date (fallback behavior)
    assert analyzer._calculate_calc_date("1900-01-01", "1900-01-01") == "1900-01-01"
    # EXIF with time: use if date is earlier
    assert analyzer._calculate_calc_date("2024-10-10 14:30:45", "2024-10-15") == "2024-10-10 14:30:45"
    # EXIF with colon separators: treat as valid for comparison
    assert analyzer._calculate_calc_date("2011:05:28 13:59:34", "2011-06-01") == "2011-05-28 13:59:34"


def test_calculate_calc_time_used():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    assert analyzer._calculate_calc_time_used(
        "EXIF", "2011:05:28 13:59:34", "", ""
    ) == ("1359", "EXIF")
    assert analyzer._calculate_calc_time_used(
        "EXIF", "2011:05:28 00:00:00", "", "2359"
    ) == ("2359", "Filename")
    assert analyzer._calculate_calc_time_used(
        "Sidecar", "", "2011:05:28 07:05:34", ""
    ) == ("0705", "Sidecar")
    assert analyzer._calculate_calc_time_used(
        "Filename", "", "", "1234"
    ) == ("1234", "Filename")
    assert analyzer._calculate_calc_time_used(
        "Folder", "", "", "1234"
    ) == ("", "")


def test_calculate_calc_offset_prefers_exif_when_time_from_filename():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    assert analyzer._calculate_calc_offset(
        "Filename", "EXIF", "+01:00", ""
    ) == "+01:00"


def test_calculate_meta_name_delta():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    assert analyzer._calculate_meta_name_delta("2011-05-28 13:59:34", "2011-06-01") == "0:0:3 10:0"
    assert analyzer._calculate_meta_name_delta("2011-05-00", "2011-06-01") == ""


def test_calculate_metadata_date():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    # Prefer EXIF when valid
    assert analyzer._calculate_metadata_date("2011:05:28 13:59:34", "2011-06-01") == (
        "2011-05-28 13:59:34",
        "EXIF",
    )
    # Fall back to sidecar when EXIF invalid
    assert analyzer._calculate_metadata_date("1900-01-01", "2011:06:02 09:00:00") == (
        "2011-06-02 09:00:00",
        "Sidecar",
    )
    # Both invalid
    assert analyzer._calculate_metadata_date("", "") == ("", "")
    # Name date placeholder day=00: prefer EXIF when same month
    assert analyzer._calculate_calc_date("2008-08-12", "2008-08-00") == "2008-08-12"
    # Name date placeholder day=00: keep Name date when EXIF is much later
    assert analyzer._calculate_calc_date("2025-01-02", "2008-08-00") == "2008-08-00"


def test_calculate_calc_filename():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    # Full data available
    calc_date = "2024-10-15"
    time_part = "1430"
    exif = {"ImageWidth": 1920, "ImageHeight": 1080}
    result = analyzer._calculate_calc_filename(calc_date, time_part, exif, "MyEvent", "IMG_4120", "jpg")
    assert result.startswith("2024-10-15_1430_1920x1080_MyEvent_")
    assert result.endswith(".jpg")
    # Missing time component
    result = analyzer._calculate_calc_filename(calc_date, "", exif, "MyEvent", "IMG_4120", "jpg")
    assert "_0000_" in result  # Should use 0000 for time
    # Date-only parent (should be skipped)
    result = analyzer._calculate_calc_filename(calc_date, time_part, exif, "2024-10", "IMG_4120", "jpg")
    assert "2024-10" not in result or result.count("2024-10") == 1  # Only in date prefix
    # Missing dimensions
    result = analyzer._calculate_calc_filename(calc_date, time_part, {}, "MyEvent", "IMG_4120", "jpg")
    assert "_0x0_" in result


def test_calculate_calc_path():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    # Standard case - now includes source_root in path
    result = analyzer._calculate_calc_path("2024-10-15", "MyEvent", "2024-10-15_1430_1920x1080_MyEvent_IMG_4120.jpg")
    assert "/tmp/2020+/2024/2024-10/MyEvent" == result
    # Date-only parent folder - should not include parent in path
    result = analyzer._calculate_calc_path("2024-10-15", "2024-10", "2024-10-15_1430_1920x1080_IMG_4120.jpg")
    assert result == "/tmp/2020+/2024/2024-10"
    # Different decade
    result = analyzer._calculate_calc_path("1995-05-20", "Event", "1995-05-20_1200_800x600_Event_photo.jpg")
    assert result == "/tmp/1990+/1995/1995-05/Event"


def test_calculate_calc_status():
    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    assert analyzer._calculate_calc_status(
        "/root/2024/2024-10/img.jpg",
        "/root/2024/2024-10",
        "img.jpg",
    ) == "MATCH"
    assert analyzer._calculate_calc_status(
        "/root/2024/2024-10/img.jpg",
        "/root/2024/2024-10",
        "img2.jpg",
    ) == "RENAME"
    assert analyzer._calculate_calc_status(
        "/root/2024/2024-10/img.jpg",
        "/root/2024/2024-11",
        "img.jpg",
    ) == "MOVE"


def test_calculate_calc_filename_with_real_exif():
    """Integration test with actual EXIF extraction from real image file."""
    pytest.importorskip("PIL")
    # Create a minimal image file
    from PIL import Image
    import tempfile

    analyzer = ImageAnalyzer("/tmp", logger=_DummyLogger())
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_image_path = Path(tmpdir) / "test_image.jpg"
        # Create a minimal 1920x1080 JPEG
        img = Image.new("RGB", (1920, 1080), color="red")
        img.save(test_image_path)
        
        # Mock exiftool to return dimensions
        exif = {"ImageWidth": 1920, "ImageHeight": 1080}
        
        calc_date = "2024-10-15"
        time_part = "1430"
        result = analyzer._calculate_calc_filename(
            calc_date, time_part, exif, "Vacation", test_image_path.stem, "jpg"
        )
        
        # Verify format: YYYY-MM-DD_HHMM_WIDTHxHEIGHT_PARENT_BASENAME.EXT
        assert result.startswith("2024-10-15_1430_1920x1080_Vacation_")
        assert result.endswith(".jpg")


def test_csv_output_includes_calc_columns(tmp_path):
    """Integration test: verify CSV output includes all Calc columns."""
    analyzer = ImageAnalyzer(str(tmp_path), logger=_DummyLogger())
    
    # Create a test image file
    test_image = tmp_path / "2024-10-15_IMG_4120.jpg"
    test_image.write_text("dummy image data")
    
    # Run analyze_to_csv
    csv_path = tmp_path / "output.csv"
    analyzer.analyze_to_csv(str(csv_path))
    
    # Read CSV and verify columns
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        row = next(reader)
        
        # Verify all original columns present
        assert "Filenanme" in row
        assert "Folder Date" in row
        assert "EXIF Date" in row
        assert "EXIF Ext" in row
        assert "Metadata Date" in row
        assert "Calc Date Used" in row
        assert "Calc Time Used" in row
        assert "Meta - Name" in row
        assert "Calc Description" in row
        assert "Calc Tags" in row
        assert "Calc Offset" in row
        assert "Calc Timezone" in row
        
        # Verify new Calc columns present
        assert "Calc Date" in row
        assert "Calc Filename" in row
        assert "Calc Path" in row
        
        # Verify Calc columns are populated (not empty)
        assert row["Calc Filename"]  # Should have calculated filename
        assert row["Calc Path"]  # Should have calculated path
        assert row["Calc Offset"]
        assert row["Calc Timezone"]


class _DummyLogger:
    def info(self, *_args, **_kwargs):
        return None

    def error(self, *_args, **_kwargs):
        return None

    def warning(self, *_args, **_kwargs):
        return None

    def audit(self, *_args, **_kwargs):
        return None


class _ListLogger:
    def __init__(self):
        self.infos = []
        self.errors = []

    def info(self, msg, *_args, **_kwargs):
        self.infos.append(str(msg))

    def error(self, msg, *_args, **_kwargs):
        self.errors.append(str(msg))

    def warning(self, *_args, **_kwargs):
        return None

    def audit(self, *_args, **_kwargs):
        return None
