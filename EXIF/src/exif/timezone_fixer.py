"""
Business logic for fixing timezone offsets in EXIF data based on CSV input.
"""

import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from zoneinfo import ZoneInfo


class TimezoneFixer:
    """
    Fixes timezone offsets in image EXIF data based on CSV input.
    """

    def __init__(
        self,
        input_csv: str,
        dry_run: bool = False,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize TimezoneFixer.

        Args:
            input_csv: Path to CSV file with timezone fix instructions
            dry_run: If True, simulate changes without modifying files
            logger: Logger instance for output
        """
        self.input_csv = Path(input_csv)
        self.dry_run = dry_run
        self.logger = logger or logging.getLogger("timezone_fixer")

    def calculate_new_datetime_offset(
        self, 
        target_date: str, 
        target_offset: str, 
        new_timezone: str
    ) -> tuple[str, str]:
        """
        Calculate new datetime and offset when changing timezone.

        Args:
            target_date: Current EXIF date (multiple formats supported)
            target_offset: Current offset (+HH:MM or -HH:MM)
            new_timezone: New timezone label (e.g., 'America/New_York')

        Returns:
            Tuple of (new_date, new_offset) in EXIF format
        """
        try:
            # Parse current date - try multiple formats
            dt = None
            formats_to_try = [
                "%Y:%m:%d %H:%M:%S",      # EXIF format
                "%Y-%m-%d %H:%M:%S",      # ISO format
                "%m/%d/%Y %H:%M",         # Excel US format
                "%d/%m/%Y %H:%M",         # Excel International format
                "%Y-%m-%d %H:%M",         # ISO without seconds
                "%Y:%m:%d %H:%M",         # EXIF without seconds
            ]
            
            for fmt in formats_to_try:
                try:
                    dt = datetime.strptime(target_date, fmt)
                    break
                except ValueError:
                    continue
            
            if dt is None:
                raise ValueError(f"Could not parse date: {target_date}")

            # Parse current offset
            sign = 1 if target_offset[0] == '+' else -1
            hours = int(target_offset[1:3])
            minutes = int(target_offset[4:6])
            from datetime import timedelta, timezone as tz
            current_offset_td = timedelta(hours=sign * hours, minutes=sign * minutes)

            # Create timezone-aware datetime in current timezone
            current_tz = tz(current_offset_td)
            dt_current = dt.replace(tzinfo=current_tz)

            # Convert to new timezone
            new_tz = ZoneInfo(new_timezone)
            dt_new = dt_current.astimezone(new_tz)

            # Format new date and offset
            new_date = dt_new.strftime("%Y:%m:%d %H:%M:%S")
            offset_seconds = int(dt_new.utcoffset().total_seconds())
            offset_hours = offset_seconds // 3600
            offset_minutes = (abs(offset_seconds) % 3600) // 60
            new_offset = f"{offset_hours:+03d}:{offset_minutes:02d}"

            return new_date, new_offset

        except Exception as e:
            self.logger.error(f"Error calculating new datetime/offset: {e}")
            raise

    def run(self) -> Dict[str, int]:
        """
        Process CSV file and fix timezones for specified images.

        Returns:
            Dictionary with counts: {
                'total': int,
                'processed': int,
                'skipped': int,
                'errors': int
            }
        """
        if not self.input_csv.exists():
            raise FileNotFoundError(f"CSV file not found: {self.input_csv}")

        from .immich_extract_support import ExifToolManager

        counts = {
            'total': 0,
            'processed': 0,
            'skipped': 0,
            'errors': 0
        }

        self.logger.info(f"Reading CSV file: {self.input_csv}")

        with open(self.input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                counts['total'] += 1

                file_path = row.get('file', '')
                fix_timezone = row.get('fix_timezone', '').strip()
                target_date = row.get('target_date', '')
                target_offset = row.get('target_offset', '')

                # Skip if fix_timezone is blank
                if not fix_timezone:
                    counts['skipped'] += 1
                    self.logger.debug(f"Skipping {file_path} (no fix_timezone)")
                    continue

                # Validate required fields
                if not file_path or not target_date or not target_offset:
                    counts['errors'] += 1
                    error_msg = f"Missing required fields: target_date={target_date}, target_offset={target_offset}"
                    self.logger.error(f"[AUDIT] {file_path},error,{target_date},{target_offset},,{fix_timezone},{error_msg}")
                    self.logger.error(
                        f"Missing required fields for {file_path}: "
                        f"target_date={target_date}, target_offset={target_offset}"
                    )
                    continue

                # Check if file exists
                if not Path(file_path).exists():
                    counts['errors'] += 1
                    error_msg = "File not found"
                    self.logger.error(f"[AUDIT] {file_path},error,{target_date},{target_offset},,{fix_timezone},{error_msg}")
                    self.logger.error(f"File not found: {file_path}")
                    continue

                try:
                    # Calculate new date and offset
                    new_date, new_offset = self.calculate_new_datetime_offset(
                        target_date, target_offset, fix_timezone
                    )

                    # Log the update
                    status = "dry_run" if self.dry_run else "updated"
                    self.logger.info(
                        f"[AUDIT] {file_path},{status},{target_date},{target_offset},{new_date},{new_offset},{fix_timezone},"
                    )
                    self.logger.info(
                        f"{'[DRY RUN] ' if self.dry_run else ''}Updating {file_path}: "
                        f"{target_date} {target_offset} → {new_date} {new_offset} ({fix_timezone})"
                    )

                    if not self.dry_run:
                        # Update EXIF data
                        # Get current description and tags to preserve them
                        from .image_analyzer import ImageAnalyzer
                        analyzer = ImageAnalyzer()
                        exif_data = analyzer.get_exif(file_path)

                        description = exif_data.get("Description", "")
                        tags = exif_data.get("Subject", exif_data.get("Keywords", []))
                        if not isinstance(tags, list):
                            tags = [tags] if tags else []

                        # Update with new date/offset while preserving metadata
                        ExifToolManager.update_exif(
                            file_path,
                            description,
                            tags,
                            dry_run=False,
                            date_exif=new_date,
                            skip_if_unchanged=False,
                            logger=self.logger,
                            date_exif_offset=new_offset
                        )

                    counts['processed'] += 1

                except Exception as e:
                    counts['errors'] += 1
                    error_msg = str(e)
                    self.logger.error(f"[AUDIT] {file_path},error,{target_date},{target_offset},,{fix_timezone},{error_msg}")
                    self.logger.error(f"Error processing {file_path}: {e}")

        return counts
