import os
import json
import logging
from pathlib import Path
from typing import List, Optional
from .immich_config import ImmichConfig
from .immich_extract_support import ImmichAPI, ExifToolManager, find_image_file

class ImmichExtractor:
    def __init__(self, url: str, api_key: str, search_paths: List[str], album: Optional[str] = None, search: bool = False, updated_after: Optional[str] = None, search_archive: bool = False, refresh_album_cache: bool = False, use_album_cache: bool = False, dry_run: bool = False, force_update_fuzzy: bool = False, logger: Optional[logging.Logger] = None):
        self.url = url
        self.api_key = api_key
        self.search_paths = search_paths
        self.album = album
        self.search = search
        self.updated_after = updated_after
        self.search_archive = search_archive
        self.refresh_album_cache = refresh_album_cache
        self.use_album_cache = use_album_cache
        self.dry_run = dry_run
        self.force_update_fuzzy = force_update_fuzzy
        self.logger = logger or logging.getLogger("extract")
        self.api = ImmichAPI(url, api_key)
        # Try to get log file path from logger handlers
        self.log_path = None
        if self.logger and hasattr(self.logger, 'handlers'):
            for h in self.logger.handlers:
                if isinstance(h, logging.FileHandler):
                    self.log_path = getattr(h, 'baseFilename', None)
                    break

    def run(self):
        self.logger.debug("Entered ImmichExtractor.run()")
        # Album cache logic
        cache_dir = Path('.log')
        cache_dir.mkdir(exist_ok=True)
        album_cache_path = cache_dir / 'immich_album_cache.json'
        album_cache = {}
        need_refresh = self.refresh_album_cache or not album_cache_path.exists()
        self.logger.debug(
            f"Album cache path: {album_cache_path}, need_refresh={need_refresh}, "
            f"use_album_cache={self.use_album_cache}"
        )
        if not need_refresh and self.use_album_cache:
            try:
                self.logger.debug("Loading album cache from file...")
                with open(album_cache_path, 'r') as f:
                    album_cache = json.load(f)
            except Exception as e:
                self.logger.info(f"Could not load album cache: {e}. Will refresh from Immich.")
                need_refresh = True
        if need_refresh:
            self.logger.info("Fetching all albums from Immich to build album cache...")
            albums = self.api.list_albums()
            self.logger.debug(f"Got {len(albums)} albums from Immich.")
            asset_to_albums = {}
            for album in albums:
                album_name = album.get('albumName', '').strip()
                album_id = album.get('id')
                if not album_id:
                    continue
                self.logger.debug(f"Fetching assets for album_id={album_id}")
                album_assets = self.api.get_album_assets(album_id)
                self.logger.debug(f"Got {len(album_assets)} assets for album_id={album_id}")
                for asset in album_assets:
                    aid = asset.get('id')
                    if aid:
                        asset_to_albums.setdefault(aid, set()).add(album_name)
            album_cache = {aid: sorted(list(names)) for aid, names in asset_to_albums.items()}
            with open(album_cache_path, 'w') as f:
                json.dump(album_cache, f, indent=2)
            self.logger.info(f"Album cache written to {album_cache_path}")
        else:
            self.logger.info(f"Using album cache from {album_cache_path}")
            with open(album_cache_path, 'r') as f:
                album_cache = json.load(f)

        self.logger.debug(f"Album cache loaded with {len(album_cache)} asset entries.")
        # Asset search or album fetch
        if self.search:
            self.logger.info("Searching assets via /api/search/metadata...")
            search_payload = {}
            if self.updated_after:
                search_payload['updatedAfter'] = self.updated_after
            search_payload['withExif'] = True
            if self.search_archive:
                search_payload['isArchived'] = True
            page = 1
            assets = []
            asset_count = 0
            while True:
                search_payload['page'] = page
                resp = self.api.session.post(f"{self.api.base_url}/api/search/metadata", json=search_payload)
                resp.raise_for_status()
                assets_raw = resp.json()
                while isinstance(assets_raw, dict) and 'data' in assets_raw:
                    assets_raw = assets_raw['data']
                if isinstance(assets_raw, dict) and 'assets' in assets_raw:
                    assets_obj = assets_raw['assets']
                    if (
                        isinstance(assets_obj, dict)
                        and 'items' in assets_obj
                        and isinstance(assets_obj['items'], list)
                    ):
                        assets.extend(assets_obj['items'])
                        asset_count += len(assets_obj['items'])
                        if asset_count % 10000 == 0:
                            self.logger.info(f"Fetched {asset_count} assets so far...")
                        if assets_obj.get('nextPage'):
                            page = int(assets_obj.get('nextPage'))
                        else:
                            break
                    elif isinstance(assets_obj, list):
                        assets.extend(assets_obj)
                        asset_count += len(assets_obj)
                        if asset_count % 10000 == 0:
                            self.logger.info(f"Fetched {asset_count} assets so far...")
                        if assets_raw.get('nextPage'):
                            page = int(assets_raw.get('nextPage'))
                        else:
                            break
                    else:
                        self.logger.info("Error: Could not find asset list in search API response.")
                        break
                elif (
                    isinstance(assets_raw, dict)
                    and 'assets' in assets_raw
                    and isinstance(assets_raw['assets'], list)
                ):
                    assets.extend(assets_raw['assets'])
                    asset_count += len(assets_raw['assets'])
                    if asset_count % 10000 == 0:
                        self.logger.info(f"Fetched {asset_count} assets so far...")
                    if assets_raw.get('nextPage'):
                        page = int(assets_raw.get('nextPage'))
                    else:
                        break
                else:
                    self.logger.info("Error: Could not find asset list in search API response.")
                    break
            self.logger.info(f"Found {len(assets)} assets via search.")
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
        current_file_for_fuzzy = {'path': None}
        fuzzy_this_file = {'fuzzy': False}


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
                    if current_file_for_fuzzy['path']:
                        fuzzy_match_files.add(current_file_for_fuzzy['path'])
                        fuzzy_this_file['fuzzy'] = True
                    self.logger.info(
                        f"  (Fuzzy match) EXIF datetimes within 24h and minutes/seconds match: "
                        f"'{dt1}' vs '{dt2}'"
                    )
                    return True
            return dt1 == dt2
        ExifToolManager._datetimes_equal = _datetimes_equal_with_fuzzy

        for i, asset in enumerate(assets, 1):
            asset_id = asset.get('id')
            file_name = asset.get('originalFileName')
            status = None
            log_path = None
            if not file_name:
                status = 'no_filename'
                self.logger.audit(f"[AUDIT] (asset {asset_id}) : {status}")
                skipped_count += 1
                continue
            details = self.api.get_asset_details(asset_id) or asset
            tags_raw = details.get('tags', [])
            description = details.get('description', '').strip()
            if not description:
                exif_info = details.get('exifInfo', {})
                description = exif_info.get('description', '').strip()
            tags = []
            for t in tags_raw:
                if isinstance(t, dict):
                    if 'name' in t:
                        tags.append(t['name'])
                    elif 'value' in t:
                        tags.append(t['value'])
                elif isinstance(t, str):
                    tags.append(t)
            album_names = album_cache.get(asset_id, [])
            tags = sorted(set(tags + album_names))
            date_original = details.get('dateTimeOriginal', '')
            if not date_original:
                exif_info = details.get('exifInfo', {})
                date_original = exif_info.get('dateTimeOriginal', '')
            date_exif = ''
            if date_original:
                import re
                from datetime import datetime, timezone
                date_exif = re.sub(r'T', ' ', date_original)
                date_exif = re.sub(r'-', ':', date_exif, count=2)
                try:
                    dt = None
                    if 'Z' in date_exif or '+' in date_exif or '-' in date_exif[10:]:
                        dt = datetime.fromisoformat(date_original.replace('Z', '+00:00'))
                    else:
                        dt = datetime.strptime(date_exif, "%Y:%m:%d %H:%M:%S")
                        dt = dt.replace(tzinfo=timezone.utc)
                    dt_utc = dt.astimezone(timezone.utc)
                    date_exif = dt_utc.strftime("%Y:%m:%d %H:%M:%S")
                except Exception:
                    date_exif = re.sub(r'(\d{2}:\d{2}:\d{2})([.\d]*)?(Z|[+-]\d+:?\d+)?$', r'\1', date_exif)
            image_path = find_image_file(file_name, self.search_paths, logger=self.logger)
            if not image_path:
                status = 'not_found'
                self.logger.audit(f"{file_name} : {status}")
                skipped_count += 1
                continue
            abs_image_path = os.path.abspath(image_path)
            log_path = abs_image_path
            if abs_image_path in processed_files:
                status = 'skipped'
                self.logger.audit(f"{log_path} : {status}")
                skipped_count += 1
                continue
            processed_files.add(abs_image_path)
            current_file_for_fuzzy['path'] = abs_image_path
            fuzzy_this_file['fuzzy'] = False
            result = ExifToolManager.update_exif(
                image_path, description, tags, self.dry_run, date_exif, skip_if_unchanged=True
            )
            if result == 'skipped' and self.force_update_fuzzy and fuzzy_this_file['fuzzy']:
                status = 'fuzzy_forced'
                self.logger.audit(f"{log_path} : {status}")
                result = ExifToolManager.update_exif(
                    image_path, description, tags, self.dry_run, date_exif, skip_if_unchanged=False
                )
            elif result == 'skipped' and fuzzy_this_file['fuzzy']:
                status = 'fuzzy_skipped'
                self.logger.audit(f"{log_path} : {status}")
            elif result == 'skipped':
                status = 'skipped'
                self.logger.audit(f"{log_path} : {status}")
            elif result == 'updated':
                status = 'updated'
                self.logger.audit(f"{log_path} : {status}")
                updated_count += 1
            else:
                status = 'error'
                self.logger.error(f"{log_path} : {status}")
                error_count += 1
                error_files.append(file_name)
            current_file_for_fuzzy['path'] = None
            # Progress indicator every 50 files
            if i % 50 == 0:
                self.logger.info(f"Processed {i}/{len(assets)} files...")

        # Return summary for logging by caller
        return {
            'total_assets': len(assets),
            'updated_count': updated_count,
            'skipped_count': skipped_count,
            'fuzzy_match_count': len(fuzzy_match_files),
            'error_count': error_count,
            'error_files': error_files,
        }
