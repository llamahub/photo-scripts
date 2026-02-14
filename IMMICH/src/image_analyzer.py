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

# Mapping from ExifTool File Type to normalized extension
FILE_TYPE_TO_EXT = {
    "JPEG": "jpg",
    "JPG": "jpg",
    "HEIC": "heic",
    "HEIF": "heic",
    "PNG": "png",
    "GIF": "gif",
    "TIFF": "tif",
    "TIF": "tif",
    "BMP": "bmp",
    "WEBP": "webp",
    "DNG": "dng",
    "CR2": "cr2",
    "NEF": "nef",
    "ARW": "arw",
}


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

CAMERA_COUNTER_PATTERN = re.compile(r"^_?(?:DSC|IMG|PXL|VID|MOV|PICT|PHOTO)\d+$", re.IGNORECASE)

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
    metadata_date: str
    calc_date_used: str
    calc_time_used: str
    meta_name_delta: str
    calc_description: str
    calc_tags: str
    calc_date: str
    calc_offset: str
    calc_timezone: str
    calc_filename: str
    calc_path: str
    calc_status: str


class ImageAnalyzer:
    """Analyze image library files and emit CSV rows."""

    def __init__(
        self,
        source_root: str,
        logger,
        max_workers: Optional[int] = None,
    ):
        self.source_root = Path(source_root)
        self.logger = logger
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
        exif_ext = self._get_file_type_extension(file_path, image_exif)

        # Calculate derived fields
        filename_time = self._extract_filename_time(file_path.name)
        name_date, name_date_source = self._calculate_name_date_with_source(
            folder_date, filename_date
        )
        metadata_date, metadata_source = self._calculate_metadata_date(exif_date, sidecar_date)
        calc_date, calc_date_used = self._calculate_calc_date_with_source(
            metadata_date, metadata_source, name_date, name_date_source
        )
        calc_time_value, calc_time_used = self._calculate_calc_time_used(
            calc_date_used, exif_date, sidecar_date, filename_time
        )
        calc_offset = self._calculate_calc_offset(
            calc_time_used,
            calc_date_used,
            exif_offset,
            sidecar_offset,
        )
        if not calc_offset:
            calc_offset, calc_timezone = self._get_system_timezone()
            if calc_offset and not calc_timezone:
                calc_timezone = self._format_timezone(calc_date, calc_offset)
        else:
            calc_timezone = self._format_timezone(calc_date, calc_offset)
        meta_name_delta = self._calculate_meta_name_delta(metadata_date, name_date)
        calc_description = self._calculate_calc_description(
            sidecar_description, exif_description
        )
        calc_tags = self._calculate_calc_tags(sidecar_tags, exif_tags)
        calc_filename = self._calculate_calc_filename(
            calc_date,
            calc_time_value,
            image_exif,
            file_path.parent.name,
            file_path.stem,
            exif_ext,
        )
        calc_path = self._calculate_calc_path(calc_date, file_path.parent.name, calc_filename)
        calc_status = self._calculate_calc_status(
            str(file_path), calc_path, calc_filename
        )

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
            metadata_date=metadata_date,
            calc_date_used=calc_date_used,
            calc_time_used=calc_time_used,
            meta_name_delta=meta_name_delta,
            calc_description=calc_description,
            calc_tags=calc_tags,
            calc_date=calc_date,
            calc_offset=calc_offset,
            calc_timezone=calc_timezone,
            calc_filename=calc_filename,
            calc_path=calc_path,
            calc_status=calc_status,
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
        if CAMERA_COUNTER_PATTERN.match(stem):
            return ""
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

    def _get_file_type_extension(self, file_path: Path, exif_data: Dict) -> str:
        """Extract file type extension from ExifTool File Type field."""
        # Try to get File Type from ExifTool output
        file_type = exif_data.get("File Type") or exif_data.get("FileType") or ""
        if file_type:
            # Map ExifTool File Type to extension
            ext = FILE_TYPE_TO_EXT.get(file_type.upper())
            if ext:
                return ext
        
        # Fallback to file extension if File Type not available
        return file_path.suffix.lower().lstrip(".")

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

    def _is_date_only(self, folder_name: str) -> bool:
        """Check if folder name contains only date-like patterns and no descriptive text."""
        if not folder_name:
            return True
        # Treat pure date folders with optional numeric suffixes as date-only.
        if re.match(r"^\d{4}([_-]\d{2}([_-]\d{2})?)?(_\d+)?$", folder_name):
            return True
        # Remove all date-like patterns (YYYY, YYYY-MM, YYYY-MM-DD, with underscores/hyphens)
        cleaned = re.sub(r"[_\-]?(\d{4}(?:[_\-]\d{2})?(?:[_\-]\d{2})?)", "", folder_name)
        cleaned = cleaned.strip("_-").strip()
        # If nothing remains, it was purely date-based
        return not cleaned

    def _extract_descriptive_parent_folder(self, parent_name: str) -> str:
        """Extract non-date text from parent folder name, or return empty if purely date-based."""
        if self._is_date_only(parent_name):
            return ""
        # Strip version suffixes like _01, _02, etc. that appear after the descriptive text
        parent_name = re.sub(r"_\d+$", "", parent_name)
        return parent_name

    def _strip_duplicate_info_from_basename(
        self, basename: str, parent_folder: str, dimensions: str
    ) -> str:
        """Remove duplicate info from basename (date prefix, dimensions, parent folder)."""
        if not basename:
            return ""

        # Remove leading normalized prefix: YYYY-MM-DD_HHMM_WIDTHxHEIGHT_
        # This handles already-normalized filenames from previous runs
        basename = re.sub(r"^\d{4}-\d{2}-\d{2}_\d{4}_\d+x\d+_", "", basename)

        # Now remove the descriptive (non-date) part of parent folder if present
        parent_desc = self._extract_descriptive_parent_folder(parent_folder)
        if parent_desc:
            # Try exact match first (parent folder with spaces/hyphens as-is)
            if basename.startswith(parent_desc):
                basename = basename[len(parent_desc):].lstrip("_").strip()
            else:
                # Try with underscores replacing spaces/hyphens
                parent_pattern = re.sub(r"[\s_-]+", "_", parent_desc)
                if basename.startswith(parent_pattern):
                    basename = basename[len(parent_pattern):].lstrip("_").strip()

        return basename if basename else "UNKNOWN"

    def _get_image_dimensions(self, image_exif: Dict) -> str:
        """Extract and format image dimensions from EXIF, or try reading from file directly."""
        width = image_exif.get("ImageWidth")
        height = image_exif.get("ImageHeight")

        if width and height:
            return f"{width}x{height}"
        return "0x0"

    def _get_year_month(self, date_str: str) -> Optional[str]:
        """Extract YYYY-MM from date string, return None if invalid/missing."""
        if not date_str:
            return None
        # Check for invalid markers
        if date_str.startswith("1900") or date_str.startswith("0000"):
            return None
        # Extract YYYY-MM with either '-' or ':' separator
        match = re.match(r"^(\d{4})[-:](\d{2})", date_str)
        if match:
            year = int(match.group(1))
            if year < 1900:
                return None
            return f"{match.group(1)}-{match.group(2)}"
        return None

    def _normalize_date_separators(self, value: str) -> str:
        if not value or len(value) < 10:
            return value
        return value[:10].replace(":", "-") + value[10:]

    def _calculate_metadata_date(self, exif_date: str, sidecar_date: str) -> tuple[str, str]:
        """
        Calculate Metadata Date:
        IF EXIF Date is valid THEN return EXIF Date
        ELSE return Sidecar Date
        """
        exif_ym = self._get_year_month(exif_date)
        if exif_ym:
            return self._normalize_date_separators(exif_date or ""), "EXIF"

        sidecar_ym = self._get_year_month(sidecar_date)
        if sidecar_ym:
            return self._normalize_date_separators(sidecar_date or ""), "Sidecar"

        return "", ""

    def _calculate_name_date_with_source(
        self, folder_date: str, filename_date: str
    ) -> tuple[str, str]:
        name_date = self._calculate_name_date(folder_date, filename_date)
        if not name_date:
            return "", ""

        filename_ym = self._get_year_month(filename_date)
        folder_ym = self._get_year_month(folder_date)

        if not folder_ym and filename_ym:
            return name_date, "Filename"
        if not filename_ym and folder_ym:
            return name_date, "Folder"
        if filename_ym and folder_ym:
            if name_date == filename_date:
                return name_date, "Filename"
            return name_date, "Folder"

        return name_date, ""

    def _calculate_calc_date_with_source(
        self,
        metadata_date: str,
        metadata_source: str,
        name_date: str,
        name_source: str,
    ) -> tuple[str, str]:
        calc_date = self._calculate_calc_date(metadata_date, name_date)
        if calc_date and calc_date == metadata_date:
            return calc_date, metadata_source
        if calc_date and calc_date == name_date:
            return calc_date, name_source
        return calc_date, ""

    def _extract_time_from_datetime(self, value: str) -> str:
        if not value or len(value) < 16:
            return ""
        hour = value[11:13] if value[11:13].isdigit() else ""
        minute = value[14:16] if value[14:16].isdigit() else ""
        if not hour or not minute:
            return ""
        return f"{hour}{minute}"

    def _extract_filename_time(self, filename: str) -> str:
        stem = Path(filename).stem
        patterns = [
            r"\d{4}-\d{2}-\d{2}[_-](\d{4})",
            r"\d{8}[_-](\d{4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, stem)
            if match:
                time_value = match.group(1)
                if time_value == "0000":
                    return ""
                return time_value

        return ""

    def _calculate_calc_time_used(
        self,
        calc_date_used: str,
        exif_date: str,
        sidecar_date: str,
        filename_time: str,
    ) -> tuple[str, str]:
        if calc_date_used == "EXIF":
            time_value = self._extract_time_from_datetime(exif_date)
            if time_value and time_value != "0000":
                return time_value, "EXIF"
            if filename_time:
                return filename_time, "Filename"
            return "", ""
        if calc_date_used == "Sidecar":
            time_value = self._extract_time_from_datetime(sidecar_date)
            return time_value, "Sidecar" if time_value else ""
        if calc_date_used == "Filename" and filename_time:
            return filename_time, "Filename"
        return "", ""

    def _calculate_calc_offset(
        self,
        calc_time_used: str,
        calc_date_used: str,
        exif_offset: str,
        sidecar_offset: str,
    ) -> str:
        if calc_time_used == "EXIF":
            return exif_offset or ""
        if calc_time_used == "Sidecar":
            return sidecar_offset or ""
        if calc_time_used == "Filename" and calc_date_used == "EXIF":
            return exif_offset or ""
        return ""

    def _get_system_timezone(self) -> tuple[str, str]:
        local_time = datetime.now().astimezone()
        offset = local_time.utcoffset()
        if offset is None:
            return "", ""

        total_minutes = int(offset.total_seconds() // 60)
        sign = "+" if total_minutes >= 0 else "-"
        abs_minutes = abs(total_minutes)
        hours = abs_minutes // 60
        minutes = abs_minutes % 60
        offset_str = f"{sign}{hours:02d}:{minutes:02d}"
        tz_name = self._format_timezone("", offset_str)
        if not tz_name:
            tz_name = local_time.tzname() or ""
        return offset_str, tz_name

    def _parse_datetime_for_delta(self, value: str) -> Optional[datetime]:
        if not value or len(value) < 10:
            return None
        date_part = value[:10].replace(":", "-")
        if date_part[5:7] == "00" or date_part[8:10] == "00":
            return None

        time_part = "00:00:00"
        if len(value) >= 19:
            time_part = value[11:19]
        elif len(value) >= 16:
            time_part = f"{value[11:16]}:00"

        try:
            return datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    def _add_months(self, dt: datetime, months: int) -> datetime:
        year = dt.year + (dt.month - 1 + months) // 12
        month = (dt.month - 1 + months) % 12 + 1
        day = min(dt.day, self._days_in_month(year, month))
        return dt.replace(year=year, month=month, day=day)

    def _days_in_month(self, year: int, month: int) -> int:
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        return (next_month - datetime(year, month, 1)).days

    def _calculate_meta_name_delta(self, metadata_date: str, name_date: str) -> str:
        start = self._parse_datetime_for_delta(metadata_date)
        end = self._parse_datetime_for_delta(name_date)
        if not start or not end:
            return ""

        if start > end:
            start, end = end, start

        years = end.year - start.year
        temp = self._add_months(start, years * 12)
        if temp > end:
            years -= 1
            temp = self._add_months(start, years * 12)

        months = end.month - temp.month
        if months < 0:
            months += 12
            years -= 1
            temp = self._add_months(start, years * 12)

        temp = self._add_months(temp, months)
        if temp > end:
            months -= 1
            temp = self._add_months(self._add_months(start, years * 12), months)

        delta = end - temp
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60

        return f"{years}:{months}:{days} {hours}:{minutes}"

    def _calculate_calc_description(self, sidecar_desc: str, exif_desc: str) -> str:
        sidecar_desc = (sidecar_desc or "").strip()
        exif_desc = (exif_desc or "").strip()
        if sidecar_desc and exif_desc:
            if sidecar_desc == exif_desc:
                return exif_desc
            return f"{exif_desc}, {sidecar_desc}"
        return exif_desc or sidecar_desc

    def _calculate_calc_tags(self, sidecar_tags: str, exif_tags: str) -> str:
        def split_tags(value: str) -> List[str]:
            return [tag.strip() for tag in (value or "").split(";") if tag.strip()]

        merged: List[str] = []
        seen = set()
        for tag in split_tags(exif_tags) + split_tags(sidecar_tags):
            if tag not in seen:
                seen.add(tag)
                merged.append(tag)

        return "; ".join(merged)

    def _calculate_name_date(self, folder_date: str, filename_date: str) -> str:
        """
        Calculate Name Date according to spec:
        IF month(Filename Date) == month(Folder Date) THEN return Filename Date
        ELSE IF year(Folder Date) < year(Filename Date) THEN return Folder Date
        ELSE return Filename Date
        """
        # Get year-month from both dates
        folder_ym = self._get_year_month(folder_date)
        filename_ym = self._get_year_month(filename_date)

        # If either is invalid, use the other (or empty if both invalid)
        if not folder_ym:
            return filename_date or ""
        if not filename_ym:
            return folder_date or ""

        # Extract components: YYYY-MM format
        folder_year = folder_ym[:4]
        folder_month = folder_ym[5:7]
        filename_year = filename_ym[:4]
        filename_month = filename_ym[5:7]

        # Same month and year: use filename_date
        if folder_month == filename_month and folder_year == filename_year:
            return filename_date or ""

        # Folder year < filename year: use folder_date
        if folder_year < filename_year:
            return folder_date or ""

        # Default: use filename_date
        return filename_date or ""

    def _calculate_calc_date(self, exif_date: str, name_date: str) -> str:
        """
        Calculate Calc Date according to spec:
        IF EXIF Date is valid AND date(EXIF Date) <= date(Name Date) THEN return EXIF Date
        ELSE return Name Date
        """
        # Validate dates (compare date-only part, ignoring time)
        exif_ym = self._get_year_month(exif_date)
        name_ym = self._get_year_month(name_date)

        # If exif_date is invalid, use name_date
        if not exif_ym:
            return name_date or ""

        # If name_date is invalid, use exif_date
        if not name_ym:
            return self._normalize_date_separators(exif_date or "")

        # If the name date is a month-only placeholder (day=00), prefer EXIF
        # when EXIF is in the same month to avoid using the placeholder day.
        if len(name_date) >= 10 and name_date[8:10] == "00" and exif_ym == name_ym:
            return self._normalize_date_separators(exif_date or "")

        # Compare date-only parts (first 10 chars: YYYY-MM-DD or YYYY:MM:DD)
        exif_date_only = exif_date[:10] if len(exif_date) >= 10 else exif_date
        name_date_only = name_date[:10] if len(name_date) >= 10 else name_date
        exif_date_only = exif_date_only.replace(":", "-")
        name_date_only = name_date_only.replace(":", "-")

        # If EXIF date <= Name date, use EXIF date (lexicographic comparison works for YYYY-MM-DD)
        if exif_date_only <= name_date_only:
            return self._normalize_date_separators(exif_date or "")

        # Otherwise use Name date
        return name_date or ""

    def _calculate_calc_filename(
        self,
        calc_date: str,
        time_part: str,
        image_exif: Dict,
        parent_folder: str,
        original_filename: str,
        ext: str,
    ) -> str:
        """
        Calculate normalized filename: YYYY-MM-DD_HHMM_WIDTHxHEIGHT_PARENT_BASENAME.EXT
        """
        if not calc_date:
            return original_filename

        # Extract date part from calc_date (YYYY-MM-DD)
        date_part = calc_date[:10] if len(calc_date) >= 10 else calc_date
        
        # Extract time part (HHMM) from the chosen source
        time_part = time_part or "0000"

        # Get dimensions
        dimensions = self._get_image_dimensions(image_exif)

        # Get descriptive parent folder (or empty if date-only)
        parent_desc = self._extract_descriptive_parent_folder(parent_folder)

        # Get basename and strip duplicates
        basename = self._strip_duplicate_info_from_basename(original_filename, parent_folder, dimensions)

        # Build filename: YYYY-MM-DD_HHMM_WIDTHxHEIGHT_PARENT_BASENAME.EXT
        if parent_desc:
            filename = f"{date_part}_{time_part}_{dimensions}_{parent_desc}_{basename}.{ext}"
        else:
            filename = f"{date_part}_{time_part}_{dimensions}_{basename}.{ext}"

        return filename

    def _calculate_calc_status(
        self, original_path: str, calc_path: str, calc_filename: str
    ) -> str:
        """
        Compare original file path with calculated path and return status code.
        Status codes:
        - MATCH: Paths are identical
        - RENAME: Same path but filename differs
        - MOVE: Different path
        """
        # Reconstruct what the full path would be
        reconstructed_path = str(Path(calc_path) / calc_filename)
        
        if original_path == reconstructed_path:
            return "MATCH"

        orig_parent = str(Path(original_path).parent)
        calc_parent = str(Path(calc_path))
        if orig_parent == calc_parent:
            return "RENAME"

        return "MOVE"
        
        # Extract components for comparison
        orig_filename = Path(original_path).name
        calc_filename_only = Path(reconstructed_path).name
        
        # Check if dates differ (but first 10 chars should match date)
        if original_filename_date and original_filename_date != calc_date:
            return "DATE_MISMATCH"
        
        # Check if parent folder differs
        orig_parent = Path(original_path).parent.name
        calc_parent_desc = self._extract_descriptive_parent_folder(original_parent_folder)
        if calc_parent_desc and orig_parent != original_parent_folder:
            # Check if the descriptive parts at least match (ignoring version suffixes)
            orig_parent_desc = self._extract_descriptive_parent_folder(orig_parent)
            if orig_parent_desc != calc_parent_desc:
                return "FOLDER_DIFF"
        
        # Check if time differs (UTC offset issue)
        orig_time = orig_filename.split('_')[1] if len(orig_filename.split('_')) > 1 else ''
        calc_time = calc_filename_only.split('_')[1] if len(calc_filename_only.split('_')) > 1 else ''
        if orig_time and calc_time and orig_time != calc_time:
            return "TIME_DIFF"
        
        # Check if format changed (normalized vs non-normalized)
        if not orig_filename[:10].count('-') == 2:  # Original not in YYYY-MM-DD format
            if calc_filename_only[:10].count('-') == 2:  # Calc is in YYYY-MM-DD format
                return "FORMAT_CHANGED"
        
        return "OTHER"

    def _calculate_calc_path(self, calc_date: str, parent_folder: str, calc_filename: str) -> str:
        """
        Calculate organized path: source_root/<decade>/<year>/<year>-<month>/<parent> (folder only, no filename)
        """
        if not calc_date or len(calc_date) < 10:
            return str(self.source_root)

        # Extract year and month from calc_date (YYYY-MM-DD)
        year = calc_date[:4]
        month = calc_date[5:7]

        # Calculate decade (e.g., 2020, 2010, 1990)
        try:
            year_int = int(year)
            decade = (year_int // 10) * 10
        except ValueError:
            decade = 0

        # Get descriptive parent folder (or empty if date-only)
        parent_desc = self._extract_descriptive_parent_folder(parent_folder)

        # Build path: source_root/<decade>/<year>/<year>-<month>/<parent> (folder only)
        if parent_desc:
            path = str(self.source_root / f"{decade}+/{year}/{year}-{month}/{parent_desc}")
        else:
            path = str(self.source_root / f"{decade}+/{year}/{year}-{month}")

        return path

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
            "Metadata Date",
            "Calc Date Used",
            "Calc Time Used",
            "Meta - Name",
            "Calc Description",
            "Calc Tags",
            "Calc Date",
            "Calc Offset",
            "Calc Timezone",
            "Calc Filename",
            "Calc Path",
            "Calc Status",
            "Select",
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
            "Metadata Date": row.metadata_date,
            "Calc Date Used": row.calc_date_used,
            "Calc Time Used": row.calc_time_used,
            "Meta - Name": row.meta_name_delta,
            "Calc Description": row.calc_description,
            "Calc Tags": row.calc_tags,
            "Calc Date": row.calc_date,
            "Calc Offset": row.calc_offset,
            "Calc Timezone": row.calc_timezone,
            "Calc Filename": row.calc_filename,
            "Calc Path": row.calc_path,
            "Calc Status": row.calc_status,
            "Select": "",
        }
