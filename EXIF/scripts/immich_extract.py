#!/usr/bin/env python3
"""
Immich Album Description and Tag Extractor/EXIF Updater

This script pulls description and tags from Immich for all photos in a given album
and uses exiftool to update the EXIF data directly.

Requirements:
- requests library: pip install requests
- exiftool installed on system
- Immich instance with API access

Usage:
  python extract.py --url IMMICH_URL --api-Key IMMICH_API_KEY --album ALBUM_ID --search-paths DIR1 [DIR2 ...] [--dry-run]
"""


import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional
import requests
import json
import logging
from datetime import datetime

# --- Load config for .env support ---
try:
    # Try relative to EXIF/scripts/immich_extract.py (for direct run)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "COMMON" / "src"))
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

    from exif.immich_config import ImmichConfig
except ImportError:
    # Try relative to workspace root (for run wrapper or other entrypoints)
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "COMMON" / "src"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "EXIF" / "src"))

    from exif.immich_config import ImmichConfig



class ImmichAPI:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({'x-api-key': api_key})

    def get_album_assets(self, album_id: str) -> List[dict]:
        url = f"{self.base_url}/api/albums/{album_id}"
        resp = self.session.get(url)
        resp.raise_for_status()
        album = resp.json()
        return album.get('assets', [])

    def get_asset_details(self, asset_id: str) -> Optional[dict]:
        url = f"{self.base_url}/api/assets/{asset_id}"
        resp = self.session.get(url)
        if resp.status_code == 200:
            return resp.json()
        return None

    def list_albums(self) -> list:
        url = f"{self.base_url}/api/albums"
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.json()



class ExifToolManager:
    @staticmethod
    def check_exiftool():
        try:
            subprocess.run(['exiftool', '-ver'], capture_output=True, check=True)
            return True
        except Exception:
            return False

    @staticmethod
    def _parse_exif_datetime(dt_str):
        # Try to parse EXIF date/time with or without timezone, and with various formats
        from datetime import datetime, timezone
        import re
        import logging
        logger = logging.getLogger("extract")
        if not dt_str:
            return None
        dt_str = re.sub(r'[.][0-9]+', '', dt_str)
        formats = [
            "%Y:%m:%d %H:%M:%S%z",
            "%Y:%m:%d %H:%M:%S",
            "%Y:%m:%d %H:%M",
            "%Y:%m:%d"
        ]
        for fmt in formats:
            try:
                if '%z' in fmt and ('-' in dt_str[10:] or '+' in dt_str[10:]):
                    return datetime.strptime(dt_str, fmt).astimezone(timezone.utc)
                elif '%z' not in fmt:
                    return datetime.strptime(dt_str, fmt).replace(tzinfo=timezone.utc)
            except Exception:
                continue
        logger.info(f"  (Debug) Could not parse EXIF datetime: '{dt_str}'")
        return None

    @staticmethod
    def _datetimes_equal(dt1, dt2):
        import logging
        logger = logging.getLogger("extract")
        d1 = ExifToolManager._parse_exif_datetime(dt1)
        d2 = ExifToolManager._parse_exif_datetime(dt2)
        logger.info(
            f"  (Debug) Comparing EXIF datetimes: raw1='{dt1}' raw2='{dt2}' "
            f"parsed1='{d1}' parsed2='{d2}'"
        )
        if d1 and d2:
            if d1 == d2:
                return True
            # Fuzzy match: within 24 hours and minutes/seconds match
            delta = abs((d1 - d2).total_seconds())
            if delta <= 86400 and d1.minute == d2.minute and d1.second == d2.second:
                logger.info(
                    f"  (Fuzzy match) EXIF datetimes within 24h and minutes/seconds match: "
                    f"'{dt1}' vs '{dt2}'"
                )
                return True
        return dt1 == dt2  # fallback: compare as strings

    @staticmethod
    def update_exif(
        file_path: str, description: str, tags: List[str],
        dry_run: bool = False, date_exif: str = '', skip_if_unchanged: bool = False
    ) -> str:
        import logging
        logger = logging.getLogger("extract")
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.mpg':
            return ExifToolManager.handle_mpg(file_path, description, tags, dry_run, date_exif)
        if not os.path.exists(file_path):
            logger.info(f"✗ File not found: {file_path}")
            return 'error'
    # tag_str = ', '.join(tags)  # Unused variable
        # Optionally skip update if nothing has changed
        skip_date_fields = False
        if skip_if_unchanged:
            try:
                exif_cmd = [
                    'exiftool',
                    '-j',
                    '-ImageDescription',
                    '-XMP:Description',
                    '-Keywords',
                    '-XMP:Subject',
                    '-DateTimeOriginal',
                    '-CreateDate',
                    '-ModifyDate',
                    file_path
                ]
                result = subprocess.run(exif_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    meta = json.loads(result.stdout)[0]
                    # Compare description (treat missing/empty/whitespace as equivalent)
                    desc_current = meta.get('ImageDescription', '') or meta.get('XMP:Description', '')
                    desc_current = (desc_current or '').strip()
                    desc_new = (description or '').strip()
                    # Compare tags (combine Keywords and XMP:Subject, treat missing/empty/None/[''] as equivalent)
                    tags_current = meta.get('Keywords', [])
                    if tags_current is None:
                        tags_current = []
                    if isinstance(tags_current, str):
                        tags_current = [tags_current]
                    tags_subject = meta.get('XMP:Subject', [])
                    if tags_subject is None:
                        tags_subject = []
                    if isinstance(tags_subject, str):
                        tags_subject = [tags_subject]
                    
                    def split_tags(taglist):
                        result = []
                        for t in taglist:
                            if isinstance(t, str):
                                result.extend([x.strip().lower() for x in t.split(',') if x.strip()])
                            elif isinstance(t, list):
                                result.extend([x.strip().lower() for x in t if x and x.strip()])
                        return result
                    tags_current_combined = set(split_tags(tags_current) + split_tags(tags_subject))
                    if not tags_current_combined and ext in ['.heic', '.heif']:
                        exif_cmd_txt = [
                            'exiftool',
                            '-s',
                            '-Keywords',
                            '-XMP:Subject',
                            file_path
                        ]
                        result_txt = subprocess.run(exif_cmd_txt, capture_output=True, text=True)
                        tags_fallback = set()
                        for line in result_txt.stdout.splitlines():
                            if line.startswith('Keywords') or line.startswith('Subject'):
                                val = line.split(':', 1)[-1].strip()
                                if val:
                                    tags_fallback.update([
                                        t.strip().lower() for t in val.split(',') if t.strip()
                                    ])
                        tags_current_combined = tags_fallback
                    tags_new = set([t.strip().lower() for t in tags if t and t.strip()])
                    date_fields = ['DateTimeOriginal', 'CreateDate', 'ModifyDate']
                    # Compare as sets for idempotency
                    date_match = True
                    if date_exif:
                        for f in date_fields:
                            current = meta.get(f, '')
                            if not ExifToolManager._datetimes_equal(current, date_exif):
                                date_match = False
                                break
                        if date_match:
                            # All date fields already match, so do not update them
                            skip_date_fields = True
                    if (
                        desc_current == desc_new and
                        tags_current_combined == tags_new and
                        (not date_exif or date_match)
                    ):
                        logger.info(f"  ✓ No metadata changes for {file_path}, skipping update.")
                        return 'skipped'  # Distinguish skipped
                # else, fall through to update
            except Exception as e:
                logger.info(f"  ✗ Could not check existing metadata for {file_path}: {e}")
                # Fall through to update
        # Build exiftool command with each tag as a separate -Keywords argument
        cmd = [
            'exiftool',
            '-m',  # Suppress minor warnings
            '-overwrite_original',
            f'-ImageDescription={description}',
            f'-XMP:Description={description}'
        ]
        # Add each tag as a separate -Keywords argument
        for tag in tags:
            cmd.append(f'-Keywords={tag}')
        if ext in ['.heic', '.heif']:
            for tag in tags:
                cmd.append(f'-XMP:Subject={tag}')
        # Only add date fields if they need to be updated
        if date_exif and not skip_date_fields:
            cmd.extend([
                f'-DateTimeOriginal={date_exif}',
                f'-CreateDate={date_exif}',
                f'-ModifyDate={date_exif}'
            ])
        cmd.append(file_path)
        if dry_run:
            logger.info(f"DRY RUN: Would execute: {' '.join(cmd)}")
            return 'updated'
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # After successful EXIF update, set filesystem mtime to now
                try:
                    os.utime(file_path, None)  # None sets mtime to current time
                except Exception as utime_err:
                    logger.info(f"  (Warning) Could not update mtime for {file_path}: {utime_err}")
                # Also call 'touch' to ensure mtime is updated as expected for Immich
                try:
                    subprocess.run(['touch', file_path], check=True)
                except Exception as touch_err:
                    logger.info(f"  (Warning) Could not run touch for {file_path}: {touch_err}")
                logger.info(f"✓ Updated: {file_path}")
                return 'updated'
            else:
                logger.info(f"✗ Error updating {file_path}: {result.stderr}")
                return 'error'
        except Exception as e:
            logger.info(f"✗ Error running exiftool: {e}")
            return 'error'

    @staticmethod
    def handle_mpg(
        file_path: str, description: str, tags: List[str],
        dry_run: bool = False, date_exif: str = ''
    ) -> str:
        """
        If an MP4 with the same name exists in the same folder, update that instead (only if metadata has changed).
        If not, create an MP4 copy and update its metadata.
        """
        mp4_path = os.path.splitext(file_path)[0] + '.mp4'
        if os.path.exists(mp4_path):
            # Only update if metadata has changed
            return ExifToolManager.update_exif(
                mp4_path, description, tags, dry_run, date_exif, skip_if_unchanged=True
            )
        else:
            if dry_run:
                print(f"DRY RUN: Would create MP4 copy from MPG: {file_path} -> {mp4_path}")
                print(f"DRY RUN: Would update metadata for {mp4_path}")
                return 'updated'
            # Use ffmpeg to convert MPG to MP4
            try:
                import shutil
                if not shutil.which('ffmpeg'):
                    print("✗ ffmpeg not found. Cannot convert MPG to MP4.")
                    return 'error'
                print(f"Converting MPG to MP4: {file_path} -> {mp4_path}")
                ffmpeg_cmd = [
                    'ffmpeg', '-y', '-i', file_path, '-c:v', 'copy', '-c:a', 'copy', mp4_path
                ]
                result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"✗ Error converting MPG to MP4: {result.stderr}")
                    return 'error'
                print(f"✓ Created MP4: {mp4_path}. Updating metadata...")
                return ExifToolManager.update_exif(
                    mp4_path, description, tags, dry_run, date_exif, skip_if_unchanged=False
                )
            except Exception as e:
                print(f"✗ Error handling MPG file: {e}")
                return 'error'



def find_image_file(file_name: str, search_paths: List[str]) -> Optional[str]:
    for search_path in search_paths:
        search_dir = Path(search_path)
        if search_dir.exists():
            for file_path in search_dir.rglob(file_name):
                if file_path.is_file():
                    return str(file_path)
    return None



def setup_logger(log_path=None):
    logger = logging.getLogger("extract")
    logger.setLevel(logging.INFO)
    logger.handlers = []  # Remove any existing handlers
    if not log_path:
        log_dir = Path('.log')
        log_dir.mkdir(exist_ok=True)
        log_path = log_dir / f"extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    handler = logging.FileHandler(str(log_path), encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger, log_path

def main():

    parser = argparse.ArgumentParser(
        description='Extract description and tags from Immich album and update EXIF data'
    )
    parser.add_argument('--url', required=False,
        help='Immich base URL (e.g., http://localhost:2283)')
    parser.add_argument('--api-key', required=False,
        help='Immich API key')
    parser.add_argument('--album', help='Immich album ID')
    parser.add_argument('--search', action='store_true',
        help='Use Immich search API instead of album (enables --updatedAfter)')
    parser.add_argument('--updatedAfter', type=str, default=None,
        help='Only process assets updated after this ISO date/time (e.g., 2025-06-30T00:00:00Z)')
    parser.add_argument('--search-paths', nargs='+', required=True,
        help='Paths to search for image files')
    parser.add_argument('--dry-run', action='store_true',
        help='Show what would be done without making changes')
    parser.add_argument('--search-archive', action='store_true',
        help='Search for archived assets (Immich isArchived=true)')
    parser.add_argument('--refresh-album-cache', action='store_true',
        help='Force refresh album cache from Immich')
    parser.add_argument('--use-album-cache', action='store_true',
        help='Use local album cache if present (default: use cache if present, refresh if not)')
    parser.add_argument('--log-file', type=str, default=None,
        help='Path to log file (default: .log/extract_<timestamp>.log)')
    parser.add_argument('--force-update-fuzzy', action='store_true',
        help='Force update files with fuzzy datetime matches')
    args = parser.parse_args()


    # --- Load .env using common config ---
    # Try to load from EXIF/.env, fallback to workspace root .env
    project_path = Path(__file__).resolve().parent.parent
    config = None
    try:
        config = ImmichConfig(_env_file=project_path / ".env", _env_file_encoding="utf-8")
    except Exception:
        try:
            config = ImmichConfig(_env_file=Path.cwd() / ".env", _env_file_encoding="utf-8")
        except Exception:
            config = ImmichConfig()

    # Support IMMICH_URL and IMMICH_API_KEY from env or .env
    env_url = os.environ.get("IMMICH_URL")
    env_api_key = os.environ.get("IMMICH_API_KEY")

    # Precedence: CLI > ENV > config (ImmichConfig)
    url = args.url or env_url or config.immich_url
    api_key = args.api_key or env_api_key or config.immich_api_key
    if not url or not api_key:
        print("Error: Immich URL and API key must be provided via --url/--api-key, IMMICH_URL/IMMICH_API_KEY in .env, or ImmichConfig.")
        sys.exit(2)


    logger, log_path = setup_logger(args.log_file)

    # Add DEBUG output to stdout if requested
    debug = os.environ.get("DEBUG", "0") == "1" or args.dry_run
    def debug_print(msg):
        if debug:
            print(f"[DEBUG] {msg}")

    # Replace all print() except summary with logger.info()
    def log(msg):
        logger.info(msg)
        if debug:
            print(f"[LOG] {msg}")


    debug_print(f"Starting immich_extract.py with args: {sys.argv}")
    debug_print(f"Using Immich URL: {url}")
    debug_print(f"Search mode: {args.search}, Album: {args.album}")

    if args.search and args.album:
        print("Error: --search and --album cannot be used together.")
        sys.exit(1)
    if not args.search and not args.album:
        print("Error: You must specify either --album or --search.")
        sys.exit(1)

    if not ExifToolManager.check_exiftool():
        print("✗ exiftool not found. Please install exiftool first.")
        sys.exit(1)

    debug_print("Initializing ImmichAPI client...")
    api = ImmichAPI(url, api_key)
    debug_print("ImmichAPI client initialized.")

    # Album cache logic

    cache_dir = Path('.log')
    cache_dir.mkdir(exist_ok=True)
    album_cache_path = cache_dir / 'immich_album_cache.json'
    album_cache = {}
    need_refresh = args.refresh_album_cache or not album_cache_path.exists()
    debug_print(f"Album cache path: {album_cache_path}, need_refresh: {need_refresh}")
    if not need_refresh and args.use_album_cache:
        try:
            with open(album_cache_path, 'r') as f:
                album_cache = json.load(f)
            debug_print("Loaded album cache from file.")
        except Exception as e:
            log(f"Could not load album cache: {e}. Will refresh from Immich.")
            need_refresh = True
    if need_refresh:
        log("Fetching all albums from Immich to build album cache...")
        debug_print("Calling api.list_albums()...")
        albums = api.list_albums()
        debug_print(f"Fetched {len(albums)} albums.")
        # Build mapping: asset_id -> set of album names
        asset_to_albums = {}
        for album in albums:
            album_name = album.get('albumName', '').strip()
            album_id = album.get('id')
            if not album_id:
                continue
            debug_print(f"Fetching assets for album: {album_name} ({album_id})")
            album_assets = api.get_album_assets(album_id)
            debug_print(f"  Found {len(album_assets)} assets in album {album_name}")
            for asset in album_assets:
                aid = asset.get('id')
                if aid:
                    asset_to_albums.setdefault(aid, set()).add(album_name)
        # Convert sets to sorted lists for JSON
        album_cache = {aid: sorted(list(names)) for aid, names in asset_to_albums.items()}
        with open(album_cache_path, 'w') as f:
            json.dump(album_cache, f, indent=2)
        log(f"Album cache written to {album_cache_path}")
    else:
        log(f"Using album cache from {album_cache_path}")
        with open(album_cache_path, 'r') as f:
            album_cache = json.load(f)
        debug_print("Loaded album cache from file (no refresh needed).")


    if args.search:
        log("Searching assets via /api/search/metadata...")
        debug_print("Building search payload...")
        search_payload = {}
        if args.updatedAfter:
            search_payload['updatedAfter'] = args.updatedAfter
        search_payload['withExif'] = True
        if args.search_archive:
            search_payload['isArchived'] = True
        page = 1
        assets = []
        while True:
            search_payload['page'] = page
            debug_print(f"POST {api.base_url}/api/search/metadata page={page} payload={search_payload}")
            resp = api.session.post(f"{api.base_url}/api/search/metadata", json=search_payload)
            debug_print(f"Response status: {resp.status_code}")
            resp.raise_for_status()
            assets_raw = resp.json()
            debug_print(f"Raw search response: {str(assets_raw)[:200]}...")
            # Recursively unwrap all nested 'data' keys until 'assets' or no more 'data'
            while isinstance(assets_raw, dict) and 'data' in assets_raw:
                assets_raw = assets_raw['data']
            # Immich 2025+ API: assets may be under assets['items']
            if isinstance(assets_raw, dict) and 'assets' in assets_raw:
                assets_obj = assets_raw['assets']
                if isinstance(assets_obj, dict) and 'items' in assets_obj and isinstance(assets_obj['items'], list):
                    assets.extend(assets_obj['items'])
                    if assets_obj.get('nextPage'):
                        page = int(assets_obj.get('nextPage'))
                    else:
                        break
                elif isinstance(assets_obj, list):
                    assets.extend(assets_obj)
                    if assets_raw.get('nextPage'):
                        page = int(assets_raw.get('nextPage'))
                    else:
                        break
                else:
                    print("Error: Could not find asset list in search API response. Here is the response:")
                    print(json.dumps(assets_raw, indent=2))
                    break
            elif isinstance(assets_raw, dict) and 'assets' in assets_raw and isinstance(assets_raw['assets'], list):
                assets.extend(assets_raw['assets'])
                if assets_raw.get('nextPage'):
                    page = int(assets_raw.get('nextPage'))
                else:
                    break
            else:
                print("Error: Could not find asset list in search API response. Here is the response:")
                print(json.dumps(assets_raw, indent=2))
                break
        log(f"Found {len(assets)} assets via search.")
        debug_print(f"Total assets found: {len(assets)}")
    else:
        log(f"Fetching assets for album {args.album}...")
        debug_print(f"Calling api.get_album_assets({args.album})")
        assets = api.get_album_assets(args.album)
        log(f"Found {len(assets)} assets in album.")
        debug_print(f"Total assets found: {len(assets)}")

    updated_count = 0
    skipped_count = 0
    error_count = 0
    error_files = []  # Track files/assets with errors
    processed_files = set()  # Deduplicate by absolute file path
    fuzzy_match_files = set()  # Track files with at least one fuzzy match

    # Patch _datetimes_equal to increment fuzzy_match_files via closure and track per-file fuzzy status
    current_file_for_fuzzy = {'path': None}
    fuzzy_this_file = {'fuzzy': False}
    def _datetimes_equal_with_fuzzy(dt1, dt2):
        import logging
        logger = logging.getLogger("extract")
        d1 = ExifToolManager._parse_exif_datetime(dt1)
        d2 = ExifToolManager._parse_exif_datetime(dt2)
        logger.info(f"  (Debug) Comparing EXIF datetimes: raw1='{dt1}' raw2='{dt2}' parsed1='{d1}' parsed2='{d2}'")
        if d1 and d2:
            if d1 == d2:
                return True
            delta = abs((d1 - d2).total_seconds())
            if delta <= 86400 and d1.minute == d2.minute and d1.second == d2.second:
                if current_file_for_fuzzy['path']:
                    fuzzy_match_files.add(current_file_for_fuzzy['path'])
                    fuzzy_this_file['fuzzy'] = True
                logger.info(f"  (Fuzzy match) EXIF datetimes within 24h and minutes/seconds match: '{dt1}' vs '{dt2}'")
                return True
        return dt1 == dt2

    # Monkey-patch ExifToolManager._datetimes_equal for this run
    ExifToolManager._datetimes_equal = _datetimes_equal_with_fuzzy

    debug_print(f"Beginning asset processing loop for {len(assets)} assets...")
    for i, asset in enumerate(assets, 1):
        if debug and i % 10 == 0:
            print(f"[DEBUG] Processed {i} assets...")
        asset_id = asset.get('id')
        file_name = asset.get('originalFileName')
        if not file_name:
            log(f"[{i}] Skipping asset with no file name.")
            skipped_count += 1
            continue
        # Always fetch asset details to get up-to-date tags and description
        details = api.get_asset_details(asset_id) or asset
        tags_raw = details.get('tags', [])
        description = details.get('description', '').strip()
        if not description:
            # Fallback to exifInfo.description if present
            exif_info = details.get('exifInfo', {})
            description = exif_info.get('description', '').strip()
        # Only use tag 'name' or 'value' for keywords
        tags = []
        for t in tags_raw:
            if isinstance(t, dict):
                if 'name' in t:
                    tags.append(t['name'])
                elif 'value' in t:
                    tags.append(t['value'])
            elif isinstance(t, str):
                tags.append(t)
        # Add album names from cache
        album_names = album_cache.get(asset_id, [])
        tags = sorted(set(tags + album_names))
        # Extract dateTimeOriginal for EXIF date fields
        date_original = details.get('dateTimeOriginal', '')
        if not date_original:
            exif_info = details.get('exifInfo', {})
            date_original = exif_info.get('dateTimeOriginal', '')
        # exiftool expects 'YYYY:MM:DD HH:MM:SS' format in UTC
        date_exif = ''
        if date_original:
            import re
            from datetime import datetime, timezone
            # Remove timezone if present, replace T with space, and - with :
            date_exif = re.sub(r'T', ' ', date_original)
            date_exif = re.sub(r'-', ':', date_exif, count=2)
            # Parse as UTC if possible
            try:
                # Try to parse with timezone info
                dt = None
                if 'Z' in date_exif or '+' in date_exif or '-' in date_exif[10:]:
                    dt = datetime.fromisoformat(date_original.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(date_exif, "%Y:%m:%d %H:%M:%S")
                    dt = dt.replace(tzinfo=timezone.utc)
                dt_utc = dt.astimezone(timezone.utc)
                date_exif = dt_utc.strftime("%Y:%m:%d %H:%M:%S")
            except Exception:
                # fallback: strip timezone and subsecond
                date_exif = re.sub(r'(\d{2}:\d{2}:\d{2})([.\d]*)?(Z|[+-]\d+:?\d+)?$', r'\1', date_exif)
        updated_at = details.get('updatedAt', '')
        log(f"\n[{i}/{len(assets)}] {file_name}")
        log(f"  Description: {description[:100]}{'...' if len(description) > 100 else ''}")
        log(f"  Tags: {tags}")
        if date_exif:
            log(f"  DateTimeOriginal: {date_exif}")
        if updated_at:
            log(f"  Immich UpdatedAt: {updated_at}")
        image_path = find_image_file(file_name, args.search_paths)
        if not image_path:
            log(f"  ✗ Image file not found for asset: {file_name}")
            error_count += 1
            error_files.append(file_name)
            continue
        abs_image_path = os.path.abspath(image_path)
        if abs_image_path in processed_files:
            log(f"  ✓ Already processed {image_path}, skipping duplicate.")
            skipped_count += 1
            continue
        processed_files.add(abs_image_path)
        # Set current file for fuzzy match tracking
        current_file_for_fuzzy['path'] = abs_image_path
        fuzzy_this_file['fuzzy'] = False
        # Only put tags in keywords, description in description fields, and update EXIF dates
        result = ExifToolManager.update_exif(image_path, description, tags, args.dry_run, date_exif, skip_if_unchanged=True)
        # If skipped due to fuzzy match and --force-update-fuzzy is set, force update
        if result == 'skipped' and args.force_update_fuzzy and fuzzy_this_file['fuzzy']:
            log(f"  (Force update) Fuzzy datetime match detected and --force-update-fuzzy set. Forcing update.")
            result = ExifToolManager.update_exif(image_path, description, tags, args.dry_run, date_exif, skip_if_unchanged=False)
        current_file_for_fuzzy['path'] = None  # Reset after processing
        if result == 'updated':
            updated_count += 1
        elif result == 'skipped':
            skipped_count += 1
        else:
            log(f"  ✗ Error updating EXIF for file: {image_path}")
            error_count += 1
            error_files.append(file_name)

    # Print summary to stdout only
    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"{'='*50}")
    print(f"Total assets processed: {len(assets)}")
    print(f"Successfully updated: {updated_count}")
    print(f"Skipped: {skipped_count}")
    print(f"Fuzzy datetime matches: {len(fuzzy_match_files)}")
    print(f"Errors: {error_count}")
    if error_files:
        print("\nError details:")
        for ef in error_files:
            print(f"  - {ef}")
    if args.dry_run:
        print("\nThis was a dry run. No files were actually modified.")
    print(f"\nLog file: {log_path}")

def list_albums_cli():
    parser = argparse.ArgumentParser(description='List Immich albums')
    parser.add_argument('--url', required=True, help='Immich base URL (e.g., http://localhost:2283)')
    parser.add_argument('--api-key', required=True, help='Immich API key')
    args = parser.parse_args()
    api = ImmichAPI(args.url, args.api_key)
    albums = api.list_albums()
    print(f"{'ID':36}  Name")
    print('-'*60)
    for album in albums:
        print(f"{album.get('id',''):36}  {album.get('albumName','')}")

if __name__ == '__main__':
    if '--list-albums' in sys.argv:
        sys.argv.remove('--list-albums')
        list_albums_cli()
    else:
        main()
