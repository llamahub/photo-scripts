#!/usr/bin/env python3
"""Image analyzer for IMMICH analyze script."""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".gif",
    ".bmp",
    ".webp",
    ".heic",
    ".heif",
    ".dng",
    ".cr2",
    ".nef",
    ".arw",
}

SIDECAR_EXTENSIONS = [".xmp", ".XMP", ".json", ".JSON"]

EXIF_DATE_PRIORITY = [
    "DateTimeOriginal",
    "ExifIFD:DateTimeOriginal",
    "XMP-photoshop:DateCreated",
    "CreateDate",
    "ModifyDate",
    "MediaCreateDate",
    "MediaModifyDate",
    "TrackCreateDate",
    "TrackModifyDate",
    "FileModifyDate",
]

DESCRIPTION_KEYS = [
    "Description",
    "ImageDescription",
    "XMP:Description",
    "XMP-dc:Description",
    "IPTC:Caption-Abstract",
]

TAGS_KEYS = [
    "Subject",
    "Keywords",
    "XMP:Subject",
    "XMP-dc:Subject",
    "IPTC:Keywords",
]

OFFSET_KEYS = [
    "OffsetTimeOriginal",
    "OffsetTime",
    "OffsetTimeDigitized",
    "TimeZoneOffset",
]

IANA_OFFSET_MAP = {
    -720: "Etc/GMT+12",
    -660: "Pacific/Pago_Pago",
    -600: "Pacific/Honolulu",
    -570: "Pacific/Marquesas",
    -540: "America/Anchorage",
    -480: "America/Los_Angeles",
    -420: "America/Denver",
    -360: "America/Chicago",
    -300: "America/New_York",
    -240: "America/Halifax",
    -210: "America/St_Johns",
    -180: "America/Sao_Paulo",
    -120: "Etc/GMT+2",
    -60: "Atlantic/Cape_Verde",
    0: "UTC",
    60: "Europe/Berlin",
    120: "Europe/Athens",
    180: "Europe/Moscow",
    210: "Asia/Tehran",
    240: "Asia/Dubai",
    270: "Asia/Kabul",
    300: "Asia/Karachi",
    330: "Asia/Kolkata",
    345: "Asia/Kathmandu",
    360: "Asia/Dhaka",
    390: "Asia/Yangon",
    420: "Asia/Bangkok",
    480: "Asia/Singapore",
    540: "Asia/Tokyo",
    570: "Australia/Darwin",
    600: "Australia/Brisbane",
    630: "Australia/Adelaide",
    660: "Australia/Sydney",
    720: "Pacific/Auckland",
}


@dataclass
class ImageRow:
    filename: str
    folder_date: str
    filename_date: str
    sidecar_file: str
    sidecar_date: str
    sidecar_offset: str
    sidecar_timezone: str
    sidecar_description: str
    sidecar_tags: str
    exif_date: str
    exif_offset: str
    exif_timezone: str
    exif_description: str
    exif_tags: str
    exif_ext: str


class ImageAnalyzer:
    """Analyze image library files and emit CSV rows."""

    def __init__(
        self,
        source_root: str,
        logger,
        detect_true_ext: bool = True,
        max_workers: Optional[int] = None,
    ):
        self.source_root = Path(source_root)
        self.logger = logger
        self.detect_true_ext = detect_true_ext
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.exif_timeout_files: List[Path] = []
        self.exiftool_available = shutil.which("exiftool") is not None

        if not self.exiftool_available:
            self.logger.warning("exiftool not found on PATH; EXIF fields will be blank")

    def analyze_to_csv(self, output_csv: str) -> int:
        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        rows = 0
        progress_interval = 50
        max_in_flight = self.max_workers * 4
        file_iter = iter(self._iter_image_files())

        with output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self._csv_headers())
            writer.writeheader()

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = set()

                def submit_next():
                    try:
                        next_path = next(file_iter)
                    except StopIteration:
                        return False
                    futures.add(executor.submit(self._analyze_file, next_path))
                    return True

                for _ in range(max_in_flight):
                    if not submit_next():
                        break

                while futures:
                    done, futures = wait(futures, return_when=FIRST_COMPLETED)
                    for future in done:
                        row = future.result()
                        writer.writerow(self._row_to_dict(row))
                        rows += 1

                        self.logger.audit(
                            f"AUDIT file={row.filename} exif_date={row.exif_date} "
                            f"sidecar_date={row.sidecar_date} status=ok"
                        )

                        if rows % progress_interval == 0:
                            self.logger.info(f"Progress: {rows} files processed")

                    while len(futures) < max_in_flight:
                        if not submit_next():
                            break

        if self.exif_timeout_files:
            self._retry_exif_timeouts()

        return rows

    def _iter_image_files(self) -> Iterable[Path]:
        for path in self.source_root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix in SIDECAR_EXTENSIONS:
                continue
            if path.suffix.lower() in IMAGE_EXTENSIONS:
                yield path

    def _analyze_file(self, file_path: Path) -> ImageRow:
        sidecar_path = self._find_sidecar(file_path)
        sidecar_exif = self._read_exif(sidecar_path) if sidecar_path else {}
        image_exif = self._read_exif(file_path)

        folder_date = self._extract_folder_date(file_path.parent.name)
        filename_date = self._extract_filename_date(file_path.name)

        sidecar_date_raw = self._get_first_exif_value(sidecar_exif, EXIF_DATE_PRIORITY)
        sidecar_date, sidecar_offset_from_date = self._split_datetime_offset(
            sidecar_date_raw
        )
        sidecar_offset = self._get_first_exif_value(sidecar_exif, OFFSET_KEYS)
        if not sidecar_offset:
            sidecar_offset = sidecar_offset_from_date
        sidecar_timezone = self._format_timezone(sidecar_date, sidecar_offset)
        sidecar_description = self._get_first_exif_value(sidecar_exif, DESCRIPTION_KEYS)
        sidecar_tags_value = self._get_first_exif_value(sidecar_exif, TAGS_KEYS)
        sidecar_tags = self._format_tags(sidecar_tags_value)
        if sidecar_path and sidecar_path.suffix.lower() == ".xmp":
            xmp_tags = self._extract_xmp_tags(sidecar_path)
            if xmp_tags:
                sidecar_tags = "; ".join(xmp_tags)

        exif_date_raw = self._get_first_exif_value(image_exif, EXIF_DATE_PRIORITY)
        exif_date, exif_offset_from_date = self._split_datetime_offset(exif_date_raw)
        exif_offset = self._get_first_exif_value(image_exif, OFFSET_KEYS)
        if not exif_offset:
            exif_offset = exif_offset_from_date
        exif_timezone = self._format_timezone(exif_date, exif_offset)
        exif_description = self._get_first_exif_value(image_exif, DESCRIPTION_KEYS)
        exif_tags = self._format_tags(self._get_first_exif_value(image_exif, TAGS_KEYS))
        exif_ext = self._get_true_extension(file_path)

        return ImageRow(
            filename=str(file_path),
            folder_date=folder_date,
            filename_date=filename_date,
            sidecar_file=str(sidecar_path) if sidecar_path else "",
            sidecar_date=sidecar_date,
            sidecar_offset=sidecar_offset,
            sidecar_timezone=sidecar_timezone,
            sidecar_description=sidecar_description,
            sidecar_tags=sidecar_tags,
            exif_date=exif_date,
            exif_offset=exif_offset,
            exif_timezone=exif_timezone,
            exif_description=exif_description,
            exif_tags=exif_tags,
            exif_ext=exif_ext,
        )

    def _find_sidecar(self, file_path: Path) -> Optional[Path]:
        for ext in SIDECAR_EXTENSIONS:
            candidate = file_path.with_suffix(ext)
            if candidate.exists():
                return candidate
        return None

    def _read_exif(self, file_path: Path | None) -> Dict:
        if not file_path or not self.exiftool_available:
            return {}
        return self._read_exif_with_timeout(file_path, timeout=10, track_timeouts=True)

    def _read_exif_with_timeout(
        self, file_path: Path, timeout: int, track_timeouts: bool
    ) -> Dict:
        cmd = ["exiftool", "-j", str(file_path)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            if track_timeouts and file_path not in self.exif_timeout_files:
                self.exif_timeout_files.append(file_path)
            self.logger.error(
                f"EXIF extraction timed out for {file_path} after {timeout}s"
            )
            return {}
        except Exception as exc:
            self.logger.error(f"EXIF extraction failed for {file_path}: {exc}")
            return {}

        if result.returncode != 0 or not result.stdout:
            return {}

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return {}

        if not data:
            return {}

        return data[0] if isinstance(data, list) else data

    def _retry_exif_timeouts(self) -> None:
        retry_timeout = 30
        total = len(self.exif_timeout_files)
        self.logger.info(
            f"Retrying EXIF timeouts sequentially ({total} files, timeout={retry_timeout}s)"
        )

        for path in self.exif_timeout_files:
            data = self._read_exif_with_timeout(
                path, timeout=retry_timeout, track_timeouts=False
            )
            if data:
                self.logger.info(f"EXIF retry succeeded: {path}")
            else:
                self.logger.error(f"EXIF retry failed: {path}")

    def _extract_folder_date(self, folder_name: str) -> str:
        date_match = re.search(r"(\d{4})[-_]?([01]\d)?[-_]?([0-3]\d)?", folder_name)
        if not date_match:
            return ""

        year = date_match.group(1)
        month = date_match.group(2) or "00"
        day = date_match.group(3) or "00"
        return f"{year}-{month}-{day}"

    def _extract_filename_date(self, filename: str) -> str:
        stem = Path(filename).stem
        start_match = re.match(r"^(\d{4})[-_]?([01]\d)[-_]?([0-3]\d)", stem)
        if start_match:
            return f"{start_match.group(1)}-{start_match.group(2)}-{start_match.group(3)}"

        search_match = re.search(r"(\d{4})[-_]?([01]\d)[-_]?([0-3]\d)", stem)
        if search_match:
            return f"{search_match.group(1)}-{search_match.group(2)}-{search_match.group(3)}"

        year_match = re.search(r"(\d{4})[-_]?([01]\d)?[-_]?([0-3]\d)?", stem)
        if not year_match:
            return ""

        year = year_match.group(1)
        month = year_match.group(2) or "00"
        day = year_match.group(3) or "00"
        return f"{year}-{month}-{day}"

    def _get_first_exif_value(self, exif: Dict, keys: List[str]) -> str:
        for key in keys:
            value = exif.get(key)
            if value:
                return self._normalize_exif_value(value)
        return ""

    def _normalize_exif_value(self, value) -> str:
        if isinstance(value, list):
            return "; ".join(str(item) for item in value if item)
        return str(value)

    def _split_datetime_offset(self, value: str) -> tuple[str, str]:
        if not value:
            return "", ""
        text = str(value).strip()
        match = re.match(r"^(.*?)([+-]\d{2}:?\d{2})$", text)
        if not match:
            return text, ""
        date_part = match.group(1).strip()
        offset_part = match.group(2)
        return date_part, offset_part

    def _format_tags(self, value: str) -> str:
        if not value:
            return ""
        return value

    def _format_timezone(self, date_value: str, offset: str) -> str:
        if not offset:
            return ""
        offset_minutes = self._parse_offset_minutes(offset)
        if offset_minutes is None:
            return ""
        return IANA_OFFSET_MAP.get(offset_minutes, "UTC")

    def _parse_offset_minutes(self, offset) -> Optional[int]:
        if offset is None:
            return None
        if isinstance(offset, (int, float)):
            return int(offset) * 60

        text = str(offset).strip()
        if not text:
            return None

        # Handle formats like +HH:MM, -HH:MM, +HHMM, -HHMM, +HH, -HH
        match = re.match(r"^([+-]?)(\d{1,2})(?::?(\d{2}))?$", text)
        if not match:
            return None

        sign = -1 if match.group(1) == "-" else 1
        hours = int(match.group(2))
        minutes = int(match.group(3) or 0)
        return sign * (hours * 60 + minutes)

    def _get_true_extension(self, file_path: Path) -> str:
        if not self.detect_true_ext:
            return file_path.suffix.lower().lstrip(".")
        try:
            from PIL import Image

            with Image.open(file_path) as image:
                fmt = (image.format or "").lower()
        except Exception:
            return file_path.suffix.lower().lstrip(".")

        mapping = {
            "jpeg": "jpg",
            "tiff": "tif",
            "heif": "heic",
        }
        return mapping.get(fmt, fmt or file_path.suffix.lower().lstrip("."))

    def _extract_xmp_tags(self, file_path: Path) -> List[str]:
        try:
            content = file_path.read_text(errors="ignore")
        except Exception:
            return []

        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return []

        tags: List[str] = []
        parent_map = {child: parent for parent in root.iter() for child in parent}

        def local_name(tag: str) -> str:
            return tag.split("}")[-1].lower() if tag else ""

        for elem in root.iter():
            name = local_name(elem.tag)

            if name in {"subject", "keywords", "tagslist"}:
                if elem.text and elem.text.strip():
                    tags.append(elem.text.strip())

            if name == "li":
                ancestor = parent_map.get(elem)
                allow = False
                while ancestor is not None:
                    ancestor_name = local_name(ancestor.tag)
                    if ancestor_name in {"subject", "keywords", "tagslist"}:
                        allow = True
                        break
                    ancestor = parent_map.get(ancestor)
                if allow and elem.text and elem.text.strip():
                    tags.append(elem.text.strip())

        deduped: List[str] = []
        seen = set()
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                deduped.append(tag)
        return deduped

    def _csv_headers(self) -> List[str]:
        return [
            "Filenanme",
            "Folder Date",
            "Filename Date",
            "Sidecar File",
            "Sidecar Date",
            "Sidecar Offset",
            "Sidecar Timezone",
            "Sidecar Description",
            "Sidecar Tags",
            "EXIF Date",
            "EXIF Offset",
            "EXIF Timezone",
            "EXIF Description",
            "EXIF Tags",
            "EXIF Ext",
        ]

    def _row_to_dict(self, row: ImageRow) -> Dict[str, str]:
        return {
            "Filenanme": row.filename,
            "Folder Date": row.folder_date,
            "Filename Date": row.filename_date,
            "Sidecar File": row.sidecar_file,
            "Sidecar Date": row.sidecar_date,
            "Sidecar Offset": row.sidecar_offset,
            "Sidecar Timezone": row.sidecar_timezone,
            "Sidecar Description": row.sidecar_description,
            "Sidecar Tags": row.sidecar_tags,
            "EXIF Date": row.exif_date,
            "EXIF Offset": row.exif_offset,
            "EXIF Timezone": row.exif_timezone,
            "EXIF Description": row.exif_description,
            "EXIF Tags": row.exif_tags,
            "EXIF Ext": row.exif_ext,
        }
