#!/usr/bin/env python3
"""Image updater for IMMICH update script."""

from __future__ import annotations

import csv
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from zoneinfo import ZoneInfo


SELECTED_VALUES = {"y", "yes", "true"}
HEIC_EXTENSIONS = {".heic", ".heif"}
SIDECAR_EXTENSIONS = {".xmp", ".XMP", ".json", ".JSON", ".disabled",".possible", ".unknown"}


class ImageUpdater:
    def _format_exif_datetime(self, calc_date: str, calc_filename: str) -> str:
        """
        Normalize various date formats to EXIF datetime (YYYY:MM:DD HH:MM:SS).
        Handles Excel-style dates, ISO, and placeholder months/days.
        If time is missing, tries to extract from filename or defaults to 00:00:00.
        """
        if not calc_date or not isinstance(calc_date, str):
            return ""

        # Try Excel-style dates (M/D/YY H:MM or M/D/YY)
        for fmt in ("%m/%d/%y %H:%M", "%m/%d/%y"):
            try:
                dt = datetime.strptime(calc_date, fmt)
                return dt.strftime("%Y:%m:%d %H:%M:%S")
            except ValueError:
                continue

        # Try ISO date/time patterns
        # Accepts: YYYY-MM-DD, YYYY-MM-DD HH:MM, YYYY-MM-DD HH:MM:SS
        date_part_raw = calc_date[:10].replace(":", "-")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_part_raw):
            return ""

        year, month, day = date_part_raw.split("-")
        # Replace placeholder months/days (00) with 01
        month = "01" if month == "00" else month
        day = "01" if day == "00" else day
        date_part = f"{year}:{month}:{day}"

        # Try to extract time part from calc_date
        time_part = ""
        if len(calc_date) >= 16 and ":" in calc_date[11:16]:
            # Handles YYYY-MM-DD HH:MM or YYYY-MM-DD HH:MM:SS
            time_part = calc_date[11:19] if len(calc_date) >= 19 else f"{calc_date[11:16]}:00"

        # If no time in date, try to extract from filename (e.g., 2023-11-26_0911_...)
        if not time_part:
            match = re.match(r"^\d{4}-\d{2}-\d{2}_(\d{4})_", calc_filename or "")
            if match:
                hhmm = match.group(1)
                if hhmm != "0000":
                    time_part = f"{hhmm[:2]}:{hhmm[2:]}:00"

        if not time_part:
            time_part = "00:00:00"

        return f"{date_part} {time_part}"

    def __init__(self, csv_path: str, logger, dry_run: bool = False, all_rows: bool = False, max_workers: Optional[int] = None) -> None:
        self.csv_path = Path(csv_path)
        self.logger = logger
        self.dry_run = dry_run
        self.all_rows = all_rows
        # Calculate max_workers: use provided value or default to 4-8 range, capped at CPU count
        if max_workers is None:
            cpu_count = os.cpu_count() or 1
            max_workers = min(8, max(4, cpu_count // 2))
        self.max_workers = max_workers
        self.stats = {
            "rows_total": 0,
            "rows_selected": 0,
            "exif_updated": 0,
            "exif_skipped": 0,
            "renamed": 0,
            "moved": 0,
            "sidecar_renamed": 0,
            "sidecar_moved": 0,
            "sidecar_errors": 0,
            "errors": 0,
        }
        self.exiftool_available = shutil.which("exiftool") is not None

    def process(self) -> Dict[str, int]:
        if not self.exiftool_available:
            self.logger.error("exiftool not available; cannot update EXIF")
            raise RuntimeError("exiftool not available; cannot update EXIF")
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")

        # Phase 0: Load and validate all selected rows
        rows = self._load_selected_rows()
        if not rows:
            self.logger.info("No rows to process")
            return self.stats

        self.logger.info(f"Processing {len(rows)} selected files")
        
        # Phase 1: Update EXIF in parallel (I/O bound operation)
        self.logger.info(f"Phase 1: Updating EXIF metadata ({self.max_workers} workers)...")
        self._process_exif_batch(rows)
        
        # Phase 2: Move files serially (to avoid conflicts)
        self.logger.info("Phase 2: Moving files to final locations...")
        self._process_moves_batch(rows)

        return self.stats

    def _load_selected_rows(self) -> List[Dict[str, str]]:
        """Load and filter rows from CSV based on selection criteria."""
        rows = []
        with self.csv_path.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            select_col = None
            if not self.all_rows:
                select_col = self._select_column(reader.fieldnames or [])

            for row in reader:
                self.stats["rows_total"] += 1
                if not self.all_rows and not self._is_selected(row.get(select_col, "")):
                    continue

                self.stats["rows_selected"] += 1
                
                # Validate row can be processed
                if self._validate_row(row):
                    rows.append(row)
                else:
                    self.stats["errors"] += 1

        return rows

    def _validate_row(self, row: Dict[str, str]) -> bool:
        """Check if row has required fields."""
        file_path = row.get("Filenanme") or row.get("Filename") or row.get("File") or ""
        if not file_path:
            self.logger.error("Row missing filename column")
            return False

        if not Path(file_path).exists():
            self.logger.error(f"File not found: {file_path}")
            return False
        
        return True

    def _process_exif_batch(self, rows: List[Dict[str, str]]) -> None:
        """Update EXIF for all rows in parallel using ThreadPoolExecutor."""
        if not rows:
            return

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._update_exif_for_row, row): i for i, row in enumerate(rows)}
            
            for idx, future in enumerate(as_completed(futures), 1):
                row_idx = futures[future]
                try:
                    exif_status, new_calc_path, exif_datetime = future.result()
                    rows[row_idx]["_exif_status"] = exif_status
                    rows[row_idx]["_new_calc_path"] = new_calc_path
                    rows[row_idx]["_exif_datetime"] = exif_datetime
                    
                    if exif_status == "updated":
                        self.stats["exif_updated"] += 1
                    elif exif_status == "skipped":
                        self.stats["exif_skipped"] += 1
                    else:
                        self.stats["errors"] += 1
                except Exception as exc:
                    self.logger.error(f"EXIF update error for row {row_idx}: {exc}")
                    self.stats["errors"] += 1
                    rows[row_idx]["_exif_status"] = "error"
                    rows[row_idx]["_exif_datetime"] = ""

                if idx % 50 == 0:
                    self.logger.info(f"EXIF Progress: {idx}/{len(rows)} files processed")

    def _update_exif_for_row(self, row: Dict[str, str]) -> tuple:
        """Update EXIF for a single row. Returns (status, new_calc_path, exif_datetime)."""
        file_path = row.get("Filenanme") or row.get("Filename") or row.get("File") or ""
        calc_description = row.get("Calc Description", "")
        calc_tags = self._split_tags(row.get("Calc Tags", ""))
        calc_date = row.get("Calc Date", "")
        calc_filename = row.get("Calc Filename", "")

        exif_datetime = self._format_exif_datetime(calc_date, calc_filename)
        calc_offset = self._resolve_calc_offset(row, exif_datetime)

        # Always error and stop if exiftool is not available, regardless of dry run
        if not self.exiftool_available:
            self.logger.error("exiftool not available; cannot update EXIF")
            raise RuntimeError("exiftool not available; cannot update EXIF")

        exif_status = self._update_exif(
            file_path,
            calc_description,
            calc_tags,
            exif_datetime,
            calc_offset,
        )

        # If EXIF was updated and original path had placeholder date, recalculate path
        new_calc_path = ""
        if exif_status == "updated" and calc_date and self._is_placeholder_date(calc_date):
            calc_path = row.get("Calc Path", "")
            new_calc_path = self._recalculate_path_after_exif_update(
                calc_path, exif_datetime, file_path
            )

        return exif_status, new_calc_path, exif_datetime

    def _process_moves_batch(self, rows: List[Dict[str, str]]) -> None:
        """Move files serially after EXIF updates are complete."""
        for idx, row in enumerate(rows, 1):
            self._process_row_for_move(row)
            
            if idx % 50 == 0:
                self.logger.info(f"Move Progress: {idx}/{len(rows)} files processed")

    def _process_row_for_move(self, row: Dict[str, str]) -> None:
        """Handle file move phase after EXIF updates."""
        file_path = row.get("Filenanme") or row.get("Filename") or row.get("File") or ""
        calc_status = row.get("Calc Status", "")
        
        # Use new calc_path if it was recalculated due to placeholder date, otherwise use original
        calc_path = row.get("_new_calc_path", "") or row.get("Calc Path", "")
        calc_filename = row.get("Calc Filename", "")
        
        # Use the exif_datetime that was computed during EXIF phase
        exif_datetime = row.get("_exif_datetime", "")
        
        calc_filename = self._normalize_calc_filename(
            calc_filename,
            row.get("Calc Date", ""),
            calc_path,
            exif_datetime,
        )
        target_path = self._resolve_target_path(file_path, calc_status, calc_path, calc_filename)

        if target_path:
            self._move_sidecars(file_path, target_path)

        file_status = self._apply_file_action(
            file_path,
            calc_status,
            calc_path,
            calc_filename,
        )
        if file_status == "renamed":
            self.stats["renamed"] += 1
        elif file_status == "moved":
            self.stats["moved"] += 1
        elif file_status == "error":
            self.stats["errors"] += 1

        self.logger.audit(
            f"AUDIT file={file_path} exif={row.get('_exif_status', 'none')} file_action={file_status}"
        )

    def _select_column(self, fieldnames: List[str]) -> str:
        if "Selected" in fieldnames:
            return "Selected"
        if "Select" in fieldnames:
            return "Select"
        raise ValueError("CSV missing selection column: Selected/Select")

    def _is_selected(self, value: str) -> bool:
        return str(value).strip().lower() in SELECTED_VALUES

    def _split_tags(self, value: str) -> List[str]:
        return [tag.strip() for tag in (value or "").split(";") if tag.strip()]

    def _is_placeholder_date(self, date_str: str) -> bool:
        """Check if date has placeholder month (00) or day (00)."""
        if not date_str or len(date_str) < 10:
            return False
        # Format is YYYY-MM-DD or YYYY:MM:DD
        return date_str[5:7] == "00" or date_str[8:10] == "00"

    def _recalculate_path_after_exif_update(
        self, original_calc_path: str, new_exif_datetime: str, file_path: str
    ) -> str:
        """
        Recalculate the organized folder path based on the new EXIF date.
        
        Original calc_path was based on placeholder date (YYYY-00-DD or YYYY-MM-00).
        Now that we've updated EXIF to a real date, we need to update the path
        to use the new year-month.
        
        Path structure: .../DECADE/YEAR/YEAR-MONTH/PARENT_FOLDER
        Example: /2000+/2009/2009-01/2009 June and July
        """
        if not new_exif_datetime or not original_calc_path:
            return original_calc_path

        # Extract year and month from new EXIF date (format: YYYY:MM:DD HH:MM:SS)
        date_part = new_exif_datetime.replace(":", "-")[:10]  # Convert to YYYY-MM-DD
        if len(date_part) < 7:
            return original_calc_path

        year = date_part[:4]
        month = date_part[5:7]
        
        # Calculate decade (e.g., 2020, 2010, 1990)
        try:
            year_int = int(year)
            decade = (year_int // 10) * 10
            decade_str = f"{decade}+"
        except ValueError:
            return original_calc_path

        # Parse the original path to extract components
        # Typical structure: /root/DECADE+/YEAR/YEAR-MONTH/PARENT_FOLDER
        path_parts = Path(original_calc_path).parts
        if len(path_parts) < 2:
            return original_calc_path

        # Find the decade part (contains "+")
        decade_idx = -1
        for i, part in enumerate(path_parts):
            if "+" in part:
                decade_idx = i
                break

        if decade_idx < 0:
            return original_calc_path

        # Rebuild path with new year-month
        # Keep everything up to and including decade, then add year and new year-month
        new_parts = list(path_parts[: decade_idx + 1])  # Up to and including decade+
        new_parts.append(year)  # Add year folder
        new_parts.append(f"{year}-{month}")  # Add new year-month folder

        # Add any remaining folders (parent folder descriptions)
        if len(path_parts) > decade_idx + 3:
            new_parts.extend(path_parts[decade_idx + 3 :])

        new_calc_path = str(Path(*new_parts))
        self.logger.debug(
            f"Recalculated path after EXIF update: {original_calc_path} -> {new_calc_path}"
        )
        return new_calc_path

    def _resolve_target_path(
        self,
        file_path: str,
        calc_status: str,
        calc_path: str,
        calc_filename: str,
    ) -> Path | None:
        status = (calc_status or "").strip().upper()
        if status not in {"RENAME", "MOVE"}:
            return Path(file_path)
        if not calc_path or not calc_filename:
            return None
        return Path(calc_path) / calc_filename

    def _move_sidecars(self, source_path: str, target_path: Path) -> None:
        source = Path(source_path)
        if not source.exists():
            return

        if source.resolve() == target_path.resolve():
            return

        target_base = target_path.with_suffix("")

        for ext in SIDECAR_EXTENSIONS:
            sidecar = source.with_suffix(ext)
            if not sidecar.exists():
                continue

            target_sidecar = target_base.with_suffix(ext)
            if self.dry_run:
                sidecar_action = (
                    "would_rename"
                    if sidecar.parent.resolve() == target_sidecar.parent.resolve()
                    else "would_move"
                )
                self.logger.audit(
                    "AUDIT sidecar=%s sidecar_action=%s target=%s",
                    sidecar,
                    sidecar_action,
                    target_sidecar,
                )
                continue

            if sidecar.resolve() == target_sidecar.resolve():
                continue

            try:
                target_sidecar.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(sidecar), str(target_sidecar))
                sidecar_action = (
                    "renamed"
                    if sidecar.parent.resolve() == target_sidecar.parent.resolve()
                    else "moved"
                )
                if sidecar_action == "renamed":
                    self.stats["sidecar_renamed"] += 1
                else:
                    self.stats["sidecar_moved"] += 1
                self.logger.audit(
                    "AUDIT sidecar=%s sidecar_action=%s target=%s",
                    sidecar,
                    sidecar_action,
                    target_sidecar,
                )
            except Exception as exc:
                self.stats["sidecar_errors"] += 1
                self.logger.error(
                    f"Failed to move sidecar {sidecar} -> {target_sidecar}: {exc}"
                )

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
            self.logger.warning(f"Invalid Calc Timezone '{timezone_name}': {exc}")
            return ""

        offset = dt.replace(tzinfo=tzinfo).utcoffset()
        if offset is None:
            return ""
        # Format as "+HH:MM" or "-HH:MM"
        total_seconds = offset.total_seconds()
        sign = "+" if total_seconds >= 0 else "-"
        total_seconds = abs(int(total_seconds))
        hours, remainder = divmod(total_seconds, 3600)
        minutes = remainder // 60
        return f"{sign}{hours:02.0f}:{minutes:02.0f}"

    def _normalize_calc_filename(
        self,
        calc_filename: str,
        calc_date: str,
        calc_path: str,
        exif_datetime: str,
    ) -> str:
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

        if self.dry_run:
            self.logger.debug(f"Would update EXIF for {file_path} (dry run)")
            return "updated"
        if not self.exiftool_available:
            self.logger.error("exiftool not available; cannot update EXIF")
            return "error"

        ext = Path(file_path).suffix.lower()
        is_heic = ext in HEIC_EXTENSIONS

        cmd = ["exiftool", "-overwrite_original", "-F"]
        cmd.append(f"-Description={description}")

        # Deduplicate tags before writing
        unique_tags = list(dict.fromkeys(tags)) if tags is not None else []

        if unique_tags:
            if len(unique_tags) == 1:
                tag = unique_tags[0]
                cmd.append(f"-Subject={tag}")
                cmd.append(f"-Keywords={tag}")
                cmd.append(f"-XMP:Subject={tag}")
                cmd.append(f"-XMP-dc:Subject={tag}")
                cmd.append(f"-IPTC:Keywords={tag}")
            else:
                for tag in unique_tags:
                    cmd.append(f"-Subject={tag}")
                    cmd.append(f"-Keywords={tag}")
                    cmd.append(f"-XMP:Subject={tag}")
                    cmd.append(f"-IPTC:Keywords={tag}")
                cmd.append("-XMP-dc:Subject=")
        else:
            # No tags: clear all possible fields
            cmd.append("-Subject=")
            cmd.append("-Keywords=")
            cmd.append("-XMP:Subject=")
            cmd.append("-XMP-dc:Subject=")
            cmd.append("-IPTC:Keywords=")

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
