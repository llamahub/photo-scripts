#!/usr/bin/env python3
"""Naming policy utilities for normalized file paths and filenames.

This module centralizes the naming convention used across analyze/update/cache flows.
Current convention matches the logic in image_analyzer.py and image_updater.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class NamingInputs:
    """Inputs required to compute normalized names and paths."""

    source_root: str
    calc_date: str
    calc_time: str
    width: int | None
    height: int | None
    parent_folder: str
    original_basename: str
    ext: str
    original_path: str | None = None


@dataclass(frozen=True)
class NamingResult:
    """Computed normalized naming fields."""

    calc_filename: str
    calc_path: str
    calc_status: str
    parent_desc: str
    basename: str


class NamingPolicy:
    """Naming policy that mirrors existing analyzer/updater conventions."""

    @staticmethod
    def build(inputs: NamingInputs) -> NamingResult:
        parent_desc = NamingPolicy.extract_descriptive_parent_folder(inputs.parent_folder)
        dimensions = NamingPolicy.format_dimensions(inputs.width, inputs.height)
        basename = NamingPolicy.strip_duplicate_info_from_basename(
            inputs.original_basename,
            inputs.parent_folder,
            dimensions,
        )
        calc_filename = NamingPolicy.calculate_calc_filename(
            calc_date=inputs.calc_date,
            time_part=inputs.calc_time,
            dimensions=dimensions,
            parent_desc=parent_desc,
            basename=basename,
            ext=inputs.ext,
        )
        calc_path = NamingPolicy.calculate_calc_path(
            source_root=inputs.source_root,
            calc_date=inputs.calc_date,
            parent_folder=inputs.parent_folder,
        )
        calc_status = NamingPolicy.calculate_calc_status(
            inputs.original_path,
            calc_path,
            calc_filename,
        )
        return NamingResult(
            calc_filename=calc_filename,
            calc_path=calc_path,
            calc_status=calc_status,
            parent_desc=parent_desc,
            basename=basename,
        )

    @staticmethod
    def format_dimensions(width: int | None, height: int | None) -> str:
        if width and height:
            return f"{width}x{height}"
        return "0x0"

    @staticmethod
    def extract_descriptive_parent_folder(parent_name: str) -> str:
        """Extract non-date text from parent folder name, or return empty if date-only."""
        if NamingPolicy.is_date_only(parent_name):
            return ""
        parent_name = re.sub(r"_\d+$", "", parent_name)
        return parent_name

    @staticmethod
    def is_date_only(folder_name: str) -> bool:
        """Return True if folder name is purely date-based."""
        if not folder_name:
            return True
        if re.match(r"^\d{4}([_-]\d{2}([_-]\d{2})?)?(_\d+)?$", folder_name):
            return True
        cleaned = re.sub(r"[_\-]?(\d{4}(?:[_\-]\d{2})?(?:[_\-]\d{2})?)", "", folder_name)
        cleaned = cleaned.strip("_-").strip()
        return not cleaned

    @staticmethod
    def strip_duplicate_info_from_basename(
        basename: str,
        parent_folder: str,
        dimensions: str,
    ) -> str:
        """Remove duplicate date, dimensions, and parent info from basename."""
        if not basename:
            return ""

        basename = re.sub(r"^\d{4}-\d{2}-\d{2}_\d{4}_\d+x\d+_", "", basename)

        parent_desc = NamingPolicy.extract_descriptive_parent_folder(parent_folder)
        if parent_desc:
            if basename.startswith(parent_desc):
                basename = basename[len(parent_desc):].lstrip("_").strip()
            else:
                parent_pattern = re.sub(r"[\s_-]+", "_", parent_desc)
                if basename.startswith(parent_pattern):
                    basename = basename[len(parent_pattern):].lstrip("_").strip()

        return basename if basename else "UNKNOWN"

    @staticmethod
    def calculate_calc_filename(
        *,
        calc_date: str,
        time_part: str,
        dimensions: str,
        parent_desc: str,
        basename: str,
        ext: str,
    ) -> str:
        """Calculate normalized filename: YYYY-MM-DD_HHMM_WIDTHxHEIGHT_PARENT_BASENAME.ext"""
        if not calc_date:
            return f"{basename}.{ext}" if ext else basename

        date_part = calc_date[:10] if len(calc_date) >= 10 else calc_date
        time_part = time_part or "0000"

        if parent_desc:
            filename = f"{date_part}_{time_part}_{dimensions}_{parent_desc}_{basename}.{ext}"
        else:
            filename = f"{date_part}_{time_part}_{dimensions}_{basename}.{ext}"

        return filename

    @staticmethod
    def calculate_calc_path(source_root: str, calc_date: str, parent_folder: str) -> str:
        """Calculate organized folder path: root/decade+/year/year-month/parent_desc."""
        if not calc_date or len(calc_date) < 10:
            return str(Path(source_root))

        year = calc_date[:4]
        month = calc_date[5:7]

        try:
            year_int = int(year)
            decade = (year_int // 10) * 10
        except ValueError:
            decade = 0

        parent_desc = NamingPolicy.extract_descriptive_parent_folder(parent_folder)
        if parent_desc:
            path = str(Path(source_root) / f"{decade}+/{year}/{year}-{month}/{parent_desc}")
        else:
            path = str(Path(source_root) / f"{decade}+/{year}/{year}-{month}")

        return path

    @staticmethod
    def calculate_calc_status(
        original_path: str | None,
        calc_path: str,
        calc_filename: str,
    ) -> str:
        """Return MATCH, RENAME, MOVE based on original vs calculated path."""
        if not original_path:
            return "MOVE"

        reconstructed_path = str(Path(calc_path) / calc_filename)
        if original_path == reconstructed_path:
            return "MATCH"

        orig_parent = str(Path(original_path).parent)
        calc_parent = str(Path(calc_path))
        if orig_parent == calc_parent:
            return "RENAME"

        return "MOVE"

    @staticmethod
    def normalize_calc_filename(
        calc_filename: str,
        exif_datetime: str,
        calc_path: str,
    ) -> str:
        """Normalize filename date prefix and reduce parent double-underscore artifacts."""
        normalized = calc_filename or ""

        if exif_datetime:
            date_part = exif_datetime.split(" ")[0].replace(":", "-")
            if re.match(r"^\d{4}-\d{2}-\d{2}$", date_part):
                if re.match(r"^\d{4}-\d{2}-\d{2}", normalized):
                    normalized_date = normalized[:10]
                    if normalized_date != date_part:
                        normalized = date_part + normalized[10:]

        parent_desc = Path(calc_path).name if calc_path else ""
        if parent_desc:
            normalized = normalized.replace(f"{parent_desc}__", f"{parent_desc}_", 1)

        return normalized
