#!/usr/bin/env python3
"""
================================================================================
=== [organize] - Organize VideoProc Vlogger project files and media
================================================================================

This script organizes VideoProc Vlogger project files (.vpd) by consolidating
all used media files into a clean directory structure with sequential naming
based on timeline position.

Key features:
- Copies only files actually used in the timeline
- Organizes into {target}/images, {target}/video, {target}/audio
- Renames files with sequence prefix based on timeline position
- Creates new self-contained VPD file with updated paths
- Resulting project is fully portable and organized

Usage:
    organize.py project.dvp /path/to/target
    organize.py project.dvp /path/to/target --media-root /Users/user/target
    organize.py project.dvp /target --dry-run --verbose
"""

import sys
import os
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict
from datetime import datetime

# Add COMMON to path for shared utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'COMMON', 'src'))

# Import COMMON framework modules
try:
    from common.logging import ScriptLogging
    from common.argument_parser import (
        ScriptArgumentParser,
        create_standard_arguments,
        merge_arguments
    )
except ImportError:
    ScriptLogging = None
    print("Warning: COMMON modules not available")

# Script metadata
SCRIPT_NAME = 'organize'
SCRIPT_INFO = {
    'name': SCRIPT_NAME,
    'description': 'Organize VideoProc Vlogger project files and media into clean structure',
    'examples': [
        'project.dvp /path/to/target',
        'project.dvp /path/to/target --media-root /Users/user/target',
        'project.dvp /target --dry-run --verbose',
        'project.dvp /target --remove-backup'
    ]
}

# Script-specific arguments
SCRIPT_ARGUMENTS = {
    'source_dvp': {
        'positional': True,
        'flag': '--source',
        'help': 'Source VideoProc Vlogger project folder (.dvp) to organize'
    },
    'target_dir': {
        'positional': True,
        'flag': '--target',
        'help': 'Target root directory for organized project'
    },
    'media_root': {
        'flag': '--media-root',
        'help': 'Root path to use in VPD file for media references (defaults to target directory for portability)'
    },
    'remove_backup': {
        'flag': '--remove-backup',
        'action': 'store_true',
        'help': 'Remove backup file after successful organization (backup is created by default)'
    }
}

# Merge with standard arguments (verbose, quiet, dry_run)
ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


class TimelineBlock:
    """Represents a media block in the timeline."""
    
    def __init__(self, resid: str, tstart: int, block_type: str, track_name: str, block_data: dict):
        self.resid = resid
        self.tstart = tstart  # Timeline position in milliseconds
        self.block_type = block_type  # ImageFileBlock, VideoFileBlock, AudioFileBlock
        self.track_name = track_name
        self.block_data = block_data
        
    def __repr__(self):
        return f"TimelineBlock(resid={self.resid[:8]}, tstart={self.tstart}, type={self.block_type})"


class MediaResource:
    """Represents a media resource from scapegoat."""
    
    def __init__(self, uuid: str, path: str, title: str, resource_type: str, duration: float):
        self.uuid = uuid
        self.path = path
        self.title = title
        self.resource_type = resource_type  # image, video, audio
        self.duration = duration
        self.timeline_uses: List[TimelineBlock] = []
        self.new_path: Optional[str] = None
        self.sequence_number: Optional[int] = None
        
    @property
    def earliest_tstart(self) -> int:
        """Get earliest timeline position where this resource is used."""
        if not self.timeline_uses:
            return float('inf')
        return min(block.tstart for block in self.timeline_uses)
    
    @property
    def is_used(self) -> bool:
        """Check if resource is actually used in timeline."""
        return len(self.timeline_uses) > 0
    
    def __repr__(self):
        return f"MediaResource(uuid={self.uuid[:8]}, type={self.resource_type}, uses={len(self.timeline_uses)})"


class VPDOrganizer:
    """Organizes VideoProc Vlogger project files."""
    
    @staticmethod
    def normalize_uuid(uuid_str: str) -> str:
        """
        Normalize UUID to consistent format (uppercase, no hyphens).
        Handles both formats: 
        - With hyphens: 09A9D66C-2A9C-452B-B1FE-5AA6EBD72927
        - Without hyphens: 8B3DF940F26B065CB67321254910507F
        """
        return uuid_str.replace('-', '').upper()
    
    def __init__(self, vpd_path: str, target_dir: str, media_root: str = None, dry_run: bool = False, logger=None, source_dvp: str = None):
        """
        Initialize organizer.
        
        Args:
            vpd_path: Path to input VPD file
            target_dir: Directory where organized files will be written
            media_root: Root path to use in VPD file references (if different from target_dir)
            dry_run: If True, don't actually copy files or save VPD
            logger: Logger instance
            source_dvp: Original source .dvp folder path (for naming)
        """
        self.vpd_path = Path(vpd_path)
        self.target_dir = Path(target_dir)
        self.media_root = Path(media_root) if media_root else self.target_dir.resolve()
        self.dry_run = dry_run
        self.logger = logger or logging.getLogger(__name__)
        self.source_dvp = Path(source_dvp) if source_dvp else None
        self.vpd_data = None
        self.resources: Dict[str, MediaResource] = {}
        self.timeline_blocks: List[TimelineBlock] = []
        self.dvp_folder: Optional[Path] = None  # Will be set in create_target_structure
        self.uuid_to_resid_map: Dict[str, str] = {}  # Maps timeline instance UUID to resource UUID
        
    def load_vpd(self) -> Dict:
        """Load VPD project file."""
        self.logger.info(f"Loading project: {self.vpd_path}")
        
        try:
            with open(self.vpd_path, 'r', encoding='utf-8') as f:
                self.vpd_data = json.load(f)
            
            self.logger.info("Successfully loaded VPD project file")
            return self.vpd_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in VPD file: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load VPD file: {e}")
            raise
    
    def extract_resources(self) -> Dict[str, MediaResource]:
        """Extract all media resources from VPD file."""
        self.logger.info("Extracting media resources from project...")
        resources = {}
        uuid_map = {}
        
        # Extract images from imagelist scapegoat
        if 'imagelist' in self.vpd_data and 'scapegoat' in self.vpd_data['imagelist']:
            for res in self.vpd_data['imagelist']['scapegoat']:
                resource = MediaResource(
                    uuid=res['uuid'],
                    path=res['path'],
                    title=res.get('title', 'Untitled'),
                    resource_type='image',
                    duration=res.get('duration', 0.0)
                )
                # Store with normalized UUID as key
                normalized_uuid = self.normalize_uuid(resource.uuid)
                resources[normalized_uuid] = resource
                self.logger.debug(f"  Found image: {resource.title} (uuid={normalized_uuid[:8]})")
            
            # Build mapping from timeline instance UUID to resource UUID for images
            # Links can be at top level or inside ResourceList groups
            if 'subitems' in self.vpd_data['imagelist']:
                for item in self.vpd_data['imagelist']['subitems']:
                    if item.get('type') == 'link':
                        # Top-level link: uuid=instance (timeline refs), resid=resource (scapegoat)
                        if 'uuid' in item and 'resid' in item:
                            instance_uuid = self.normalize_uuid(item['uuid'])
                            resource_uuid = self.normalize_uuid(item['resid'])
                            uuid_map[instance_uuid] = resource_uuid
                            self.logger.debug(f"  Link: {instance_uuid[:8]} -> {resource_uuid[:8]}")
                    elif item.get('type') == 'ResourceList':
                        # Group of links (folder import)
                        for link in item.get('subitems', []):
                            if link.get('type') == 'link' and 'uuid' in link and 'resid' in link:
                                instance_uuid = self.normalize_uuid(link['uuid'])
                                resource_uuid = self.normalize_uuid(link['resid'])
                                uuid_map[instance_uuid] = resource_uuid
                                self.logger.debug(f"  Link (in {item.get('title')}): {instance_uuid[:8]} -> {resource_uuid[:8]}")
        
        # Extract audio from audiolist subitems
        if 'audiolist' in self.vpd_data and 'subitems' in self.vpd_data['audiolist']:
            for res in self.vpd_data['audiolist']['subitems']:
                if 'uuid' in res and 'path' in res:
                    resource = MediaResource(
                        uuid=res['uuid'],
                        path=res['path'],
                        title=res.get('title', 'Untitled'),
                        resource_type='audio',
                        duration=res.get('duration', 0.0)
                    )
                    normalized_uuid = self.normalize_uuid(resource.uuid)
                    resources[normalized_uuid] = resource
                    # For audio, the UUID is used directly (no link indirection)
                    uuid_map[normalized_uuid] = normalized_uuid
                    self.logger.debug(f"  Found audio: {resource.title} (uuid={normalized_uuid[:8]})")
        
        # Extract video from videolist scapegoat
        if 'videolist' in self.vpd_data and 'scapegoat' in self.vpd_data['videolist']:
            for res in self.vpd_data['videolist']['scapegoat']:
                resource = MediaResource(
                    uuid=res['uuid'],
                    path=res['path'],
                    title=res.get('title', 'Untitled'),
                    resource_type='video',
                    duration=res.get('duration', 0.0)
                )
                normalized_uuid = self.normalize_uuid(resource.uuid)
                resources[normalized_uuid] = resource
                self.logger.debug(f"  Found video: {resource.title} (uuid={normalized_uuid[:8]})")
            
            # Build mapping for video links if they exist
            if 'subitems' in self.vpd_data['videolist']:
                for link in self.vpd_data['videolist']['subitems']:
                    if link.get('type') == 'link' and 'uuid' in link and 'resid' in link:
                        instance_uuid = self.normalize_uuid(link['uuid'])
                        resource_uuid = self.normalize_uuid(link['resid'])
                        uuid_map[instance_uuid] = resource_uuid
                        self.logger.debug(f"  Link: {instance_uuid[:8]} -> {resource_uuid[:8]}")
        
        self.resources = resources
        self.uuid_to_resid_map = uuid_map
        self.logger.info(f"Found {len(resources)} total resources in project")
        self.logger.info(f"Built {len(uuid_map)} UUID mappings")
        
        # Count by type
        by_type = defaultdict(int)
        for r in resources.values():
            by_type[r.resource_type] += 1
        
        for media_type, count in by_type.items():
            self.logger.info(f"  {media_type}: {count} files")
        
        return resources
    
    def extract_timeline_blocks(self) -> List[TimelineBlock]:
        """Extract all media blocks from timeline tracks."""
        self.logger.info("Analyzing timeline structure...")
        blocks = []
        
        if 'timeline' not in self.vpd_data or 'subitems' not in self.vpd_data['timeline']:
            self.logger.warning("No timeline tracks found in project")
            return blocks
        
        tracks = self.vpd_data['timeline']['subitems']
        
        for track in tracks:
            track_type = track.get('type', 'Unknown')
            track_title = track.get('title', 'Untitled')
            
            self.logger.debug(f"  Scanning track: {track_title} ({track_type})")
            
            if 'subitems' not in track:
                continue
            
            for block in track['subitems']:
                block_type = block.get('type', '')
                
                # Check if this is a media file block (includes generic MediaFileBlock for audio)
                if block_type in ['ImageFileBlock', 'VideoFileBlock', 'AudioFileBlock', 'MediaFileBlock']:
                    resid = block.get('resid')
                    tstart = block.get('tstart', 0)
                    
                    if resid:
                        timeline_block = TimelineBlock(
                            resid=resid,
                            tstart=tstart,
                            block_type=block_type,
                            track_name=track_title,
                            block_data=block
                        )
                        blocks.append(timeline_block)
                        self.logger.debug(f"    Block: {block_type} at t={tstart}ms, resid={resid[:8]}...")
        
        self.timeline_blocks = blocks
        self.logger.info(f"Found {len(blocks)} media blocks in timeline")
        
        return blocks
    
    def link_timeline_to_resources(self):
        """Link timeline blocks to their corresponding resources."""
        self.logger.info("Linking timeline blocks to resources...")
        
        linked = 0
        unlinked = 0
        
        for block in self.timeline_blocks:
            # Normalize the resid from the timeline block (this is actually an instance UUID)
            normalized_instance_uuid = self.normalize_uuid(block.resid)
            
            # Look up the actual resource UUID through the mapping
            if normalized_instance_uuid in self.uuid_to_resid_map:
                resource_uuid = self.uuid_to_resid_map[normalized_instance_uuid]
                
                if resource_uuid in self.resources:
                    self.resources[resource_uuid].timeline_uses.append(block)
                    linked += 1
                else:
                    self.logger.warning(f"Timeline block {block.resid[:8]} maps to unknown resource: {resource_uuid[:8]}")
                    unlinked += 1
            else:
                # Try direct lookup (for cases where resid directly references resource)
                if normalized_instance_uuid in self.resources:
                    self.resources[normalized_instance_uuid].timeline_uses.append(block)
                    linked += 1
                else:
                    self.logger.warning(f"Timeline block references unknown instance: {block.resid[:8]}")
                    unlinked += 1
        
        self.logger.info(f"Linked {linked} blocks to resources")
        if unlinked > 0:
            self.logger.warning(f"{unlinked} blocks reference missing resources")
        
        # Report usage statistics
        used = sum(1 for r in self.resources.values() if r.is_used)
        unused = len(self.resources) - used
        
        self.logger.info(f"Resource usage: {used} used, {unused} unused")
    
    def assign_sequence_numbers(self):
        """Assign sequence numbers based on timeline position."""
        self.logger.info("Assigning sequence numbers based on timeline position...")
        
        # Get only used resources and sort by earliest timeline position
        used_resources = [r for r in self.resources.values() if r.is_used]
        used_resources.sort(key=lambda r: r.earliest_tstart)
        
        # Assign sequence numbers
        for seq, resource in enumerate(used_resources, start=1):
            resource.sequence_number = seq
            self.logger.debug(f"  {seq:04d}: {resource.title} (t={resource.earliest_tstart}ms)")
        
        self.logger.info(f"Assigned sequence numbers to {len(used_resources)} resources")
    
    def create_target_structure(self):
        """Create target directory structure including .dvp folder."""
        # Create the .dvp folder structure
        # Create two separate structures:
        # 1. {target_root}/{project_name}.dvp/ - contains only the .vpd file
        # 2. {target_root}/{project_name}_media/ - contains organized images/video/audio
        
        # Use source .dvp folder name if available, otherwise use .vpd filename
        if self.source_dvp and self.source_dvp.suffix.lower() == '.dvp':
            project_name = self.source_dvp.stem  # e.g., "AM" from "AM.dvp"
        else:
            project_name = self.vpd_path.stem  # e.g., "A&M" from "A&M.vpd"
        
        # Store project name for use in path generation
        self.project_name = project_name
        
        self.dvp_folder = self.target_dir / f"{project_name}.dvp"
        self.media_folder = self.target_dir / f"{project_name}_media"
        
        self.logger.info(f"Creating target directory structure:")
        self.logger.info(f"  Project: {self.dvp_folder}")
        self.logger.info(f"  Media: {self.media_folder}")
        
        if self.dry_run:
            self.logger.info("[DRY RUN] Would create directories:")
            self.logger.info(f"  {self.dvp_folder}/")
            self.logger.info(f"  {self.media_folder}/images")
            self.logger.info(f"  {self.media_folder}/video")
            self.logger.info(f"  {self.media_folder}/audio")
            return
        
        try:
            self.dvp_folder.mkdir(parents=True, exist_ok=True)
            self.media_folder.mkdir(parents=True, exist_ok=True)
            (self.media_folder / 'images').mkdir(exist_ok=True)
            (self.media_folder / 'video').mkdir(exist_ok=True)
            (self.media_folder / 'audio').mkdir(exist_ok=True)
            
            self.logger.info("✓ Directory structure created")
            
        except Exception as e:
            self.logger.error(f"Failed to create directory structure: {e}")
            raise
    
    def copy_and_rename_files(self) -> Tuple[int, int]:
        """
        Copy used media files to target with sequential naming.
        
        Returns:
            Tuple of (copied_count, error_count)
        """
        self.logger.info("Copying and renaming media files...")
        
        copied = 0
        errors = 0
        
        for resource in self.resources.values():
            if not resource.is_used:
                self.logger.debug(f"  Skipping unused: {resource.title}")
                continue
            
            if not resource.sequence_number:
                self.logger.error(f"  Resource has no sequence number: {resource.title}")
                errors += 1
                continue
            
            # Determine target subdirectory
            if resource.resource_type == 'image':
                subdir = 'images'
            elif resource.resource_type == 'video':
                subdir = 'video'
            elif resource.resource_type == 'audio':
                subdir = 'audio'
            else:
                self.logger.error(f"  Unknown resource type: {resource.resource_type}")
                errors += 1
                continue
            
            # Create new filename with sequence prefix and track name
            original_filename = Path(resource.path).name
            
            # Remove existing sequence pattern if present (e.g., "0001_Video_Track_")
            # Pattern: 4 digits, underscore, track name, underscore
            import re
            cleaned_filename = re.sub(r'^\d{4}_[^_]+_Track_', '', original_filename)
            
            # Use the track name from the first (earliest) timeline use
            track_name = resource.timeline_uses[0].track_name if resource.timeline_uses else "unknown"
            # Clean track name for use in filename (remove spaces, special chars)
            clean_track = track_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            new_filename = f"{resource.sequence_number:04d}_{clean_track}_{cleaned_filename}"
            
            # Physical location where file will be copied (using target_dir)
            new_path = self.media_folder / subdir / new_filename
            
            # Path to store in VPD file (using media_root for cross-platform compatibility)
            vpd_path = self.media_root / f"{self.project_name}_media" / subdir / new_filename
            resource.new_path = str(vpd_path)
            
            # Check if source file exists
            if not os.path.exists(resource.path):
                self.logger.error(f"  Source file not found: {resource.path}")
                errors += 1
                continue
            
            # Copy file
            if self.dry_run:
                self.logger.info(f"  [DRY RUN] Would copy: {original_filename}")
                self.logger.info(f"            → {subdir}/{new_filename}")
                copied += 1
            else:
                try:
                    shutil.copy2(resource.path, new_path)
                    self.logger.info(f"  ✓ Copied: {original_filename} → {subdir}/{new_filename}")
                    copied += 1
                except Exception as e:
                    self.logger.error(f"  ✗ Failed to copy {original_filename}: {e}")
                    errors += 1
        
        self.logger.info(f"File operations complete: {copied} copied, {errors} errors")
        return copied, errors
    
    def copy_unused_resources(self) -> Tuple[int, int]:
        """
        Copy unused media files to target/unused folder for reference.
        
        Returns:
            Tuple of (copied_count, error_count)
        """
        self.logger.info("Copying unused resources to 'unused' folder...")
        
        copied = 0
        errors = 0
        
        # Create unused subdirectories
        unused_base = self.media_folder / 'unused'
        
        for resource in self.resources.values():
            if resource.is_used:
                continue
            
            # Determine target subdirectory
            if resource.resource_type == 'image':
                subdir = 'images'
            elif resource.resource_type == 'video':
                subdir = 'video'
            elif resource.resource_type == 'audio':
                subdir = 'audio'
            else:
                self.logger.debug(f"  Skipping unknown type: {resource.title}")
                continue
            
            # Keep original filename for unused resources
            original_filename = Path(resource.path).name
            unused_path = unused_base / subdir / original_filename
            
            # Create directory if needed
            if not self.dry_run:
                unused_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if source file exists
            if not os.path.exists(resource.path):
                self.logger.debug(f"  Source not found (skipping): {original_filename}")
                continue
            
            # Copy file
            if self.dry_run:
                self.logger.info(f"  [DRY RUN] Would copy unused: {original_filename}")
                copied += 1
            else:
                try:
                    shutil.copy2(resource.path, unused_path)
                    self.logger.debug(f"  ✓ Copied unused: {original_filename}")
                    copied += 1
                except Exception as e:
                    self.logger.warning(f"  ✗ Failed to copy unused {original_filename}: {e}")
                    errors += 1
        
        if copied > 0:
            self.logger.info(f"Copied {copied} unused resources to 'unused' folder")
        return copied, errors
    
    def update_vpd_paths(self):
        """Update all file paths in VPD data to point to new organized locations."""
        self.logger.info("Updating file paths in VPD data...")
        
        updated = 0
        
        # Get set of used resource UUIDs for filtering links
        used_resource_uuids = {
            self.normalize_uuid(uuid) 
            for uuid, res in self.resources.items() 
            if res.is_used
        }
        
        # Update image paths in imagelist scapegoat
        if 'imagelist' in self.vpd_data and 'scapegoat' in self.vpd_data['imagelist']:
            # Keep ALL resources (needed for timeline blocks), but update paths
            for res in self.vpd_data['imagelist']['scapegoat']:
                uuid = res['uuid']
                if uuid in self.resources and self.resources[uuid].is_used:
                    # Used resource: update to organized path
                    resource = self.resources[uuid]
                    res['path'] = resource.new_path
                    res['title'] = Path(resource.new_path).stem
                    updated += 1
                    self.logger.debug(f"  Updated image: {uuid[:8]} → {resource.new_path}")
                elif uuid in self.resources:
                    # Unused resource: update to unused folder path
                    resource = self.resources[uuid]
                    original_filename = Path(resource.path).name
                    unused_path = self.media_root / f"{self.project_name}_media" / 'unused' / 'images' / original_filename
                    res['path'] = str(unused_path)
                    res['title'] = f"[unused] {Path(resource.path).stem}"
                    self.logger.debug(f"  Moved to unused: {uuid[:8]}")
            
            # Keep ALL link objects - timeline blocks may reference them even if resources are missing
            # VideoProc Vlogger handles missing resources gracefully but needs the link structure intact
        
        # Update audio paths in audiolist subitems
        if 'audiolist' in self.vpd_data and 'subitems' in self.vpd_data['audiolist']:
            # Keep ALL resources, update paths for both used and unused
            for res in self.vpd_data['audiolist']['subitems']:
                uuid = res.get('uuid')
                if uuid and uuid in self.resources and self.resources[uuid].is_used:
                    # Used resource
                    resource = self.resources[uuid]
                    res['path'] = resource.new_path
                    res['title'] = Path(resource.new_path).stem
                    updated += 1
                    self.logger.debug(f"  Updated audio: {uuid[:8]} → {resource.new_path}")
                elif uuid and uuid in self.resources:
                    # Unused resource: update to unused folder
                    resource = self.resources[uuid]
                    original_filename = Path(resource.path).name
                    unused_path = self.media_root / f"{self.project_name}_media" / 'unused' / 'audio' / original_filename
                    res['path'] = str(unused_path)
                    res['title'] = f"[unused] {Path(resource.path).stem}"
                    self.logger.debug(f"  Moved to unused: {uuid[:8]}")
        
        # Update video paths in videolist scapegoat
        if 'videolist' in self.vpd_data and 'scapegoat' in self.vpd_data['videolist']:
            # Keep ALL resources, update paths for both used and unused
            for res in self.vpd_data['videolist']['scapegoat']:
                uuid = res['uuid']
                if uuid in self.resources and self.resources[uuid].is_used:
                    # Used resource
                    resource = self.resources[uuid]
                    res['path'] = resource.new_path
                    res['title'] = Path(resource.new_path).stem
                    updated += 1
                    self.logger.debug(f"  Updated video: {uuid[:8]} → {resource.new_path}")
                elif uuid in self.resources:
                    # Unused resource: update to unused folder
                    resource = self.resources[uuid]
                    original_filename = Path(resource.path).name
                    unused_path = self.media_root / f"{self.project_name}_media" / 'unused' / 'video' / original_filename
                    res['path'] = str(unused_path)
                    res['title'] = f"[unused] {Path(resource.path).stem}"
                    self.logger.debug(f"  Moved to unused: {uuid[:8]}")
            
            # Keep ALL link objects - VideoProc needs complete structure
        
        # Update project file path
        if 'projinfo' in self.vpd_data:
            # Path should be to the .vpd file inside the .dvp folder
            new_vpd_path = self.dvp_folder / self.vpd_path.name
            self.vpd_data['projinfo']['projectfile'] = str(new_vpd_path)
            
            # Update save time to now
            now = datetime.now()
            self.vpd_data['projinfo']['savetime'] = {
                'year': now.year,
                'month': now.month,
                'day': now.day,
                'hour': now.hour,
                'minute': now.minute,
                'second': now.second
            }
        
        self.logger.info(f"Updated {updated} resource paths in VPD data")
    
    def remove_broken_timeline_blocks(self):
        """Remove timeline blocks that reference missing resources."""
        self.logger.info("Cleaning timeline blocks...")
        
        removed = 0
        
        # Get set of valid resource UUIDs (both instance UUIDs and resource UUIDs)
        valid_uuids = set()
        for res_uuid in self.resources.keys():
            if self.resources[res_uuid].is_used:
                valid_uuids.add(self.normalize_uuid(res_uuid))
        
        # Add all instance UUIDs that map to valid resources
        for inst_uuid, res_uuid in self.uuid_to_resid_map.items():
            if res_uuid in valid_uuids:
                valid_uuids.add(inst_uuid)
        
        # Clean timeline tracks
        if 'timeline' in self.vpd_data and 'subitems' in self.vpd_data['timeline']:
            for track in self.vpd_data['timeline']['subitems']:
                if 'subitems' in track:
                    original_count = len(track['subitems'])
                    # Keep only blocks that reference valid resources
                    track['subitems'] = [
                        block for block in track['subitems']
                        if 'resid' not in block or self.normalize_uuid(block['resid']) in valid_uuids
                    ]
                    removed_from_track = original_count - len(track['subitems'])
                    if removed_from_track > 0:
                        self.logger.info(f"  Removed {removed_from_track} broken blocks from {track.get('title', 'track')}")
                        removed += removed_from_track
        
        if removed > 0:
            self.logger.info(f"Removed {removed} broken timeline blocks")
        else:
            self.logger.info("No broken timeline blocks found")
    
    def save_vpd(self, output_path: Path, backup_folder: Path = None):
        """
        Save updated VPD file to target directory.
        
        Args:
            output_path: Path to save new VPD file
            backup_folder: Path to backup .dvp folder (if provided)
        
        Returns:
            Path to backup folder if created, None otherwise
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would save organized VPD to: {output_path}")
            return None
        
        backup_path = None
        
        # Create backup of entire .dvp folder if requested
        if backup_folder:
            self.logger.info(f"Creating backup: {backup_folder}")
            
            try:
                # Get the source .dvp folder
                source_dvp = self.source_dvp if self.source_dvp and self.source_dvp.suffix.lower() == '.dvp' else self.vpd_path.parent
                
                # Copy entire .dvp folder to backup location
                shutil.copytree(source_dvp, backup_folder, dirs_exist_ok=False)
                self.logger.info("✓ Backup created successfully")
                backup_path = backup_folder
            except Exception as e:
                self.logger.error(f"Failed to create backup: {e}")
                raise
        
        # Save updated VPD
        self.logger.info(f"Saving organized project to: {output_path}")
        
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save the VPD file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.vpd_data, f, indent=4)
            
            self.logger.info("✓ Project saved successfully")
            
            # Copy other files from source .dvp folder (like .png thumbnail, .userdata, etc.)
            source_dvp = self.source_dvp if self.source_dvp and self.source_dvp.suffix.lower() == '.dvp' else self.vpd_path.parent
            target_dvp = output_path.parent
            
            copied_files = []
            for item in source_dvp.iterdir():
                # Skip .vpd files (we already saved the updated one)
                # Skip .backup files
                if item.suffix.lower() == '.vpd' or '.backup' in item.name:
                    continue
                
                # Copy other files (like .png, .userdata, etc.)
                if item.is_file():
                    target_file = target_dvp / item.name
                    try:
                        shutil.copy2(item, target_file)
                        copied_files.append(item.name)
                        self.logger.debug(f"  ✓ Copied: {item.name}")
                    except Exception as e:
                        self.logger.warning(f"  ✗ Failed to copy {item.name}: {e}")
            
            if copied_files:
                self.logger.info(f"✓ Copied {len(copied_files)} additional files from source .dvp folder")
            
        except Exception as e:
            self.logger.error(f"Failed to save VPD file: {e}")
            raise
        
        return backup_path


def main():
    """Main entry point with consistent argument parsing and structure."""
    
    # Create argument parser
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)

    # Print standardized header
    parser.print_header()
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate and resolve required arguments
    resolved_args = parser.validate_required_args(args, {
        'source_dvp': ['source_dvp', 'source'],
        'target_dir': ['target_dir', 'target']
    })
    
    # Validate and process source DVP folder
    source_path = Path(resolved_args['source_dvp'])
    if not source_path.exists():
        print(f"❌ Error: Source not found: {source_path}")
        sys.exit(1)
    
    # If it's a .dvp folder, find the .vpd file inside
    if source_path.is_dir() and source_path.suffix.lower() == '.dvp':
        # Find .vpd file in the folder
        vpd_files = list(source_path.glob('*.vpd'))
        if not vpd_files:
            print(f"❌ Error: No .vpd file found in {source_path}")
            sys.exit(1)
        if len(vpd_files) > 1:
            print(f"⚠️  Warning: Multiple .vpd files found, using: {vpd_files[0].name}")
        vpd_file = vpd_files[0]
    elif source_path.suffix.lower() == '.vpd':
        # Direct .vpd file provided
        vpd_file = source_path
    else:
        print(f"❌ Error: Source must be a .dvp folder or .vpd file: {source_path}")
        sys.exit(1)
    
    # Setup target directory
    target_dir = Path(resolved_args['target_dir'])
    
    # Setup media_root: defaults to target_dir (use original path, not resolved)
    media_root = resolved_args.get('media_root')
    if not media_root:
        media_root = resolved_args['target_dir']  # Use original string to preserve /Users/rex path
    
    # Setup logging with consistent pattern
    logger = parser.setup_logging(resolved_args, SCRIPT_NAME)

    # Display configuration
    config_map = {
        'source_dvp': 'Source DVP project',
        'target_dir': 'Target root directory',
        'media_root': 'Media root for VPD references',
        'dry_run': 'Dry run mode',
        'remove_backup': 'Remove backup after success'
    }
    
    display_config = dict(resolved_args)
    display_config['vpd_file'] = str(vpd_file)
    display_config['media_root'] = media_root
    display_config['backup_behavior'] = 'Create and remove' if resolved_args.get('remove_backup') else 'Create and keep'
    
    parser.display_configuration(display_config, config_map)
    
    try:
        # Initialize organizer
        organizer = VPDOrganizer(
            vpd_path=str(vpd_file),
            target_dir=str(target_dir),
            media_root=media_root,
            dry_run=resolved_args.get('dry_run', False),
            logger=logger,
            source_dvp=str(source_path)
        )
        
        # Main organization workflow
        logger.info("================================================================================")
        logger.info(" STARTING VPD ORGANIZATION PROCESS")
        logger.info("================================================================================")
        
        # Step 1: Load project
        organizer.load_vpd()
        
        # Step 2: Extract resources
        resources = organizer.extract_resources()
        
        if not resources:
            logger.warning("No media resources found in project file")
            if not resolved_args.get('quiet'):
                print("⚠️  No media resources found in project")
            return
        
        # Step 3: Analyze timeline
        organizer.extract_timeline_blocks()
        
        # Step 4: Link timeline to resources
        organizer.link_timeline_to_resources()
        
        # Step 5: Assign sequence numbers
        organizer.assign_sequence_numbers()
        
        # Step 6: Create target structure
        organizer.create_target_structure()
        
        # Step 7: Copy and rename files
        logger.info("================================================================================")
        logger.info(" COPYING AND ORGANIZING FILES")
        logger.info("================================================================================")
        
        copied, errors = organizer.copy_and_rename_files()
        
        if errors > 0:
            logger.error(f"Encountered {errors} errors during file operations")
        
        # Step 7.5: Copy unused resources to 'unused' folder
        unused_copied, unused_errors = organizer.copy_unused_resources()
        
        # Step 8: Update VPD paths
        logger.info("================================================================================")
        logger.info(" UPDATING PROJECT FILE")
        logger.info("================================================================================")
        
        organizer.update_vpd_paths()
        # Don't remove broken timeline blocks - VideoProc Vlogger handles them gracefully
        # organizer.remove_broken_timeline_blocks()
        
        # Step 9: Save new VPD file inside the .dvp folder
        output_vpd = organizer.dvp_folder / vpd_file.name
        
        # Create backup folder path with timestamp if needed
        backup_folder_path = None
        if not resolved_args.get('remove_backup'):  # Create backup by default
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            source_dvp = source_path if source_path.suffix.lower() == '.dvp' else source_path.parent
            backup_name = f"{source_dvp.stem}.backup.{timestamp}.dvp"
            backup_folder_path = source_dvp.parent / backup_name
        
        backup_path = organizer.save_vpd(output_vpd, backup_folder=backup_folder_path)
        
        # Summary
        logger.info("================================================================================")
        logger.info(" ORGANIZATION SUMMARY")
        logger.info("================================================================================")
        
        used_count = sum(1 for r in resources.values() if r.is_used)
        unused_count = len(resources) - used_count
        
        logger.info(f"Total resources found: {len(resources)}")
        logger.info(f"Resources used in timeline: {used_count}")
        logger.info(f"Resources unused (skipped): {unused_count}")
        logger.info(f"Files copied: {copied}")
        logger.info(f"Errors encountered: {errors}")
        
        if not resolved_args.get('quiet'):
            if resolved_args.get('dry_run'):
                print(f"🔍 [DRY RUN] Would organize {used_count} files into {target_dir}")
                print(f"   Skipping {unused_count} unused resources")
            else:
                print(f"✅ Organized {copied} files successfully")
                if unused_count > 0:
                    print(f"   Skipped {unused_count} unused resources")
                print(f"📁 Organized project: {output_vpd}")
                if backup_path:
                    print(f"📦 Backup saved: {backup_path}")
                if errors > 0:
                    print(f"⚠️  {errors} errors encountered - check log for details")
        
        logger.info("================================================================================")
        logger.info(" ORGANIZATION COMPLETE")
        logger.info("================================================================================")
        
        if errors > 0:
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Error during organization: {e}")
        if resolved_args.get('verbose'):
            import traceback
            logger.error(traceback.format_exc())
        
        if not resolved_args.get('quiet'):
            print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
