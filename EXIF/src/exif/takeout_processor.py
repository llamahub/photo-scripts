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
import logging
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
    """Processes Google Takeout ZIP files to extract and enhance images/videos."""
    
    def __init__(self, zip_path: str, target_dir: str,
                 create_subdir: bool = False,
                 debug: bool = False):
        """
        Initialize the TakeoutProcessor.
        
        Args:
            zip_path: Path to the Google Takeout ZIP file
            target_dir: Path to the target extraction directory
            create_subdir: If True, create a subdirectory based on ZIP filename to avoid conflicts
            debug: Enable debug logging
        """
        self.source_zip = Path(zip_path)
        self.base_target_dir = Path(target_dir)
        self.create_subdir = create_subdir
        
        # Create subdirectory based on ZIP filename to avoid conflicts between multiple ZIPs
        if create_subdir:
            zip_name = self.source_zip.stem  # Remove .zip extension
            self.target_dir = self.base_target_dir / zip_name
        else:
            self.target_dir = self.base_target_dir
            
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
        # Google Takeout uses .supplemental-metadata.json extension
        filename_lower = file_path.name.lower()
        return (filename_lower.endswith('.supplemental-metadata.json') or
                filename_lower.endswith('.json'))
    
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
            
            self.stats['metadata_updates'] += 1
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating metadata for {media_file}: {e}")
            self.stats['errors'] += 1
            return False
    
    def process_takeout(self) -> None:
        """Main processing method to extract and enhance media files."""
        self.logger.info("Starting Google Takeout processing")
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
        
        self.logger.info(f"Found {len(media_files)} media files and {len(sidecar_files)} sidecar files")
        
        # Process media files
        for media_file in media_files:
            try:
                # Determine file type
                if media_file.suffix.lower() in self.image_extensions:
                    self.stats['images_processed'] += 1
                elif media_file.suffix.lower() in self.video_extensions:
                    self.stats['videos_processed'] += 1
                
                # Find corresponding sidecar file
                sidecar_file = self.find_sidecar_for_media(media_file, extracted_files)
                
                if sidecar_file:
                    self.stats['sidecar_files_found'] += 1
                    
                    # Parse sidecar metadata
                    metadata = self.parse_sidecar_metadata(sidecar_file)
                    
                    if metadata:
                        # Update media file with metadata
                        self.update_media_metadata(media_file, metadata)
                else:
                    self.logger.debug(f"No sidecar file found for {media_file.name}")
                
                # Progress logging
                total_processed = self.stats['images_processed'] + self.stats['videos_processed']
                if total_processed % 50 == 0:
                    self.logger.info(f"Processed {total_processed}/{len(media_files)} media files...")
                    
            except Exception as e:
                self.logger.error(f"Error processing {media_file}: {e}")
                self.stats['errors'] += 1
    
    def print_summary(self) -> None:
        """Print processing summary statistics."""
        self.logger.info("=" * 60)
        self.logger.info("GOOGLE TAKEOUT PROCESSING SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Source ZIP: {self.source_zip}")
        self.logger.info(f"Target directory: {self.target_dir}")
        self.logger.info(f"Files extracted: {self.stats['files_extracted']:,}")
        self.logger.info(f"Files overwritten: {self.stats['files_overwritten']:,}")
        self.logger.info(f"Images processed: {self.stats['images_processed']:,}")
        self.logger.info(f"Videos processed: {self.stats['videos_processed']:,}")
        self.logger.info(f"Sidecar files found: {self.stats['sidecar_files_found']:,}")
        self.logger.info(f"Metadata updates applied: {self.stats['metadata_updates']:,}")
        
        if self.stats['errors'] > 0:
            self.logger.warning(f"Errors encountered: {self.stats['errors']}")
        
        self.logger.info("=" * 60)