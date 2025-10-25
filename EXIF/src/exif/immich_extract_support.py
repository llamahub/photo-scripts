import requests
import subprocess
import os
import json
import logging
from pathlib import Path
from typing import List, Optional

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
    def update_exif(file_path, description, tags, dry_run=False, date_exif=None, skip_if_unchanged=False, logger=None):
        if not os.path.exists(file_path):
            if logger:
                logger.error(f"File does not exist: {file_path}")
            return "error"


        # Determine file extension (case-insensitive)
        ext = os.path.splitext(file_path)[1].lower()
        is_heic = ext in ['.heic', '.heif']

        # Read current EXIF data, including Subject for HEIC
        exiftool_args = [
            'exiftool',
            '-j',
            '-Description',
            '-DateTimeOriginal',
        ]
        if is_heic:
            exiftool_args.append('-Subject')
        else:
            exiftool_args.append('-Keywords')
        exiftool_args.append(file_path)
        try:
            result = subprocess.run(exiftool_args, capture_output=True, text=True, check=True)
            exif_data = json.loads(result.stdout)[0] if result.stdout else {}
        except Exception as e:
            if logger:
                logger.error(f"Error reading EXIF from {file_path}: {e}")
            return "error"

        # Normalize tags/keywords for comparison
        def norm_tags(val):
            if isinstance(val, list):
                return sorted([str(t).strip() for t in val])
            if isinstance(val, str):
                return sorted([t.strip() for t in val.split(',') if t.strip()])
            return []

        current_desc = exif_data.get('Description', '').strip()
        if is_heic:
            current_tags = norm_tags(exif_data.get('Subject', []))
        else:
            current_tags = norm_tags(exif_data.get('Keywords', []))
        current_date = exif_data.get('DateTimeOriginal', '').strip()
        target_tags = norm_tags(tags)
        target_desc = (description or '').strip()
        target_date = (date_exif or '').strip()

        if logger:
            logger.debug(f"EXIF compare for {file_path}:")
            logger.debug(f"  Current Description: '{current_desc}'")
            logger.debug(f"  Target  Description: '{target_desc}'")
            logger.debug(f"  Current Tags: {current_tags}")
            logger.debug(f"  Target  Tags: {target_tags}")
            logger.debug(f"  Current DateTimeOriginal: '{current_date}'")
            logger.debug(f"  Target  DateTimeOriginal: '{target_date}'")

        unchanged = (
            current_desc == target_desc and
            current_tags == target_tags and
            (not target_date or current_date == target_date)
        )

        if skip_if_unchanged and unchanged:
            if logger:
                logger.info(f"Skipping update for {file_path}: EXIF already matches.")
            return "skipped"

        if dry_run:
            if logger:
                logger.info(f"Would update EXIF for {file_path} (dry run)")
            return "updated"

        # Build exiftool command for update
        cmd = ['exiftool', '-overwrite_original']
        if description is not None:
            cmd += [f'-Description={description}']
        if tags:
            for tag in target_tags:
                if is_heic:
                    cmd += [f'-Subject={tag}']
                else:
                    cmd += [f'-Keywords={tag}']
        if date_exif:
            cmd += [f'-DateTimeOriginal={date_exif}']
        cmd.append(file_path)
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            if logger:
                logger.info(f"Updated EXIF for {file_path}")
            return "updated"
        except Exception as e:
            if logger:
                logger.error(f"Error updating EXIF for {file_path}: {e}")
            return "error"
    @staticmethod
    def check_exiftool():
        try:
            subprocess.run(['exiftool', '-ver'], capture_output=True, check=True)
            return True
        except Exception:
            return False
    # ... (other methods as in original script)


def find_image_file(file_name: str, search_paths: list, logger: logging.Logger = None) -> Optional[str]:
    if logger is None:
        logger = logging.getLogger("extract")
    logger.debug(f"find_image_file: Searching for '{file_name}' in {search_paths}")
    for search_path in search_paths:
        search_dir = Path(search_path)
        logger.debug(f"Searching directory: {search_dir}")
        if search_dir.exists():
            try:
                for file_path in search_dir.rglob(file_name):
                    logger.debug(f"Checking file: {file_path}")
                    if file_path.is_file():
                        logger.debug(f"Found file: {file_path}")
                        return str(file_path)
            except Exception as e:
                logger.debug(f"Error searching {search_dir}: {e}")
    logger.debug(f"File '{file_name}' not found in any search path.")
    return None
