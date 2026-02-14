"""File matching utilities with EXIF support."""

import logging
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime


class ExifReader:
    """Simple EXIF reader using exiftool."""
    
    @staticmethod
    def read_exif(file_path: str) -> Dict[str, Any]:
        """
        Read EXIF data from a file using exiftool.
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary of EXIF data
        """
        try:
            result = subprocess.run(
                ["exiftool", "-j", "-DateTimeOriginal", "-FileSize", file_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            data = json.loads(result.stdout)
            if data and len(data) > 0:
                return data[0]
            return {}
            
        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
            return {}
    
    @staticmethod
    def parse_exif_datetime(exif_date: Optional[str]) -> Optional[datetime]:
        """
        Parse EXIF datetime string to datetime object.
        
        Args:
            exif_date: EXIF date string (e.g., "2025:06:15 18:30:00")
            
        Returns:
            datetime object or None
        """
        if not exif_date:
            return None
        
        try:
            # Handle EXIF format with colons
            if ":" in exif_date[:10]:
                return datetime.strptime(exif_date, "%Y:%m:%d %H:%M:%S")
            # Handle ISO format
            elif "-" in exif_date[:10]:
                # Try with time
                if "T" in exif_date:
                    # Remove timezone info for comparison
                    clean_date = exif_date.split("+")[0].split("Z")[0]
                    return datetime.strptime(clean_date, "%Y-%m-%dT%H:%M:%S")
                else:
                    return datetime.strptime(exif_date[:19], "%Y-%m-%d %H:%M:%S")
        except (ValueError, IndexError):
            pass
        
        return None


class FileMatcher:
    """Matches Immich assets to files in target directory."""
    
    def __init__(self, target_path: str, logger: Optional[logging.Logger] = None):
        """
        Initialize file matcher.
        
        Args:
            target_path: Root directory to search for files
            logger: Optional logger instance
        """
        self.target_path = Path(target_path)
        self.logger = logger or logging.getLogger(__name__)
        self.exif_reader = ExifReader()
        
        # Build filename index for faster lookups
        self.filename_index: Dict[str, List[Path]] = {}
        self._build_filename_index()
    
    def _build_filename_index(self):
        """Build index of all image files by filename."""
        if not self.target_path.exists():
            self.logger.warning(f"Target path does not exist: {self.target_path}")
            return
        
        self.logger.info(f"Building filename index for {self.target_path}...")
        
        # Common image extensions
        image_extensions = {
            '.jpg', '.jpeg', '.png', '.heic', '.heif', 
            '.raw', '.cr2', '.nef', '.arw', '.dng',
            '.gif', '.bmp', '.tiff', '.tif'
        }
        
        count = 0
        for file_path in self.target_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                filename = file_path.name
                if filename not in self.filename_index:
                    self.filename_index[filename] = []
                self.filename_index[filename].append(file_path)
                count += 1
                
                if count % 1000 == 0:
                    self.logger.debug(f"Indexed {count} files...")
        
        self.logger.info(
            f"Indexed {count} files ({len(self.filename_index)} unique filenames)"
        )
    
    def match_asset(
        self, 
        asset_data: Dict[str, Any]
    ) -> Tuple[Optional[str], str, str]:
        """
        Match an Immich asset to a file in the target directory.
        
        Args:
            asset_data: Immich asset data
            
        Returns:
            Tuple of (matched_path, match_confidence, match_method)
            - matched_path: Full path to matched file or None
            - match_confidence: "exact", "fuzzy", "none"
            - match_method: Description of how match was made
        """
        filename = asset_data.get("originalFileName")
        if not filename:
            return None, "none", "no_filename"
        
        # Find candidates by filename
        candidates = self.filename_index.get(filename, [])
        
        if not candidates:
            return None, "none", "no_file_found"
        
        if len(candidates) == 1:
            # Single match - high confidence
            return str(candidates[0]), "exact", "unique_filename"
        
        # Multiple candidates - use EXIF date to disambiguate
        return self._match_by_exif_date(candidates, asset_data)
    
    def _match_by_exif_date(
        self, 
        candidates: List[Path], 
        asset_data: Dict[str, Any]
    ) -> Tuple[Optional[str], str, str]:
        """
        Match file from multiple candidates using EXIF date comparison.
        
        Args:
            candidates: List of candidate file paths
            asset_data: Immich asset data
            
        Returns:
            Tuple of (matched_path, match_confidence, match_method)
        """
        # Get Immich date
        immich_date_str = asset_data.get("dateTimeOriginal")
        if not immich_date_str:
            # Try exifInfo
            exif_info = asset_data.get("exifInfo", {})
            immich_date_str = exif_info.get("dateTimeOriginal")
        
        if not immich_date_str:
            # Can't disambiguate without date
            return None, "none", f"ambiguous_{len(candidates)}_files"
        
        immich_date = self.exif_reader.parse_exif_datetime(immich_date_str)
        if not immich_date:
            return None, "none", f"ambiguous_{len(candidates)}_files"
        
        # Check each candidate
        best_match = None
        best_delta = None
        
        for candidate in candidates:
            exif_data = self.exif_reader.read_exif(str(candidate))
            file_date_str = exif_data.get("DateTimeOriginal")
            
            if not file_date_str:
                continue
            
            file_date = self.exif_reader.parse_exif_datetime(file_date_str)
            if not file_date:
                continue
            
            # Calculate time difference
            delta = abs((immich_date - file_date).total_seconds())
            
            # Exact match (within 1 second)
            if delta <= 1:
                return str(candidate), "exact", "exif_date_exact"
            
            # Track best match
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best_match = candidate
        
        # If we have a match within reasonable tolerance (1 hour)
        if best_match and best_delta is not None and best_delta <= 3600:
            return str(best_match), "fuzzy", f"exif_date_fuzzy_{int(best_delta)}s"
        
        # No good match found
        return None, "none", f"ambiguous_{len(candidates)}_files"
