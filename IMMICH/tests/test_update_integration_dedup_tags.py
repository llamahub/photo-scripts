#!/usr/bin/env python3
"""Integration test: update script removes duplicate EXIF tags using exiftool live."""


import shutil
import subprocess
import tempfile
from pathlib import Path
import pytest
import sys
import update

# Mark this file as integration test
pytestmark = pytest.mark.integration

SAMPLE_IMAGE = "testdata/sample_with_duplicate_tags.jpg"

@pytest.fixture
def temp_image(tmp_path):
    # Copy sample image to temp dir for safe modification
    temp_img = tmp_path / "sample.jpg"
    shutil.copy(SAMPLE_IMAGE, temp_img)
    return temp_img

@pytest.fixture
def csv_file(tmp_path, temp_image):
    # Create a CSV referencing the temp image, with a single unique tag in Calc Tags
    csv = tmp_path / "analyze.csv"
    csv.write_text(
        f"Filename,Select,Calc Tags\n{temp_image},y,ARCHIVE_DUP\n"
    )
    return csv

def get_exif_tags(image_path):
    # Use exiftool to read tags as a list
    result = subprocess.run([
        "exiftool", "-Subject", "-Keywords", "-XMP:Subject", "-IPTC:Keywords", str(image_path)
    ], capture_output=True, text=True, check=True)
    tags = {}
    for line in result.stdout.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            tags[k.strip()] = [t.strip() for t in v.split(",") if t.strip()]
    return tags

def test_update_removes_duplicate_tags(csv_file, tmp_path, monkeypatch):
    # Run update script with live exiftool
    monkeypatch.setattr(sys, "argv", ["update.py", "--input", str(csv_file)])
    rc = update.main()
    assert rc == 0
    # Check tags after update
    tags = get_exif_tags(csv_file.read_text().splitlines()[1].split(",")[0])
    # Allow XMP Subject to be missing, but at least one field must contain the tag
    found = False
    for field in ("Subject", "Keywords", "IPTC Keywords"):
        if tags.get(field) == ["ARCHIVE_DUP"]:
            found = True
    assert found, f"Tag not found in any EXIF field: {tags}"
    # If XMP Subject exists, it must be correct
    if "XMP Subject" in tags:
        assert tags["XMP Subject"] == ["ARCHIVE_DUP"], f"Duplicates remain in XMP Subject: {tags.get('XMP Subject')}"
