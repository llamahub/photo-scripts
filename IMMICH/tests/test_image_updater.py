#!/usr/bin/env python3
"""Tests for IMMICH ImageUpdater business logic."""

from pathlib import Path

import csv
import json
import shutil
import subprocess

from image_updater import ImageUpdater


class _DummyLogger:
    def __init__(self):
        self.audits = []
        self.infos = []
        self.errors = []
        self.warnings = []
        self.debugs = []

    def info(self, message, *args, **kwargs):
        self.infos.append(message % args if args else message)

    def warning(self, message, *args, **kwargs):
        self.warnings.append(message % args if args else message)

    def error(self, message, *args, **kwargs):
        self.errors.append(message % args if args else message)

    def debug(self, message, *args, **kwargs):
        self.debugs.append(message % args if args else message)

    def audit(self, message, *args, **kwargs):
        self.audits.append(message % args if args else message)


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def test_selected_values():
    updater = ImageUpdater("/tmp/none.csv", logger=_DummyLogger(), dry_run=True)
    assert updater._is_selected("Y")
    assert updater._is_selected("yes")
    assert updater._is_selected("TRUE")
    assert not updater._is_selected("no")


def test_process_csv_dry_run(tmp_path):
    image_path = tmp_path / "photo.jpg"
    image_path.write_text("data")

    csv_path = tmp_path / "analyze.csv"
    _write_csv(
        csv_path,
        [
            {
                "Filenanme": str(image_path),
                "Calc Description": "desc",
                "Calc Tags": "tag1; tag2",
                "Calc Date": "2024-01-02",
                "Calc Filename": "2024-01-02_1430_1920x1080_test.jpg",
                "Calc Path": str(tmp_path),
                "Calc Status": "MATCH",
                "Calc Time Used": "Filename",
                "Select": "Y",
            }
        ],
    )

    logger = _DummyLogger()
    updater = ImageUpdater(str(csv_path), logger=logger, dry_run=True)
    stats = updater.process()

    assert stats["rows_total"] == 1
    assert stats["rows_selected"] == 1
    assert stats["exif_updated"] == 1
    assert image_path.exists()
    assert logger.audits


def test_resolve_offset_from_timezone(tmp_path, monkeypatch):
    image_path = tmp_path / "photo.jpg"
    image_path.write_text("data")

    csv_path = tmp_path / "analyze.csv"
    _write_csv(
        csv_path,
        [
            {
                "Filenanme": str(image_path),
                "Calc Description": "",
                "Calc Tags": "",
                "Calc Date": "2024-01-02",
                "Calc Filename": "2024-01-02_1430_1920x1080_test.jpg",
                "Calc Path": str(tmp_path),
                "Calc Status": "MATCH",
                "Calc Time Used": "",
                "Calc Timezone": "UTC",
                "Select": "Y",
            }
        ],
    )

    logger = _DummyLogger()
    updater = ImageUpdater(str(csv_path), logger=logger, dry_run=True)
    updater.exiftool_available = True

    captured = {"offset": None}

    def capture_update(_file, _desc, _tags, _dt, offset):
        captured["offset"] = offset
        return "updated"

    monkeypatch.setattr(updater, "_update_exif", capture_update)

    stats = updater.process()
    assert stats["exif_updated"] == 1
    assert captured["offset"] == "+00:00"


def test_process_csv_move(tmp_path, monkeypatch):
    image_path = tmp_path / "photo.jpg"
    image_path.write_text("data")

    target_dir = tmp_path / "target"
    target_name = "2024-01-02_0000_1920x1080_photo.jpg"

    csv_path = tmp_path / "analyze.csv"
    _write_csv(
        csv_path,
        [
            {
                "Filenanme": str(image_path),
                "Calc Description": "",
                "Calc Tags": "",
                "Calc Date": "2024-01-02",
                "Calc Filename": target_name,
                "Calc Path": str(target_dir),
                "Calc Status": "MOVE",
                "Calc Time Used": "",
                "Select": "YES",
            }
        ],
    )

    logger = _DummyLogger()
    updater = ImageUpdater(str(csv_path), logger=logger, dry_run=False)
    updater.exiftool_available = True
    monkeypatch.setattr(updater, "_update_exif", lambda *_args, **_kwargs: "updated")

    stats = updater.process()
    moved_path = target_dir / target_name

    assert stats["moved"] == 1
    assert moved_path.exists()
    assert not image_path.exists()


def test_process_missing_select_column(tmp_path):
    csv_path = tmp_path / "analyze.csv"
    _write_csv(
        csv_path,
        [
            {
                "Filenanme": "file.jpg",
                "Calc Status": "MATCH",
            }
        ],
    )

    updater = ImageUpdater(str(csv_path), logger=_DummyLogger(), dry_run=True)
    try:
        updater.process()
    except ValueError as exc:
        assert "selection column" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError for missing selection column")


def test_process_row_missing_file(tmp_path):
    csv_path = tmp_path / "analyze.csv"
    _write_csv(
        csv_path,
        [
            {
                "Filenanme": str(tmp_path / "missing.jpg"),
                "Calc Status": "MATCH",
                "Select": "Y",
            }
        ],
    )

    logger = _DummyLogger()
    updater = ImageUpdater(str(csv_path), logger=logger, dry_run=True)
    stats = updater.process()

    assert stats["errors"] == 1
    assert any("not found" in msg.lower() for msg in logger.errors)


def test_apply_file_action_dry_run(tmp_path):
    image_path = tmp_path / "photo.jpg"
    image_path.write_text("data")
    target_dir = tmp_path / "target"

    updater = ImageUpdater("/tmp/none.csv", logger=_DummyLogger(), dry_run=True)
    result = updater._apply_file_action(
        str(image_path), "MOVE", str(target_dir), "renamed.jpg"
    )

    assert result == "moved"
    assert image_path.exists()


def test_apply_file_action_missing_targets(tmp_path):
    image_path = tmp_path / "photo.jpg"
    image_path.write_text("data")

    logger = _DummyLogger()
    updater = ImageUpdater("/tmp/none.csv", logger=logger, dry_run=True)
    result = updater._apply_file_action(str(image_path), "MOVE", "", "")

    assert result == "error"
    assert any("missing calc path" in msg.lower() for msg in logger.errors)


def test_offset_from_invalid_timezone(tmp_path, monkeypatch):
    image_path = tmp_path / "photo.jpg"
    image_path.write_text("data")
    csv_path = tmp_path / "analyze.csv"

    _write_csv(
        csv_path,
        [
            {
                "Filenanme": str(image_path),
                "Calc Description": "",
                "Calc Tags": "",
                "Calc Date": "2024-01-02",
                "Calc Filename": "2024-01-02_1430_1920x1080_test.jpg",
                "Calc Path": str(tmp_path),
                "Calc Status": "MATCH",
                "Calc Time Used": "",
                "Calc Timezone": "Invalid/Zone",
                "Select": "Y",
            }
        ],
    )

    logger = _DummyLogger()
    updater = ImageUpdater(str(csv_path), logger=logger, dry_run=True)
    updater.exiftool_available = True

    captured = {"offset": None}

    def capture_update(_file, _desc, _tags, _dt, offset):
        captured["offset"] = offset
        return "updated"

    monkeypatch.setattr(updater, "_update_exif", capture_update)

    stats = updater.process()
    assert stats["exif_updated"] == 1
    assert captured["offset"] == ""
    assert any("invalid calc timezone" in msg.lower() for msg in logger.warnings)


def test_format_exif_datetime_patterns():
    updater = ImageUpdater("/tmp/none.csv", logger=_DummyLogger(), dry_run=True)

    assert (
        updater._format_exif_datetime("11/26/23 9:11", "")
        == "2023:11:26 09:11:00"
    )
    assert (
        updater._format_exif_datetime("11/26/23", "")
        == "2023:11:26 00:00:00"
    )
    assert (
        updater._format_exif_datetime("2023-11-26", "")
        == "2023:11:26 00:00:00"
    )
    assert (
        updater._format_exif_datetime("2023-11-26 09:11", "")
        == "2023:11:26 09:11:00"
    )
    assert (
        updater._format_exif_datetime("2023-11-26 09:11:12", "")
        == "2023:11:26 09:11:12"
    )
    assert (
        updater._format_exif_datetime("2023-11-00", "")
        == "2023:11:01 00:00:00"
    )
    assert (
        updater._format_exif_datetime("2023-00-00", "")
        == "2023:01:01 00:00:00"
    )
    assert (
        updater._format_exif_datetime("2023-11-26", "2023-11-26_0911_test.jpg")
        == "2023:11:26 09:11:00"
    )
    assert updater._format_exif_datetime("", "") == ""
    assert updater._format_exif_datetime("not-a-date", "") == ""


def test_update_exif_with_real_exiftool(tmp_path):
    if shutil.which("exiftool") is None:
        return

    try:
        from PIL import Image
    except ImportError:
        return

    image_path = tmp_path / "photo.jpg"
    image = Image.new("RGB", (16, 16), color="red")
    image.save(image_path, format="JPEG")

    logger = _DummyLogger()
    updater = ImageUpdater(str(tmp_path / "none.csv"), logger=logger, dry_run=False)

    result = updater._update_exif(
        str(image_path),
        "Test Description",
        ["tag1", "tag2"],
        "2024:01:02 03:04:05",
        "+00:00",
    )

    assert result == "updated"

    exif = subprocess.run(
        ["exiftool", "-j", str(image_path)],
        capture_output=True,
        check=True,
        text=True,
    )
    data = json.loads(exif.stdout)[0]
    assert data.get("Description") == "Test Description"
    assert data.get("DateTimeOriginal") == "2024:01:02 03:04:05"
    assert data.get("OffsetTimeOriginal") == "+00:00"
    keywords = data.get("Keywords") or []
    if isinstance(keywords, str):
        keywords = [keywords]
    assert "tag1" in keywords
    assert "tag2" in keywords
