#!/usr/bin/env python3
"""Tests for naming policy utilities."""

from naming_policy import NamingInputs, NamingPolicy


def test_is_date_only():
    assert NamingPolicy.is_date_only("2024-10-15") is True
    assert NamingPolicy.is_date_only("2024-10") is True
    assert NamingPolicy.is_date_only("2024") is True
    assert NamingPolicy.is_date_only("2024_10_15") is True
    assert NamingPolicy.is_date_only("2024-10-15_01") is True
    assert NamingPolicy.is_date_only("2024-10-Vacation") is False
    assert NamingPolicy.is_date_only("MyEvent") is False
    assert NamingPolicy.is_date_only("") is True


def test_extract_descriptive_parent_folder():
    assert NamingPolicy.extract_descriptive_parent_folder("2024-10") == ""
    assert NamingPolicy.extract_descriptive_parent_folder("2024-10-15") == ""
    assert NamingPolicy.extract_descriptive_parent_folder("2024-10-15_01") == ""
    assert NamingPolicy.extract_descriptive_parent_folder("2024-10-Vacation") == "2024-10-Vacation"
    assert NamingPolicy.extract_descriptive_parent_folder("MyEvent") == "MyEvent"
    assert NamingPolicy.extract_descriptive_parent_folder("") == ""


def test_strip_duplicate_info_from_basename():
    result = NamingPolicy.strip_duplicate_info_from_basename(
        basename="2024-10-15_1430_1920x1080_MyEvent_IMG_4120",
        parent_folder="MyEvent",
        dimensions="1920x1080",
    )
    assert result == "IMG_4120"

    result = NamingPolicy.strip_duplicate_info_from_basename(
        basename="MyEvent_IMG_4120",
        parent_folder="MyEvent",
        dimensions="0x0",
    )
    assert result == "IMG_4120"

    result = NamingPolicy.strip_duplicate_info_from_basename(
        basename="2024-10-15_1430_1920x1080_IMG_4120",
        parent_folder="2024-10",
        dimensions="1920x1080",
    )
    assert result == "IMG_4120"

    result = NamingPolicy.strip_duplicate_info_from_basename(
        basename="2008-10-19 Cub Scout Camp_DSCN5110",
        parent_folder="2008-10-19 Cub Scout Camp_01",
        dimensions="3072x2304",
    )
    assert result == "DSCN5110"


def test_calculate_calc_filename():
    result = NamingPolicy.calculate_calc_filename(
        calc_date="2024-10-15",
        time_part="1430",
        dimensions="1920x1080",
        parent_desc="MyEvent",
        basename="IMG_4120",
        ext="jpg",
    )
    assert result == "2024-10-15_1430_1920x1080_MyEvent_IMG_4120.jpg"

    result = NamingPolicy.calculate_calc_filename(
        calc_date="2024-10-15",
        time_part="1430",
        dimensions="1920x1080",
        parent_desc="",
        basename="IMG_4120",
        ext="jpg",
    )
    assert result == "2024-10-15_1430_1920x1080_IMG_4120.jpg"


def test_calculate_calc_path():
    result = NamingPolicy.calculate_calc_path(
        source_root="/photos",
        calc_date="2024-10-15",
        parent_folder="MyEvent",
    )
    assert result == "/photos/2020+/2024/2024-10/MyEvent"

    result = NamingPolicy.calculate_calc_path(
        source_root="/photos",
        calc_date="2024-10-15",
        parent_folder="2024-10",
    )
    assert result == "/photos/2020+/2024/2024-10"


def test_calculate_calc_status():
    assert (
        NamingPolicy.calculate_calc_status(
            "/photos/2020+/2024/2024-10/MyEvent/2024-10-15_1430_1920x1080_MyEvent_IMG_1.jpg",
            "/photos/2020+/2024/2024-10/MyEvent",
            "2024-10-15_1430_1920x1080_MyEvent_IMG_1.jpg",
        )
        == "MATCH"
    )

    assert (
        NamingPolicy.calculate_calc_status(
            "/photos/2020+/2024/2024-10/MyEvent/IMG_1.jpg",
            "/photos/2020+/2024/2024-10/MyEvent",
            "2024-10-15_1430_1920x1080_MyEvent_IMG_1.jpg",
        )
        == "RENAME"
    )

    assert (
        NamingPolicy.calculate_calc_status(
            "/photos/2020+/2024/2024-09/MyEvent/IMG_1.jpg",
            "/photos/2020+/2024/2024-10/MyEvent",
            "2024-10-15_1430_1920x1080_MyEvent_IMG_1.jpg",
        )
        == "MOVE"
    )

    assert (
        NamingPolicy.calculate_calc_status(
            None,
            "/photos/2020+/2024/2024-10/MyEvent",
            "2024-10-15_1430_1920x1080_MyEvent_IMG_1.jpg",
        )
        == "MOVE"
    )


def test_normalize_calc_filename():
    calc_path = "/photos/2020+/2024/2024-10/MyEvent"
    normalized = NamingPolicy.normalize_calc_filename(
        calc_filename="2024-10-14_1430_1920x1080_MyEvent_IMG_1.jpg",
        exif_datetime="2024:10:15 10:00:00",
        calc_path=calc_path,
    )
    assert normalized.startswith("2024-10-15_1430_1920x1080_MyEvent_IMG_1.jpg")

    normalized = NamingPolicy.normalize_calc_filename(
        calc_filename="2024-10-15_1430_1920x1080_MyEvent__IMG_1.jpg",
        exif_datetime="",
        calc_path=calc_path,
    )
    assert "MyEvent__" not in normalized


def test_build():
    inputs = NamingInputs(
        source_root="/photos",
        calc_date="2024-10-15",
        calc_time="1430",
        width=1920,
        height=1080,
        parent_folder="MyEvent",
        original_basename="IMG_4120",
        ext="jpg",
        original_path="/photos/2020+/2024/2024-10/MyEvent/IMG_4120.jpg",
    )
    result = NamingPolicy.build(inputs)
    assert result.calc_filename == "2024-10-15_1430_1920x1080_MyEvent_IMG_4120.jpg"
    assert result.calc_path == "/photos/2020+/2024/2024-10/MyEvent"
    assert result.calc_status in {"RENAME", "MOVE", "MATCH"}
