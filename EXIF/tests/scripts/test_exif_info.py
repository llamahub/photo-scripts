#!/usr/bin/env python3
"""Unit tests for the exif_info script (single-file flow)."""
#!/usr/bin/env python3
"""Unit tests for the exif_info script (single-file flow)."""

import os
import tempfile
import shutil
from unittest.mock import patch
import csv

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from exif.image_analyzer import ImageAnalyzer
from exif import image_analyzer


def test_analyze_single_summary_and_script_writes_csv(tmp_path, monkeypatch):
    # Create a temporary input file
    input_file = tmp_path / "test.jpg"
    input_file.write_text("")

    # Mock ImageData.get_exif and other ImageData helpers used by analyze_single_summary
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
        "ImageWidth": 1920,
        "ImageHeight": 1080,
        "Description": "Test description",
        "Keywords": "tag1,tag2",
    }

    # Patch ImageData.get_exif and the helper methods used
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

    # Verify the returned fields include the requested date keys
    assert summary["DateTimeOriginal"] == exif_data["DateTimeOriginal"]
    assert summary["ExifIFD:DateTimeOriginal"] == exif_data["ExifIFD:DateTimeOriginal"]
    assert (
        summary["XMP-photoshop:DateCreated"] == exif_data["XMP-photoshop:DateCreated"]
    )
    assert summary["CreateDate"] == exif_data["CreateDate"]
    assert summary["FileModifyDate"] == exif_data["FileModifyDate"]
    assert summary["FileTypeExtension"] == exif_data["FileTypeExtension"]

    # Now simulate the script writing a CSV for the single file
    out_csv = tmp_path / "out.csv"

    # Use the same logic as the script: write header from keys and the single row
    os.makedirs(os.path.dirname(str(out_csv)), exist_ok=True)
    with open(str(out_csv), "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary.keys()))
        writer.writeheader()
        row = {
            k: (",".join(v) if isinstance(v, list) else v) for k, v in summary.items()
        }
        writer.writerow(row)

    # Read back CSV and assert content
    with open(str(out_csv), "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["DateTimeOriginal"] == exif_data["DateTimeOriginal"]
    # analyzer returns lowercase 'description' key in summaries when writing CSV; check either
    assert (
        rows[0].get("Description", rows[0].get("description"))
        == exif_data["Description"]
    )
