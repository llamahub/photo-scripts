#!/usr/bin/env python3
"""Image updater for IMMICH update script."""

from __future__ import annotations

import csv
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from zoneinfo import ZoneInfo


SELECTED_VALUES = {"y", "yes", "true"}
HEIC_EXTENSIONS = {".heic", ".heif"}


class ImageUpdater:
    """Apply updates from analyze CSV output to image files."""

    def __init__(self, csv_path: str, logger, dry_run: bool = False) -> None:
        self.csv_path = Path(csv_path)
        self.logger = logger
        self.dry_run = dry_run
        self.stats = {
            "rows_total": 0,
            "rows_selected": 0,
            "exif_updated": 0,
            "exif_skipped": 0,
            "renamed": 0,
            "moved": 0,
            "errors": 0,
        }
        self.exiftool_available = shutil.which("exiftool") is not None
        if not self.exiftool_available and not self.dry_run:
            self.logger.warning("exiftool not found on PATH; EXIF updates will be skipped")

    def process(self) -> Dict[str, int]:
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")

        with self.csv_path.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            select_col = self._select_column(reader.fieldnames or [])

            for row in reader:
                self.stats["rows_total"] += 1
                if not self._is_selected(row.get(select_col, "")):
                    continue

                self.stats["rows_selected"] += 1
                self._process_row(row)

                if self.stats["rows_selected"] % 50 == 0:
                    self.logger.info(
                        f"Progress: {self.stats['rows_selected']} files processed"
                    )

        return self.stats

    def _select_column(self, fieldnames: List[str]) -> str:
        if "Selected" in fieldnames:
            return "Selected"
        if "Select" in fieldnames:
            return "Select"
        raise ValueError("CSV missing selection column: Selected/Select")

    def _is_selected(self, value: str) -> bool:
        return str(value).strip().lower() in SELECTED_VALUES

    def _process_row(self, row: Dict[str, str]) -> None:
        file_path = (
            row.get("Filenanme")
            or row.get("Filename")
            or row.get("File")
            or ""
        )
        if not file_path:
            self.logger.error("Row missing filename column")
            self.stats["errors"] += 1
            return

        if not Path(file_path).exists():
            self.logger.error(f"File not found: {file_path}")
            self.stats["errors"] += 1
            return

        calc_description = row.get("Calc Description", "")
        calc_tags = self._split_tags(row.get("Calc Tags", ""))
        exif_datetime = self._format_exif_datetime(
            row.get("Calc Date", ""), row.get("Calc Filename", "")
        )
        calc_offset = self._resolve_calc_offset(row, exif_datetime)

        exif_status = self._update_exif(
            file_path,
            calc_description,
            calc_tags,
            exif_datetime,
            calc_offset,
        )
        if exif_status == "updated":
            self.stats["exif_updated"] += 1
        elif exif_status == "skipped":
            self.stats["exif_skipped"] += 1
        else:
            self.stats["errors"] += 1

        file_status = self._apply_file_action(
            file_path,
            row.get("Calc Status", ""),
            row.get("Calc Path", ""),
            row.get("Calc Filename", ""),
        )
        if file_status == "renamed":
            self.stats["renamed"] += 1
        elif file_status == "moved":
            self.stats["moved"] += 1
        elif file_status == "error":
            self.stats["errors"] += 1

        self.logger.audit(
            f"AUDIT file={file_path} exif={exif_status} file_action={file_status}"
        )

    def _split_tags(self, value: str) -> List[str]:
        return [tag.strip() for tag in (value or "").split(";") if tag.strip()]

    def _resolve_calc_offset(self, row: Dict[str, str], exif_datetime: str) -> str:
        calc_offset = (row.get("Calc Offset") or "").strip()
        if calc_offset:
            return calc_offset

        calc_timezone = (row.get("Calc Timezone") or "").strip()
        if calc_timezone:
            offset_from_tz = self._offset_from_timezone(calc_timezone, exif_datetime)
            if offset_from_tz:
                return offset_from_tz

        time_used = (row.get("Calc Time Used") or "").strip().lower()
        if time_used == "exif":
            return (row.get("EXIF Offset") or "").strip()
        if time_used == "sidecar":
            return (row.get("Sidecar Offset") or "").strip()
        return ""

    def _offset_from_timezone(self, timezone_name: str, exif_datetime: str) -> str:
        dt = self._parse_exif_datetime(exif_datetime)
        if dt is None:
            return ""

        try:
            tzinfo = ZoneInfo(timezone_name)
        except Exception as exc:
            self.logger.warning(
                f"Invalid Calc Timezone '{timezone_name}': {exc}"
            )
            return ""

        offset = dt.replace(tzinfo=tzinfo).utcoffset()
        if offset is None:
            return ""

        total_minutes = int(offset.total_seconds() // 60)
        sign = "+" if total_minutes >= 0 else "-"
        abs_minutes = abs(total_minutes)
        hours = abs_minutes // 60
        minutes = abs_minutes % 60
        return f"{sign}{hours:02d}:{minutes:02d}"

    def _parse_exif_datetime(self, exif_datetime: str) -> datetime | None:
        text = (exif_datetime or "").strip()
        if not text:
            return None

        for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue

        return None

    def _format_exif_datetime(self, calc_date: str, calc_filename: str) -> str:
        calc_date = (calc_date or "").strip()
        if not calc_date:
            return ""

        # Normalize Excel-style dates (M/D/YY H:MM or M/D/YY)
        for fmt in ("%m/%d/%y %H:%M", "%m/%d/%y"):
            try:
                dt = datetime.strptime(calc_date, fmt)
                return dt.strftime("%Y:%m:%d %H:%M:%S")
            except ValueError:
                continue

        if len(calc_date) < 10:
            return ""

        date_part_raw = calc_date[:10].replace(":", "-")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_part_raw):
            return ""

        year, month, day = date_part_raw.split("-")
        month = "01" if month == "00" else month
        day = "01" if day == "00" else day
        date_part = f"{year}:{month}:{day}"

        time_part = ""
        if len(calc_date) >= 16 and ":" in calc_date[11:16]:
            time_part = calc_date[11:19] if len(calc_date) >= 19 else f"{calc_date[11:16]}:00"

        if not time_part:
            match = re.match(r"^\d{4}-\d{2}-\d{2}_(\d{4})_", calc_filename or "")
            if match:
                hhmm = match.group(1)
                if hhmm != "0000":
                    time_part = f"{hhmm[:2]}:{hhmm[2:]}:00"

        if not time_part:
            time_part = "00:00:00"

        return f"{date_part} {time_part}"

    def _update_exif(
        self,
        file_path: str,
        description: str,
        tags: List[str],
        date_exif: str,
        date_exif_offset: str,
    ) -> str:
        if not description and not tags and not date_exif:
            return "skipped"

        if not self.exiftool_available and not self.dry_run:
            self.logger.error("exiftool not available; cannot update EXIF")
            return "error"

        if self.dry_run:
            self.logger.debug(f"Would update EXIF for {file_path} (dry run)")
            return "updated"

        ext = Path(file_path).suffix.lower()
        is_heic = ext in HEIC_EXTENSIONS

        cmd = ["exiftool", "-overwrite_original", "-F"]
        cmd.append(f"-Description={description}")

        if tags is not None:
            if tags:
                for tag in tags:
                    if is_heic:
                        cmd.append(f"-Subject={tag}")
                    else:
                        cmd.append(f"-Keywords={tag}")
            else:
                if is_heic:
                    cmd.append("-Subject=")
                else:
                    cmd.append("-Keywords=")

        if date_exif:
            cmd.append(f"-DateTimeOriginal={date_exif}")
            if date_exif_offset:
                cmd.append(f"-OffsetTimeOriginal={date_exif_offset}")

        cmd.append(file_path)

        try:
            subprocess.run(cmd, capture_output=True, check=True, text=True)
            self.logger.debug(f"Updated EXIF for {file_path}")
            return "updated"
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.strip() if exc.stderr else str(exc)
            self.logger.error(f"ExifTool error for {file_path}: {detail}")
            return "error"
        except Exception as exc:
            self.logger.error(f"Error updating EXIF for {file_path}: {exc}")
            return "error"

    def _apply_file_action(
        self,
        file_path: str,
        calc_status: str,
        calc_path: str,
        calc_filename: str,
    ) -> str:
        status = (calc_status or "").strip().upper()
        if status not in {"RENAME", "MOVE"}:
            return "none"

        if not calc_path or not calc_filename:
            self.logger.error(f"Missing calc path/filename for {file_path}")
            return "error"

        target_path = Path(calc_path) / calc_filename
        if self.dry_run:
            return "moved" if status == "MOVE" else "renamed"

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(file_path, str(target_path))
            return "moved" if status == "MOVE" else "renamed"
        except Exception as exc:
            self.logger.error(f"Failed to move {file_path} -> {target_path}: {exc}")
            return "error"
