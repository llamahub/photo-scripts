import os
import json
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from .immich_config import ImmichConfig
from .immich_extract_support import ImmichAPI, ExifToolManager, find_image_file


def exif_date_to_iso(exif_date: str) -> str:
    """
    Convert EXIF date format (YYYY:MM:DD HH:MM:SS) to ISO format (YYYY-MM-DD HH:MM:SS).
    This makes dates Excel-compatible.
    """
    if not exif_date:
        return exif_date
    # Replace colons with hyphens in the date part (first 10 chars)
    if len(exif_date) >= 10:
        return exif_date[:4] + "-" + exif_date[5:7] + "-" + exif_date[8:10] + exif_date[10:]
    return exif_date


def calculate_timezone_from_offset(date_str: str, offset_str: str) -> str:
    """
    Calculate the most likely timezone label from a date and offset.
    Uses reverse lookup to find timezone that matches the offset at that date.
    
    Args:
        date_str: EXIF date string (YYYY:MM:DD HH:MM:SS)
        offset_str: Timezone offset (e.g., '+05:00', '-08:00', '+00:00')
    
    Returns:
        Timezone label (e.g., 'America/New_York', 'UTC') or empty string if cannot determine
    """
    if not date_str or not offset_str:
        return ""
    
    try:
        from zoneinfo import ZoneInfo, available_timezones
        
        # Parse the date (handle both EXIF format YYYY:MM:DD and ISO format YYYY-MM-DD)
        date_normalized = date_str.replace("-", ":") if "-" in date_str[:10] else date_str
        dt = datetime.strptime(date_normalized, "%Y:%m:%d %H:%M:%S")
        
        # Parse the offset
        sign = 1 if offset_str[0] == '+' else -1
        hours = int(offset_str[1:3])
        minutes = int(offset_str[4:6])
        target_offset_seconds = sign * (hours * 3600 + minutes * 60)
        
        # Common timezones to check first (optimization)
        common_timezones = [
            'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
            'UTC', 'Europe/London', 'Europe/Paris', 'Asia/Tokyo'
        ]
        
        # Check common timezones first
        for tz_name in common_timezones:
            try:
                tz = ZoneInfo(tz_name)
                dt_with_tz = dt.replace(tzinfo=tz)
                tz_offset_seconds = int(dt_with_tz.utcoffset().total_seconds())
                if tz_offset_seconds == target_offset_seconds:
                    return tz_name
            except Exception:
                continue
        
        # If not found in common, search all (slower)
        for tz_name in available_timezones():
            try:
                tz = ZoneInfo(tz_name)
                dt_with_tz = dt.replace(tzinfo=tz)
                tz_offset_seconds = int(dt_with_tz.utcoffset().total_seconds())
                if tz_offset_seconds == target_offset_seconds:
                    return tz_name
            except Exception:
                continue
        
        return ""
    except Exception:
        return ""


def timestamps_equivalent(date1: str, offset1: str, date2: str, offset2: str) -> bool:
    """
    Compare two timestamps considering their timezone offsets.
    Returns True if both represent the same moment in time (UTC equivalent).
    Ignores seconds to allow for Excel editing that may truncate precision.
    
    Args:
        date1: EXIF date string (YYYY:MM:DD HH:MM:SS)
        offset1: Timezone offset (e.g., '+05:00', '-08:00', '+00:00')
        date2: EXIF date string (YYYY:MM:DD HH:MM:SS)
        offset2: Timezone offset
    
    Returns:
        True if timestamps are equivalent in UTC (ignoring seconds), False otherwise
    """
    if not date1 or not date2:
        return False
    
    try:
        # Parse EXIF dates
        dt1 = datetime.strptime(date1, "%Y:%m:%d %H:%M:%S")
        dt2 = datetime.strptime(date2, "%Y:%m:%d %H:%M:%S")
        
        # Parse offsets and convert to timedeltas
        def parse_offset(offset_str: str) -> timedelta:
            if not offset_str:
                return timedelta(0)
            # Format: +HH:MM or -HH:MM
            sign = 1 if offset_str[0] == '+' else -1
            hours = int(offset_str[1:3])
            minutes = int(offset_str[4:6])
            return timedelta(hours=sign * hours, minutes=sign * minutes)
        
        offset1_td = parse_offset(offset1)
        offset2_td = parse_offset(offset2)
        
        # Convert both to UTC by subtracting their offsets
        utc1 = dt1 - offset1_td
        utc2 = dt2 - offset2_td
        
        # Compare UTC times, ignoring seconds (truncate to minute precision)
        utc1_truncated = utc1.replace(second=0, microsecond=0)
        utc2_truncated = utc2.replace(second=0, microsecond=0)
        
        return utc1_truncated == utc2_truncated
    except (ValueError, IndexError) as e:
        # If parsing fails, can't determine equivalence
        return False


class ImmichExtractor:
    def __init__(
        self,
        url: str,
        api_key: str,
        search_path: str,
        album: Optional[str] = None,
        search: bool = False,
        updated_after: Optional[str] = None,
        search_archive: bool = False,
        refresh_album_cache: bool = False,
        use_album_cache: bool = False,
        dry_run: bool = False,
        force_update_fuzzy: bool = False,
        disable_sidecars: bool = False,
        exif_timezone: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.url = url
        self.api_key = api_key
        self.search_path = search_path
        self.album = album
        self.search = search
        self.updated_after = updated_after
        self.exif_timezone = exif_timezone
        self.search_archive = search_archive
        self.refresh_album_cache = refresh_album_cache
        self.use_album_cache = use_album_cache
        self.dry_run = dry_run
        self.force_update_fuzzy = force_update_fuzzy
        self.disable_sidecars = disable_sidecars
        self.logger = logger or logging.getLogger("extract")
        self.api = ImmichAPI(url, api_key)
        # Try to get log file path from logger handlers
        self.log_path = None
        if self.logger and hasattr(self.logger, "handlers"):
            for h in self.logger.handlers:
                if isinstance(h, logging.FileHandler):
                    self.log_path = getattr(h, "baseFilename", None)
                    break

    def run(self):
        # --- CSV logging for EXIF log entries ---
        import csv
        from datetime import datetime
        log_dir = Path('./.log')
        log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = log_dir / f'immich_extract_{timestamp}.csv'
        csv_file = open(csv_path, 'w', newline='', encoding='utf-8')
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow([
            'file', 'status', 'current_desc', 'target_desc', 'current_tags', 'target_tags', 'current_date', 'target_date', 'current_offset', 'target_offset', 'target_timezone', 'fix_timezone', 'immich_mod_date', 'error_msg'
        ])

        def log_exif_csv(log_path, status, current_desc, target_desc, current_tags, target_tags, current_date, target_date, current_offset, target_offset, immich_mod_date, error_msg):
            # Calculate target_timezone from target_date and target_offset
            target_timezone = calculate_timezone_from_offset(target_date, target_offset) if target_date and target_offset else ""
            fix_timezone = ""  # User will fill this in manually for files they want to fix
            csv_writer.writerow([
                log_path, status, current_desc, target_desc, current_tags, target_tags, current_date, target_date, current_offset, target_offset, target_timezone, fix_timezone, immich_mod_date, error_msg
            ])
            csv_file.flush()
        self.logger.debug("Entered ImmichExtractor.run()")
        self.logger.debug(
            f"ImmichExtractor configuration: search_path={self.search_path!r}, album={self.album!r}, search={self.search}, updated_after={self.updated_after!r}"
        )
        # Album cache logic
        cache_dir = Path(".log")
        cache_dir.mkdir(exist_ok=True)
        album_cache_path = cache_dir / "immich_album_cache.json"
        album_cache = {}
        need_refresh = self.refresh_album_cache or not album_cache_path.exists()
        self.logger.debug(
            f"Album cache path: {album_cache_path}, need_refresh={need_refresh}, "
            f"use_album_cache={self.use_album_cache}"
        )
        if not need_refresh and self.use_album_cache:
            try:
                self.logger.debug("Loading album cache from file...")
                with open(album_cache_path, "r") as f:
                    album_cache = json.load(f)
            except Exception as e:
                self.logger.info(
                    f"Could not load album cache: {e}. Will refresh from Immich."
                )
                need_refresh = True
        if need_refresh:
            self.logger.info("Fetching all albums from Immich to build album cache...")
            albums = self.api.list_albums()
            self.logger.debug(f"Got {len(albums)} albums from Immich.")
            asset_to_albums = {}
            for album in albums:
                album_name = album.get("albumName", "").strip()
                album_id = album.get("id")
                if not album_id:
                    continue
                self.logger.debug(f"Fetching assets for album_id={album_id}")
                album_assets = self.api.get_album_assets(album_id)
                self.logger.debug(
                    f"Got {len(album_assets)} assets for album_id={album_id}"
                )
                for asset in album_assets:
                    aid = asset.get("id")
                    if aid:
                        asset_to_albums.setdefault(aid, set()).add(album_name)
            album_cache = {
                aid: sorted(list(names)) for aid, names in asset_to_albums.items()
            }
            with open(album_cache_path, "w") as f:
                json.dump(album_cache, f, indent=2)
            self.logger.info(f"Album cache written to {album_cache_path}")
        else:
            self.logger.info(f"Using album cache from {album_cache_path}")
            with open(album_cache_path, "r") as f:
                album_cache = json.load(f)

        self.logger.debug(f"Album cache loaded with {len(album_cache)} asset entries.")
        self.logger.debug("Entering asset selection phase (search=%s)." % self.search)
        # Asset search or album fetch
        if self.search:
            self.logger.info("Searching assets via /api/search/metadata...")
            search_payload = {}
            if self.updated_after:
                search_payload["updatedAfter"] = self.updated_after
            search_payload["withExif"] = True
            if self.search_archive:
                search_payload["isArchived"] = True
            page = 1
            assets = []
            asset_count = 0
            import requests
            try:
                while True:
                    search_payload["page"] = page
                    resp = self.api.session.post(
                        f"{self.api.base_url}/api/search/metadata", json=search_payload
                    )
                    resp.raise_for_status()
                    assets_raw = resp.json()
                    while isinstance(assets_raw, dict) and "data" in assets_raw:
                        assets_raw = assets_raw["data"]
                    if isinstance(assets_raw, dict) and "assets" in assets_raw:
                        assets_obj = assets_raw["assets"]
                        if (
                            isinstance(assets_obj, dict)
                            and "items" in assets_obj
                            and isinstance(assets_obj["items"], list)
                        ):
                            assets.extend(assets_obj["items"])
                            asset_count += len(assets_obj["items"])
                            if asset_count % 10000 == 0:
                                self.logger.info(f"Fetched {asset_count} assets so far...")
                            if assets_obj.get("nextPage"):
                                page = int(assets_obj.get("nextPage"))
                            else:
                                break
                        elif isinstance(assets_obj, list):
                            assets.extend(assets_obj)
                            asset_count += len(assets_obj)
                            if asset_count % 10000 == 0:
                                self.logger.info(f"Fetched {asset_count} assets so far...")
                            if assets_raw.get("nextPage"):
                                page = int(assets_raw.get("nextPage"))
                            else:
                                break
                        else:
                            self.logger.info(
                                "Error: Could not find asset list in search API response."
                            )
                            break
                    elif (
                        isinstance(assets_raw, dict)
                        and "assets" in assets_raw
                        and isinstance(assets_raw["assets"], list)
                    ):
                        assets.extend(assets_raw["assets"])
                        asset_count += len(assets_raw["assets"])
                        if asset_count % 10000 == 0:
                            self.logger.info(f"Fetched {asset_count} assets so far...")
                        if assets_raw.get("nextPage"):
                            page = int(assets_raw.get("nextPage"))
                        else:
                            break
                    else:
                        self.logger.info(
                            "Error: Could not find asset list in search API response."
                        )
                        break
                self.logger.info(f"Found {len(assets)} assets via search.")
            except (requests.ConnectionError, requests.exceptions.RequestException) as e:
                self.logger.error("Unable to connect to Immich server. This may be a DNS/network issue.")
                self.logger.error("If you see a 'Temporary failure in name resolution' or similar error, try running the 'reset_dns' script and re-run this command.")
                self.logger.error(f"Details: {e}")
                return {
                    "total_assets": 0,
                    "updated_count": 0,
                    "skipped_count": 0,
                    "fuzzy_match_count": 0,
                    "error_count": 1,
                    "error_files": [],
                    "audit_status_counts": {"connection_error": 1},
                }
        else:
            self.logger.info(f"Fetching assets for album {self.album}...")
            assets = self.api.get_album_assets(self.album)
            self.logger.info(f"Found {len(assets)} assets in album.")

        updated_count = 0
        skipped_count = 0
        error_count = 0
        error_files = []
        processed_files = set()
        fuzzy_match_files = set()
        current_file_for_fuzzy = {"path": None}
        fuzzy_this_file = {"fuzzy": False}
        audit_status_counts = {}

        def _datetimes_equal_with_fuzzy(dt1, dt2):
            d1 = ExifToolManager._parse_exif_datetime(dt1)
            d2 = ExifToolManager._parse_exif_datetime(dt2)
            self.logger.info(
                f"  (Debug) Comparing EXIF datetimes: raw1='{dt1}' raw2='{dt2}' "
                f"parsed1='{d1}' parsed2='{d2}'"
            )
            if d1 and d2:
                if d1 == d2:
                    return True
                delta = abs((d1 - d2).total_seconds())
                if delta <= 86400 and d1.minute == d2.minute and d1.second == d2.second:
                    if current_file_for_fuzzy["path"]:
                        fuzzy_match_files.add(current_file_for_fuzzy["path"])
                        fuzzy_this_file["fuzzy"] = True
                    self.logger.info(
                        f"  (Fuzzy match) EXIF datetimes within 24h and minutes/seconds match: "
                        f"'{dt1}' vs '{dt2}'"
                    )
                    return True
            return dt1 == dt2

        ExifToolManager._datetimes_equal = _datetimes_equal_with_fuzzy

        for i, asset in enumerate(assets, 1):
            asset_id = asset.get("id")
            file_name = asset.get("originalFileName")
            self.logger.debug(
                f"Asset {i}: Extracted file_name='{file_name}' from asset metadata: {asset}"
            )
            status = None
            log_path = None
            error_msg = ""
            if not file_name:
                status = "no_filename"
                log_path = ''
                current_desc = target_desc = current_tags = target_tags = current_date = target_date = current_offset = target_offset = immich_mod_date = error_msg = ''
                self.logger.error(f"[EXIF],{log_path},{status},{current_desc},{target_desc},{current_tags},{target_tags},{exif_date_to_iso(current_date)},{exif_date_to_iso(target_date)},{current_offset},{target_offset},{error_msg}")
                log_exif_csv(log_path, status, current_desc, target_desc, current_tags, target_tags, exif_date_to_iso(current_date), exif_date_to_iso(target_date), current_offset, target_offset, immich_mod_date, error_msg)
                audit_status_counts[status] = audit_status_counts.get(status, 0) + 1
                skipped_count += 1
                continue
            details = self.api.get_asset_details(asset_id) or asset
            immich_mod_date = details.get("updatedAt", "")
            tags_raw = details.get("tags", [])
            description = details.get("description", "").strip()
            if not description:
                exif_info = details.get("exifInfo", {})
                description = exif_info.get("description", "").strip()
            tags = []
            for t in tags_raw:
                if isinstance(t, dict):
                    if "name" in t:
                        tags.append(t["name"])
                    elif "value" in t:
                        tags.append(t["value"])
                elif isinstance(t, str):
                    tags.append(t)
            album_names = album_cache.get(asset_id, [])
            tags = sorted(set(tags + album_names))
            date_original = details.get("dateTimeOriginal", "")
            timezone_from_api = None
            if not date_original:
                exif_info = details.get("exifInfo", {})
                date_original = exif_info.get("dateTimeOriginal", "")
                timezone_from_api = exif_info.get("timeZone")
            else:
                exif_info = details.get("exifInfo", {})
                timezone_from_api = exif_info.get("timeZone") if exif_info else None
            
            date_exif = ""
            date_exif_offset = "+00:00"  # Default to UTC
            if date_original:
                import re
                from datetime import datetime, timezone

                date_exif = re.sub(r"T", " ", date_original)
                date_exif = re.sub(r"-", ":", date_exif, count=2)
                try:
                    dt = None
                    # Check if date has timezone info in the raw string
                    if "Z" in date_original or "+" in date_original or "-" in date_original[10:]:
                        # Has timezone info - parse it
                        dt = datetime.fromisoformat(
                            date_original.replace("Z", "+00:00")
                        )
                        
                        # Determine which timezone to use for EXIF output
                        target_tz_to_use = None
                        
                        # Priority 1: Use timezone from API if available (e.g., "UTC-5")
                        if timezone_from_api:
                            try:
                                # Parse timezone like "UTC-5" or "UTC+5:30"
                                import re as regex
                                tz_match = regex.match(r'UTC([+-])(\d+)(?::(\d+))?', timezone_from_api)
                                if tz_match:
                                    sign = -1 if tz_match.group(1) == '-' else 1
                                    hours = int(tz_match.group(2))
                                    minutes = int(tz_match.group(3)) if tz_match.group(3) else 0
                                    offset_seconds = sign * (hours * 3600 + minutes * 60)
                                    offset_hours = int(offset_seconds // 3600)
                                    offset_minutes = int((abs(offset_seconds) % 3600) // 60)
                                    date_exif_offset = f"{'+' if offset_seconds >= 0 else '-'}{abs(offset_hours):02d}:{offset_minutes:02d}"
                                    # Convert to that offset
                                    from datetime import timedelta
                                    dt_local = dt + timedelta(seconds=offset_seconds)
                                    date_exif = dt_local.strftime("%Y:%m:%d %H:%M:%S")
                                    target_tz_to_use = True  # Mark that we used API timezone
                            except Exception as e:
                                self.logger.debug(f"Could not parse API timezone '{timezone_from_api}': {e}")
                        
                        # Priority 2: Use user-specified timezone if API didn't provide one
                        if not target_tz_to_use and self.exif_timezone:
                            from zoneinfo import ZoneInfo
                            try:
                                target_tz = ZoneInfo(self.exif_timezone)
                                dt_local = dt.astimezone(target_tz)
                                date_exif = dt_local.strftime("%Y:%m:%d %H:%M:%S")
                                # Calculate the offset for this specific datetime
                                offset_seconds = dt_local.utcoffset().total_seconds()
                                offset_hours = int(offset_seconds // 3600)
                                offset_minutes = int((abs(offset_seconds) % 3600) // 60)
                                date_exif_offset = f"{'+' if offset_seconds >= 0 else '-'}{abs(offset_hours):02d}:{offset_minutes:02d}"
                            except Exception as e:
                                self.logger.warning(f"Could not convert to timezone '{self.exif_timezone}': {e}. Using UTC.")
                                dt_utc = dt.astimezone(timezone.utc)
                                date_exif = dt_utc.strftime("%Y:%m:%d %H:%M:%S")
                                date_exif_offset = "+00:00"
                        elif not target_tz_to_use:
                            # No timezone specified - use UTC
                            dt_utc = dt.astimezone(timezone.utc)
                            date_exif = dt_utc.strftime("%Y:%m:%d %H:%M:%S")
                            date_exif_offset = "+00:00"
                    else:
                        # No timezone info - interpret as specified timezone (or server timezone if not specified)
                        if self.exif_timezone:
                            from zoneinfo import ZoneInfo
                            try:
                                tz = ZoneInfo(self.exif_timezone)
                                dt = datetime.strptime(date_exif, "%Y:%m:%d %H:%M:%S")
                                dt = dt.replace(tzinfo=tz)
                                date_exif = dt.strftime("%Y:%m:%d %H:%M:%S")
                                # Calculate the offset for this specific datetime
                                offset_seconds = dt.utcoffset().total_seconds()
                                offset_hours = int(offset_seconds // 3600)
                                offset_minutes = int((abs(offset_seconds) % 3600) // 60)
                                date_exif_offset = f"{'+' if offset_seconds >= 0 else '-'}{abs(offset_hours):02d}:{offset_minutes:02d}"
                            except Exception as e:
                                self.logger.warning(f"Could not parse timezone '{self.exif_timezone}': {e}. Using UTC as fallback.")
                                dt = datetime.strptime(date_exif, "%Y:%m:%d %H:%M:%S")
                                dt = dt.replace(tzinfo=timezone.utc)
                                date_exif_offset = "+00:00"
                        else:
                            # No timezone specified - assume UTC (legacy behavior)
                            dt = datetime.strptime(date_exif, "%Y:%m:%d %H:%M:%S")
                            dt = dt.replace(tzinfo=timezone.utc)
                            date_exif_offset = "+00:00"
                except Exception:
                    date_exif = re.sub(
                        r"(\d{2}:\d{2}:\d{2})([.\d]*)?(Z|[+-]\d+:?\d+)?$",
                        r"\1",
                        date_exif,
                    )

            # Reconstruct local file path using originalPath
            original_path = asset.get("originalPath")
            image_path = None
            if original_path:
                self.logger.debug(f"Asset {i}: originalPath present: {original_path}")
                rel_path = original_path.lstrip("/")
                rel_parts = rel_path.split("/")
                # Replace the root folder with the basename of search_path
                if rel_parts:
                    rel_parts[0] = os.path.basename(self.search_path.rstrip("/"))
                local_path = os.path.join(self.search_path, *rel_parts[1:])
                if os.path.exists(local_path):
                    image_path = local_path
                    self.logger.debug(
                        f"Asset {i}: Using reconstructed path from originalPath: {local_path}"
                    )
                else:
                    self.logger.debug(
                        f"Asset {i}: Reconstructed path does not exist: {local_path}"
                    )
            if not image_path:
                from .immich_extract_support import find_image_file

                self.logger.debug(
                    f"Asset {i}: Calling find_image_file for '{file_name}' with search_path={self.search_path!r}"
                )
                image_path = find_image_file(
                    file_name, self.search_path, logger=self.logger
                )
                self.logger.debug(
                    f"Asset {i}: find_image_file returned: {image_path!r}"
                )
            if not image_path:
                status = "not_found"
                log_path = file_name
                current_desc = target_desc = current_tags = target_tags = current_date = target_date = current_offset = target_offset = error_msg = ''
                self.logger.error(f"[EXIF],{log_path},{status},{current_desc},{target_desc},{current_tags},{target_tags},{exif_date_to_iso(current_date)},{exif_date_to_iso(target_date)},{current_offset},{target_offset},{error_msg}")
                log_exif_csv(log_path, status, current_desc, target_desc, current_tags, target_tags, exif_date_to_iso(current_date), exif_date_to_iso(target_date), current_offset, target_offset, immich_mod_date, error_msg)
                audit_status_counts[status] = audit_status_counts.get(status, 0) + 1
                skipped_count += 1
                continue
            abs_image_path = os.path.abspath(image_path)
            log_path = abs_image_path
            # Only process files within the search paths
            in_search_path = False
            for search_path in [self.search_path]:
                if abs_image_path.startswith(os.path.abspath(search_path) + os.sep):
                    in_search_path = True
                    break
            if not in_search_path:
                status = "skipped"
                error_msg = f"not in search paths: {abs_image_path}"
                self.logger.audit(
                    f"[EXIF],{log_path},{status},,,,,,,,,,{error_msg}"
                )
                audit_status_counts[status] = audit_status_counts.get(status, 0) + 1
                skipped_count += 1
                continue
            if abs_image_path in processed_files:
                status = "skipped"
                error_msg = "duplicate: already processed in this run"
                self.logger.audit(
                    f"[EXIF],{log_path},{status},,,,,,,,,,{error_msg}"
                )
                audit_status_counts[status] = audit_status_counts.get(status, 0) + 1
                skipped_count += 1
                continue
            processed_files.add(abs_image_path)
            current_file_for_fuzzy["path"] = abs_image_path
            fuzzy_this_file["fuzzy"] = False
            # Get current EXIF for logging
            from .image_analyzer import ImageAnalyzer

            error_msg = ""
            try:
                analyzer = ImageAnalyzer()
                exif_data = analyzer.get_exif(abs_image_path)
                if not exif_data:
                    raise RuntimeError("No EXIF data returned")
                current_desc = exif_data.get("Description", "")
                current_tags = exif_data.get("Subject", exif_data.get("Keywords", []))
                if isinstance(current_tags, list):
                    current_tags = ";".join(sorted([str(t) for t in current_tags]))
                else:
                    current_tags = str(current_tags)
                current_date = exif_data.get("DateTimeOriginal", "")
                current_offset = exif_data.get("OffsetTimeOriginal", "")
            except Exception as e:
                current_desc = ""
                current_tags = ""
                current_date = ""
                current_offset = ""
                error_msg = f"EXIF read error: {e}"
                status = "error"
                target_desc = description
                target_tags = ";".join(sorted([str(t) for t in tags]))
                target_date = date_exif
                target_offset = date_exif_offset if date_exif else ""
                self.logger.error(f"[EXIF],{log_path},{status},{current_desc},{target_desc},{current_tags},{target_tags},{exif_date_to_iso(current_date)},{exif_date_to_iso(target_date)},{current_offset},{target_offset},{error_msg}")
                log_exif_csv(log_path, status, current_desc, target_desc, current_tags, target_tags, exif_date_to_iso(current_date), exif_date_to_iso(target_date), current_offset, target_offset, immich_mod_date, error_msg)
                audit_status_counts[status] = audit_status_counts.get(status, 0) + 1
                error_count += 1
                error_files.append(file_name)
                continue
            target_desc = description
            target_tags = ";".join(sorted([str(t) for t in tags]))
            target_date = date_exif
            target_offset = date_exif_offset if date_exif else ""
            
            # Check if timestamps are equivalent when considering offsets
            timestamps_are_equivalent = (current_date and target_date and 
                                        timestamps_equivalent(current_date, current_offset, target_date, target_offset))
            
            # If timestamps are equivalent and everything matches, skip entirely
            if (timestamps_are_equivalent and
                current_desc == target_desc and 
                current_tags == target_tags):
                status = "offset_equivalent"
                error_msg = "timestamps equivalent (same UTC time) and tags/description match"
                self.logger.audit(f"[EXIF],{log_path},{status},{current_desc},{target_desc},{current_tags},{target_tags},{exif_date_to_iso(current_date)},{exif_date_to_iso(target_date)},{current_offset},{target_offset},{error_msg}")
                log_exif_csv(log_path, status, current_desc, target_desc, current_tags, target_tags, exif_date_to_iso(current_date), exif_date_to_iso(target_date), current_offset, target_offset, immich_mod_date, error_msg)
                audit_status_counts[status] = audit_status_counts.get(status, 0) + 1
                skipped_count += 1
                continue
            
            # If timestamps are equivalent but tags/description differ, only update metadata (not timestamp)
            # Use None for date to preserve existing timestamp
            update_date = None if timestamps_are_equivalent else date_exif
            update_offset = None if timestamps_are_equivalent else (date_exif_offset if date_exif else None)
            
            result = ExifToolManager.update_exif(
                image_path,
                description,
                tags,
                self.dry_run,
                update_date,
                skip_if_unchanged=True,
                logger=self.logger,
                date_exif_offset=update_offset,
            )
            if (
                result == "skipped"
                and self.force_update_fuzzy
                and fuzzy_this_file["fuzzy"]
            ):
                status = "fuzzy_forced"
                error_msg = "fuzzy match forced update"
                self.logger.audit(f"[EXIF],{log_path},{status},{current_desc},{target_desc},{current_tags},{target_tags},{exif_date_to_iso(current_date)},{exif_date_to_iso(target_date)},{current_offset},{target_offset},{error_msg}")
                log_exif_csv(log_path, status, current_desc, target_desc, current_tags, target_tags, exif_date_to_iso(current_date), exif_date_to_iso(target_date), current_offset, target_offset, immich_mod_date, error_msg)
                audit_status_counts[status] = audit_status_counts.get(status, 0) + 1
                # Use the same logic as above: don't update timestamp if offset_equivalent
                result = ExifToolManager.update_exif(
                    image_path,
                    description,
                    tags,
                    self.dry_run,
                    update_date,
                    skip_if_unchanged=False,
                    logger=self.logger,
                    date_exif_offset=update_offset,
                )
            elif result == "skipped" and fuzzy_this_file["fuzzy"]:
                status = "fuzzy_skipped"
                error_msg = "fuzzy match: EXIF datetimes within 24h and minutes/seconds match"
                self.logger.audit(f"[EXIF],{log_path},{status},{current_desc},{target_desc},{current_tags},{target_tags},{exif_date_to_iso(current_date)},{exif_date_to_iso(target_date)},{current_offset},{target_offset},{error_msg}")
                log_exif_csv(log_path, status, current_desc, target_desc, current_tags, target_tags, exif_date_to_iso(current_date), exif_date_to_iso(target_date), current_offset, target_offset, immich_mod_date, error_msg)
                audit_status_counts[status] = audit_status_counts.get(status, 0) + 1
            elif result == "skipped":
                status = "skipped"
                error_msg = "EXIF already matches"
                self.logger.audit(f"[EXIF],{log_path},{status},{current_desc},{target_desc},{current_tags},{target_tags},{exif_date_to_iso(current_date)},{exif_date_to_iso(target_date)},{current_offset},{target_offset},{error_msg}")
                log_exif_csv(log_path, status, current_desc, target_desc, current_tags, target_tags, exif_date_to_iso(current_date), exif_date_to_iso(target_date), current_offset, target_offset, immich_mod_date, error_msg)
                audit_status_counts[status] = audit_status_counts.get(status, 0) + 1
            elif result == "updated":
                status = "updated"
                self.logger.audit(f"[EXIF],{log_path},{status},{current_desc},{target_desc},{current_tags},{target_tags},{exif_date_to_iso(current_date)},{exif_date_to_iso(target_date)},{current_offset},{target_offset},{error_msg}")
                log_exif_csv(log_path, status, current_desc, target_desc, current_tags, target_tags, exif_date_to_iso(current_date), exif_date_to_iso(target_date), current_offset, target_offset, immich_mod_date, error_msg)
                audit_status_counts[status] = audit_status_counts.get(status, 0) + 1
                updated_count += 1
            else:
                status = "error"
                error_msg = "Update failed"
                self.logger.error(f"[EXIF],{log_path},{status},{current_desc},{target_desc},{current_tags},{target_tags},{exif_date_to_iso(current_date)},{exif_date_to_iso(target_date)},{current_offset},{target_offset},{error_msg}")
                log_exif_csv(log_path, status, current_desc, target_desc, current_tags, target_tags, exif_date_to_iso(current_date), exif_date_to_iso(target_date), current_offset, target_offset, immich_mod_date, error_msg)
                audit_status_counts[status] = audit_status_counts.get(status, 0) + 1
                error_count += 1
                error_files.append(file_name)

            current_file_for_fuzzy["path"] = None
            # Progress indicator every 50 files
            if i % 50 == 0:
                self.logger.info(f"Processed {i}/{len(assets)} files...")

        # Close CSV file
        csv_file.close()

        # Disable sidecar files if requested
        sidecars_disabled = 0
        if self.disable_sidecars:
            self.logger.info("\n" + "="*50)
            self.logger.info("Disabling sidecar files...")
            self.logger.info("="*50)
            sidecars_disabled = self._disable_sidecar_files(processed_files)

        # Close CSV file and return summary for logging by caller
        return {
            "total_assets": len(assets),
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "fuzzy_match_count": len(fuzzy_match_files),
            "error_count": error_count,
            "error_files": error_files,
            "audit_status_counts": audit_status_counts,
            "sidecars_disabled": sidecars_disabled,
        }

    def _disable_sidecar_files(self, processed_files):
        """
        Rename sidecar files (.xmp and .supplemental-metadata.json) to .bak.
        Scans the search_path recursively for ALL sidecars and disables them,
        regardless of whether they correspond to processed files.
        """
        from pathlib import Path
        
        sidecars_disabled = 0
        xmp_count = 0
        json_count = 0
        error_count = 0
        
        search_path_obj = Path(self.search_path)
        
        # Scan for and disable ALL .xmp files
        self.logger.debug(f"Scanning for .xmp sidecars in {self.search_path}")
        for xmp_path in search_path_obj.rglob("*.xmp"):
            xmp_path_str = str(xmp_path)
            xmp_bak_path = f"{xmp_path_str}.bak"
            try:
                if self.dry_run:
                    self.logger.audit(f"[DRY RUN] Would rename sidecar: {xmp_path.name}")
                else:
                    os.rename(xmp_path_str, xmp_bak_path)
                    self.logger.audit(f"Renamed sidecar: {xmp_path_str} -> {xmp_bak_path}")
                sidecars_disabled += 1
                xmp_count += 1
            except Exception as e:
                self.logger.error(f"Failed to disable sidecar {xmp_path_str}: {e}")
                error_count += 1
        
        # Scan for and disable ALL .supplemental-metadata.json files
        self.logger.debug(f"Scanning for .supplemental-metadata.json sidecars in {self.search_path}")
        for json_path in search_path_obj.rglob("*.supplemental-metadata.json"):
            json_path_str = str(json_path)
            json_bak_path = f"{json_path_str}.bak"
            try:
                if self.dry_run:
                    self.logger.audit(f"[DRY RUN] Would rename sidecar: {json_path.name}")
                else:
                    os.rename(json_path_str, json_bak_path)
                    self.logger.audit(f"Renamed sidecar: {json_path_str} -> {json_bak_path}")
                sidecars_disabled += 1
                json_count += 1
            except Exception as e:
                self.logger.error(f"Failed to disable sidecar {json_path_str}: {e}")
                error_count += 1
        
        # Log summary
        self.logger.audit(f"Sidecar disabling summary:")
        self.logger.audit(f"  .xmp files disabled: {xmp_count}")
        self.logger.audit(f"  .supplemental-metadata.json files disabled: {json_count}")
        if error_count > 0:
            self.logger.audit(f"  Errors encountered: {error_count}")
        
        return sidecars_disabled
