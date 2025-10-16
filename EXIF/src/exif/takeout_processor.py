"""
Google Takeout Processor - Extract and enhance media files from Google Takeout archives

This module provides functionality to extract images and videos from Google Takeout
ZIP files and update their metadata using the associated sidecar JSON files.
"""

import zipfile
import json
import shutil
import os
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import sys

# Import FileManager for file extension management
try:
    # Try to import from COMMON framework
    common_src_path = Path(__file__).parent.parent.parent / 'COMMON' / 'src'
    sys.path.insert(0, str(common_src_path))
    from common.file_manager import FileManager
except ImportError:
    FileManager = None


class TakeoutProcessor:
    """Processes Google Takeout ZIP files or existing folders to extract and enhance images/videos."""
    
    def __init__(self, zip_path: Optional[str] = None, target_dir: str = None,
                 create_subdir: bool = False, debug: bool = False,
                 folder_path: Optional[str] = None):
        """
        Initialize the TakeoutProcessor.
        
        Args:
            zip_path: Path to the Google Takeout ZIP file (for ZIP mode)
            target_dir: Path to the target extraction/processing directory
            create_subdir: If True, create a subdirectory based on ZIP filename to avoid conflicts
            debug: Enable debug logging
            folder_path: Path to existing folder containing Takeout files (for folder mode)
        """
        # Handle backward compatibility: if zip_path is provided as first positional arg, use ZIP mode
        if zip_path and folder_path:
            raise ValueError("Cannot specify both zip_path and folder_path")
        if not zip_path and not folder_path:
            raise ValueError("Must specify either zip_path or folder_path")
            
        self.mode = 'zip' if zip_path else 'folder'
        
        if self.mode == 'zip':
            self.source_zip = Path(zip_path)
            self.base_target_dir = Path(target_dir)
            self.create_subdir = create_subdir
            
            # Create subdirectory based on ZIP filename to avoid conflicts between multiple ZIPs
            if create_subdir:
                zip_name = self.source_zip.stem  # Remove .zip extension
                self.target_dir = self.base_target_dir / zip_name
            else:
                self.target_dir = self.base_target_dir
        else:
            # Folder mode
            self.source_folder = Path(folder_path)
            self.target_dir = Path(target_dir) if target_dir else self.source_folder
            self.create_subdir = False  # Not applicable for folder mode
            
        # Initialize logger (will be set by caller)
        self.logger = None
        
        self.stats = {
            'files_extracted': 0,
            'files_overwritten': 0,
            'images_processed': 0,
            'videos_processed': 0,
            'sidecar_files_found': 0,
            'metadata_updates': 0,
            'errors': 0
        }
        
        # Get supported file extensions
        if FileManager:
            self.image_extensions = FileManager.get_image_extensions()
            self.video_extensions = FileManager.get_video_extensions()
        else:
            # Fallback extensions
            self.image_extensions = {
                '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
                '.heic', '.raw', '.cr2', '.nef', '.arw'
            }
            self.video_extensions = {
                '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm',
                '.m4v', '.3gp', '.mpg', '.mpeg', '.mts', '.m2ts'
            }
    
    def is_media_file(self, file_path: Path) -> bool:
        """Check if file is a supported media file (image or video)."""
        ext = file_path.suffix.lower()
        return ext in self.image_extensions or ext in self.video_extensions
    
    def is_sidecar_file(self, file_path: Path) -> bool:
        """Check if file is a sidecar metadata file."""
        # Google Takeout uses various .supplemental-*.json extensions (due to filename truncation)
        filename_lower = file_path.name.lower()
        
        # Check for all supplemental variations
        supplemental_patterns = [
            '.supplemental-metadata.json',
            '.supplemental-metadata(1).json',
            '.supplemental-metadata(2).json',
            '.supplemental-meta.json',
            '.supplemental-metad.json',
            '.supplemental-metadat.json',
            '.supplemental-metada.json',
            '.supplemental-met.json',
            '.supplemental-me.json',
            '.supplemental-m.json'
        ]
        
        for pattern in supplemental_patterns:
            if filename_lower.endswith(pattern):
                return True
                
        # Also accept generic .json files
        return filename_lower.endswith('.json')
    
    def find_sidecar_for_media(self, media_file: Path, extracted_files: Dict[str, Path]) -> Optional[Path]:
        """
        Find the corresponding sidecar file for a media file.
        
        Args:
            media_file: Path to the media file
            extracted_files: Dictionary of extracted file paths (keys are relative to ZIP)
            
        Returns:
            Path to sidecar file if found, None otherwise
        """
        # Convert media file path back to relative path (as stored in extracted_files keys)
        try:
            media_relative = media_file.relative_to(self.target_dir)
        except ValueError:
            self.logger.debug(f"Could not get relative path for {media_file}")
            return None
        
        # Google Takeout uses .supplemental-metadata.json extension
        potential_sidecar = f"{media_relative}.supplemental-metadata.json"
        
        # Look for the sidecar file using the relative path
        if potential_sidecar in extracted_files:
            return extracted_files[potential_sidecar]
        
        # Alternative naming patterns for Google Takeout
        alternatives = [
            f"{media_relative.stem}.supplemental-metadata.json",  # Without original extension
            f"{media_relative}.json",                             # Legacy .json naming
            f"{media_relative.stem}.json"                         # Legacy without extension
        ]
        
        for alt_name in alternatives:
            if alt_name in extracted_files:
                return extracted_files[alt_name]
        
        return None
    
    def extract_zip_contents(self) -> Dict[str, Path]:
        """
        Extract all contents from the ZIP file.
        
        Returns:
            Dictionary mapping original paths to extracted file paths
        """
        self.logger.info(f"Extracting ZIP file: {self.source_zip}")
        self.logger.info(f"Target directory: {self.target_dir}")
        
        if not self.source_zip.exists():
            raise FileNotFoundError(f"Source ZIP file not found: {self.source_zip}")
        
        # Create target directory
        self.target_dir.mkdir(parents=True, exist_ok=True)
        
        extracted_files = {}
        
        with zipfile.ZipFile(self.source_zip, 'r') as zip_ref:
            file_list = zip_ref.namelist()
            self.logger.info(f"ZIP contains {len(file_list)} files")
            
            for file_path in file_list:
                # Skip directories
                if file_path.endswith('/'):
                    continue
                
                try:
                    # Extract file preserving directory structure
                    extracted_path = self.target_dir / file_path
                    extracted_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Warn if file already exists (conflict detection)
                    if extracted_path.exists():
                        self.logger.warning(f"File already exists, overwriting: {extracted_path}")
                        self.stats['files_overwritten'] += 1
                    
                    with zip_ref.open(file_path) as source, open(extracted_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
                    
                    extracted_files[file_path] = extracted_path
                    self.stats['files_extracted'] += 1
                    
                    if self.stats['files_extracted'] % 100 == 0:
                        self.logger.debug(f"Extracted {self.stats['files_extracted']} files...")
                
                except Exception as e:
                    self.logger.error(f"Error extracting {file_path}: {e}")
                    self.stats['errors'] += 1
        
        self.logger.info(f"Successfully extracted {self.stats['files_extracted']} files")
        return extracted_files
    
    def parse_sidecar_metadata(self, sidecar_path: Path) -> Optional[Dict]:
        """
        Parse metadata from Google Takeout sidecar JSON file.
        
        Args:
            sidecar_path: Path to the sidecar JSON file
            
        Returns:
            Dictionary of metadata if successful, None if failed
        """
        try:
            with open(sidecar_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            self.logger.debug(f"Parsed sidecar metadata from {sidecar_path.name}")
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error parsing sidecar file {sidecar_path}: {e}")
            self.stats['errors'] += 1
            return None
    
    def update_media_metadata(self, media_file: Path, sidecar_metadata: Dict) -> bool:
        """
        Update media file metadata using sidecar information.
        
        Args:
            media_file: Path to the media file
            sidecar_metadata: Metadata from sidecar file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract relevant metadata from Google Takeout sidecar
            creation_time = sidecar_metadata.get('creationTime', {}).get('timestamp')
            photo_taken_time = sidecar_metadata.get('photoTakenTime', {}).get('timestamp')
            title = sidecar_metadata.get('title', '')
            description = sidecar_metadata.get('description', '')
            
            # Use the most specific timestamp available
            timestamp = photo_taken_time or creation_time
            
            if timestamp:
                # Convert timestamp to datetime
                try:
                    # Google timestamps are in seconds since epoch
                    dt = datetime.fromtimestamp(int(timestamp))
                    
                    # Update file modification time to match photo taken time
                    os.utime(media_file, (dt.timestamp(), dt.timestamp()))
                    
                    self.logger.debug(f"Updated timestamp for {media_file.name} to {dt}")
                    
                except (ValueError, OSError) as e:
                    self.logger.warning(f"Could not update timestamp for {media_file.name}: {e}")
            
            # Log other metadata for reference
            if title and title != media_file.name:
                self.logger.debug(f"Original title for {media_file.name}: {title}")
            
            if description:
                self.logger.debug(f"Description for {media_file.name}: {description[:100]}...")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating metadata for {media_file}: {e}")
            self.stats['errors'] += 1
            return False
    
    def process_takeout(self) -> None:
        """Main processing method to extract and enhance media files."""
        if self.mode == 'zip':
            self._process_zip_mode()
        else:
            self._process_folder_mode()
    
    def _process_zip_mode(self) -> None:
        """Process ZIP file mode (original functionality)."""
        self.logger.info("Starting Google Takeout ZIP processing")
        self.logger.info(f"Source: {self.source_zip}")
        self.logger.info(f"Target: {self.target_dir}")
        
        # Extract ZIP contents
        extracted_files = self.extract_zip_contents()
        
        # Process extracted files
        self.logger.info("Processing extracted files for metadata enhancement...")
        
        media_files = []
        sidecar_files = {}
        
        # Categorize files
        for orig_path, extracted_path in extracted_files.items():
            if self.is_media_file(extracted_path):
                media_files.append(extracted_path)
            elif self.is_sidecar_file(extracted_path):
                sidecar_files[orig_path] = extracted_path
        
        self._process_media_files(media_files, sidecar_files)
    
    def _process_folder_mode(self) -> None:
        """Process existing folder mode (new functionality)."""
        self.logger.info("Starting Google Takeout folder processing")
        self.logger.info(f"Source folder: {self.source_folder}")
        self.logger.info(f"Target: {self.target_dir}")
        
        # Scan folder for media and sidecar files
        self.logger.info("Scanning folder for media and sidecar files...")
        
        media_files = []
        sidecar_files = {}
        
        # Walk through the source folder recursively
        for file_path in self.source_folder.rglob('*'):
            if file_path.is_file():
                if self.is_media_file(file_path):
                    media_files.append(file_path)
                elif self.is_sidecar_file(file_path):
                    # For folder mode, use the file path itself as the key
                    sidecar_files[str(file_path)] = file_path
        
        self.logger.info(f"Found {len(media_files)} media files and {len(sidecar_files)} sidecar files")
        
        # Process media files with in-place updates
        in_place_mode = (self.source_folder == self.target_dir)
        self._process_media_files(media_files, sidecar_files, in_place=in_place_mode)
    
    def _process_media_files(self, media_files, sidecar_files, in_place=False) -> None:
        """Process media files and update their metadata using sidecar files."""
        self.logger.info(f"Processing {len(media_files)} media files...")
        
        # Process media files
        for media_file in media_files:
            try:
                # Determine file type
                if media_file.suffix.lower() in self.image_extensions:
                    self.stats['images_processed'] += 1
                elif media_file.suffix.lower() in self.video_extensions:
                    self.stats['videos_processed'] += 1
                
                # Find corresponding sidecar file
                if self.mode == 'zip':
                    # For ZIP mode, we need to reverse lookup the original path
                    sidecar_file = self.find_sidecar_for_media(media_file, sidecar_files)
                else:
                    # For folder mode, look for sidecar files directly
                    sidecar_file = self._find_sidecar_for_media_folder(media_file, sidecar_files)
                
                if sidecar_file:
                    self.stats['sidecar_files_found'] += 1
                    
                    # Parse sidecar metadata
                    metadata = self.parse_sidecar_metadata(sidecar_file)
                    
                    if metadata:
                        self.logger.debug(f"Processing {media_file.name} with metadata from {sidecar_file.name}")
                        
                        # Update file metadata using existing method
                        success = self.update_media_metadata(media_file, metadata)
                        
                        if success:
                            self.stats['metadata_updates'] += 1
                        else:
                            self.stats['errors'] += 1
                    else:
                        self.logger.warning(f"Could not parse metadata from {sidecar_file}")
                        self.stats['errors'] += 1
                else:
                    self.logger.debug(f"No sidecar file found for {media_file.name}")
                    
            except Exception as e:
                self.logger.error(f"Error processing {media_file}: {e}")
                self.stats['errors'] += 1
    
    def _find_sidecar_for_media_folder(self, media_file: Path, sidecar_files: Dict) -> Optional[Path]:
        """Find sidecar file for a media file in folder mode."""
        # Generate possible sidecar filenames based on the media file
        media_stem = media_file.stem
        media_dir = media_file.parent
        
        # Try different sidecar naming patterns Google Takeout uses
        # Based on analysis, these patterns exist due to filename truncation:
        # supplemental-metadata.json, supplemental-meta.json, supplemental-metad.json, etc.
        supplemental_variations = [
            "supplemental-metadata.json",
            "supplemental-metadata(1).json",
            "supplemental-metadata(2).json",
            "supplemental-meta.json",
            "supplemental-metad.json",
            "supplemental-metadat.json",
            "supplemental-metada.json",
            "supplemental-met.json",
            "supplemental-me.json",
            "supplemental-m.json"
        ]
        
        possible_names = []
        # Google Takeout format: filename.jpg.supplemental-*.json (all variations)
        for variation in supplemental_variations:
            possible_names.append(f"{media_file.name}.{variation}")
        
        # Add other common formats
        possible_names.extend([
            f"{media_stem}.json",                             # Simple format: filename.json
            f"{media_file.name}.json",                        # Full filename + .json extension
        ])
        
        for name in possible_names:
            sidecar_path = media_dir / name
            if str(sidecar_path) in sidecar_files:
                return sidecar_files[str(sidecar_path)]
        
        return None
    
    def print_summary(self) -> None:
        """Print processing summary statistics."""
        self.logger.info("=" * 60)
        self.logger.info("GOOGLE TAKEOUT PROCESSING SUMMARY")
        self.logger.info("=" * 60)
        
        if self.mode == 'zip':
            self.logger.info(f"Source ZIP: {self.source_zip}")
            self.logger.info(f"Files extracted: {self.stats['files_extracted']:,}")
            self.logger.info(f"Files overwritten: {self.stats['files_overwritten']:,}")
        else:
            self.logger.info(f"Source folder: {self.source_folder}")
        
        self.logger.info(f"Target directory: {self.target_dir}")
        self.logger.info(f"Images processed: {self.stats['images_processed']:,}")
        self.logger.info(f"Videos processed: {self.stats['videos_processed']:,}")
        self.logger.info(f"Sidecar files found: {self.stats['sidecar_files_found']:,}")
        self.logger.info(f"Metadata updates applied: {self.stats['metadata_updates']:,}")
        
        if self.stats['errors'] > 0:
            self.logger.warning(f"Errors encountered: {self.stats['errors']}")
        
        self.logger.info("=" * 60)
