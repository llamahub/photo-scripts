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
