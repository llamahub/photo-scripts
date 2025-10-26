#!/usr/bin/env python3
"""Unit tests for exif_info single-file flow (new test file).

This test verifies that ImageAnalyzer.analyze_single_summary returns the
requested raw EXIF date fields and that a compact CSV can be written using
those keys (simulating the updated script behavior).
"""

import os
import csv
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
# Adjust path for tests location
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from exif.image_analyzer import ImageAnalyzer
from exif import image_analyzer


def test_analyze_single_summary_returns_date_fields(tmp_path, monkeypatch):
    # Prepare a fake input file
    input_file = tmp_path / "img.jpg"
    input_file.write_text("")

    # Example EXIF data returned by get_exif
    exif_data = {
        "DateTimeOriginal": "2023:06:15 12:30:00",
        "ExifIFD:DateTimeOriginal": "2023:06:15 12:30:00",
        "XMP-photoshop:DateCreated": "2023:06:15 00:00:00",
        "CreateDate": "2023:06:15 12:30:00",
        "ModifyDate": "2023:06:15 12:30:00",
        "MediaCreateDate": "",
        "MediaModifyDate": "",
        "TrackCreateDate": "",
        "TrackModifyDate": "",
        "FileModifyDate": "2023:06:15 12:30:00",
        "FileTypeExtension": "jpg",
        "ImageWidth": 4000,
        "ImageHeight": 3000,
        "Description": "Unit test image",
        "Keywords": ["one", "two"],
    }

    # Patch ImageData.get_exif and other helpers used by analyze_single_summary
    monkeypatch.setattr(
        image_analyzer.ImageData, "get_exif", staticmethod(lambda p: exif_data)
    )
    monkeypatch.setattr(
        image_analyzer.ImageData, "getTrueExt", staticmethod(lambda p: "jpg")
    )
    monkeypatch.setattr(
        image_analyzer.ImageData,
        "getImageDate",
        staticmethod(lambda p: "2023-06-15 12:30:00"),
    )
    monkeypatch.setattr(
        image_analyzer.ImageData,
        "getFilenameDate",
        staticmethod(lambda p: "2023-06-15 00:00:00"),
    )
    monkeypatch.setattr(
        image_analyzer.ImageData, "getParentName", staticmethod(lambda p: "2023-06")
    )
    monkeypatch.setattr(
        image_analyzer.ImageData,
        "normalize_parent_date",
        staticmethod(lambda p: "2023-06-01 00:00:00"),
    )
    monkeypatch.setattr(
        image_analyzer.ImageData,
        "getTargetFilename",
        staticmethod(lambda p, root: "/tmp/target.jpg"),
    )

    analyzer = ImageAnalyzer()

    summary = analyzer.analyze_single_summary(str(input_file))

    # Ensure requested keys exist and match the mocked values
    assert summary["DateTimeOriginal"] == exif_data["DateTimeOriginal"]
    assert summary["ExifIFD:DateTimeOriginal"] == exif_data["ExifIFD:DateTimeOriginal"]
    assert (
        summary["XMP-photoshop:DateCreated"] == exif_data["XMP-photoshop:DateCreated"]
    )
    assert summary["CreateDate"] == exif_data["CreateDate"]
    assert summary["ModifyDate"] == exif_data["ModifyDate"]
    assert summary["FileModifyDate"] == exif_data["FileModifyDate"]
    assert summary["FileTypeExtension"] == exif_data["FileTypeExtension"]

    # Simulate writing CSV as the script does
    out_csv = tmp_path / "out.csv"
    os.makedirs(os.path.dirname(str(out_csv)), exist_ok=True)
    with open(str(out_csv), "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary.keys()))
        writer.writeheader()
        row = {
            k: (",".join(v) if isinstance(v, list) else v) for k, v in summary.items()
        }
        writer.writerow(row)

    with open(str(out_csv), "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["DateTimeOriginal"] == exif_data["DateTimeOriginal"]
    # analyzer returns 'description' (lowercase) as the key
    assert rows[0].get("description") == exif_data["Description"]
