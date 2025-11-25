#!/usr/bin/env python3
"""
================================================================================
=== [repair] - Repair VideoProc Vlogger .vpd project files
================================================================================

This script repairs VideoProc Vlogger project files (.vpd) by finding and fixing
missing media file references. It searches for missing files in the project
directory tree and updates the paths in the VPD file.

Key features:
- Automatically detects missing media files (images, video, audio)
- Searches project directory tree for relocated files
- Handles filename changes (e.g., HEIC → JPG conversions)
- Creates backup before modifying project files
- Supports dry-run mode to preview changes
- Comprehensive logging of all repairs

Usage:
    repair.py project.dvp
    repair.py project.dvp --search-root /path/to/media
    repair.py project.dvp --output repaired.vpd --dry-run
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

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
SCRIPT_NAME = 'repair'
SCRIPT_INFO = {
    'name': SCRIPT_NAME,
    'description': 'Repair VideoProc Vlogger .vpd project files by finding missing media',
    'examples': [
        'project.dvp',
        'project.dvp --dry-run',
        'project.dvp --search-root /Users/john/Movies --output repaired.vpd',
        'project.dvp --search-root . --backup'
    ]
}

# Script-specific arguments
SCRIPT_ARGUMENTS = {
    'source_dvp': {
        'positional': True,
        'flag': '--source',
        'help': 'VideoProc Vlogger project folder (.dvp) or file (.vpd) to repair'
    },
    'search_root': {
        'flag': '--search-root',
        'help': 'Root directory to search for missing files (default: parent of project file)'
    },
    'output_file': {
        'flag': '--output',
        'help': 'Output file path (default: overwrites input file)'
    },
    'backup': {
        'flag': '--backup',
        'action': 'store_true',
        'help': 'Create backup before modifying (recommended)'
    },
    'no_backup': {
        'flag': '--no-backup',
        'action': 'store_true',
        'help': 'Skip backup creation (not recommended)'
    }
}

# Merge with standard arguments (verbose, quiet, dry_run)
ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


class VPDResource:
    """Represents a media resource in a VPD file."""
    
    def __init__(self, resource_type: str, location: str, uuid: str, path: str, title: str):
        self.type = resource_type
        self.location = location
        self.uuid = uuid
        self.path = path
        self.title = title
        self.exists = os.path.exists(path)


class VPDRepair:
    """Repairs VideoProc Vlogger project files."""
    
    def __init__(self, vpd_path: str, search_root: Optional[str] = None, 
                 dry_run: bool = False, logger=None):
        """
        Initialize VPD repair tool.
        
        Args:
            vpd_path: Path to the .vpd project file
            search_root: Root directory to search for missing files
            dry_run: If True, only preview changes without modifying files
            logger: Logger instance for output
        """
        self.vpd_path = Path(vpd_path)
        self.search_root = Path(search_root) if search_root else self.vpd_path.parent.parent
        self.dry_run = dry_run
        self.logger = logger
        self.vpd_data = None
        self.resources: List[VPDResource] = []
        
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
    
    def extract_resources(self) -> List[VPDResource]:
        """Extract all media resources from VPD file."""
        self.logger.info("Extracting media resources from project...")
        resources = []
        
        # Extract images from imagelist scapegoat
        if 'imagelist' in self.vpd_data and 'scapegoat' in self.vpd_data['imagelist']:
            for res in self.vpd_data['imagelist']['scapegoat']:
                resources.append(VPDResource(
                    resource_type='image',
                    location='imagelist.scapegoat',
                    uuid=res['uuid'],
                    path=res['path'],
                    title=res.get('title', 'Untitled')
                ))
        
        # Extract audio from audiolist subitems
        if 'audiolist' in self.vpd_data and 'subitems' in self.vpd_data['audiolist']:
            for res in self.vpd_data['audiolist']['subitems']:
                if 'uuid' in res and 'path' in res:
                    resources.append(VPDResource(
                        resource_type='audio',
                        location='audiolist.subitems',
                        uuid=res['uuid'],
                        path=res['path'],
                        title=res.get('title', 'Untitled')
                    ))
        
        # Extract video from videolist scapegoat
        if 'videolist' in self.vpd_data and 'scapegoat' in self.vpd_data['videolist']:
            for res in self.vpd_data['videolist']['scapegoat']:
                resources.append(VPDResource(
                    resource_type='video',
                    location='videolist.scapegoat',
                    uuid=res['uuid'],
                    path=res['path'],
                    title=res.get('title', 'Untitled')
                ))
        
        self.resources = resources
        self.logger.info(f"Found {len(resources)} total resources in project")
        
        # Count by type
        by_type = {}
        for r in resources:
            by_type[r.type] = by_type.get(r.type, 0) + 1
        
        for media_type, count in by_type.items():
            self.logger.debug(f"  {media_type}: {count} files")
        
        return resources
    
    def verify_resources(self) -> Tuple[List[VPDResource], List[VPDResource]]:
        """Check which resources exist and which are missing."""
        self.logger.info("Verifying file existence...")
        
        existing = []
        missing = []
        
        for res in self.resources:
            if res.exists:
                existing.append(res)
            else:
                missing.append(res)
        
        self.logger.info(f"Verification complete: {len(existing)} found, {len(missing)} missing")
        
        if missing:
            self.logger.warning(f"Missing files detected: {len(missing)} files need repair")
            for res in missing[:5]:  # Show first 5
                self.logger.debug(f"  Missing: {res.title} ({res.type}) - {res.path}")
            if len(missing) > 5:
                self.logger.debug(f"  ... and {len(missing) - 5} more")
        else:
            self.logger.info("✓ All files found - project is healthy!")
        
        return existing, missing
    
    def search_for_file(self, filename: str) -> List[str]:
        """
        Search for file in project directory tree.
        
        Args:
            filename: Name of file to search for
            
        Returns:
            List of matching file paths
        """
        matches = []
        filename_lower = filename.lower()
        
        # Try exact filename match
        for root, dirs, files in os.walk(self.search_root):
            for file in files:
                if file.lower() == filename_lower:
                    matches.append(os.path.join(root, file))
        
        # If no exact match, try stem match (different extensions)
        if not matches:
            stem = Path(filename).stem.lower()
            for root, dirs, files in os.walk(self.search_root):
                for file in files:
                    if Path(file).stem.lower() == stem:
                        matches.append(os.path.join(root, file))
        
        return matches
    
    def update_resource_path(self, resource: VPDResource, new_path: str) -> bool:
        """
        Update resource path in VPD data structure.
        
        Args:
            resource: Resource to update
            new_path: New file path
            
        Returns:
            True if successfully updated
        """
        location = resource.location
        uuid = resource.uuid
        
        if location == 'imagelist.scapegoat':
            for res in self.vpd_data['imagelist']['scapegoat']:
                if res['uuid'] == uuid:
                    res['path'] = new_path
                    return True
                    
        elif location == 'audiolist.subitems':
            for res in self.vpd_data['audiolist']['subitems']:
                if res.get('uuid') == uuid:
                    res['path'] = new_path
                    return True
                    
        elif location == 'videolist.scapegoat':
            for res in self.vpd_data['videolist']['scapegoat']:
                if res['uuid'] == uuid:
                    res['path'] = new_path
                    return True
        
        return False
    
    def repair_missing_files(self, missing: List[VPDResource]) -> Tuple[int, List[VPDResource]]:
        """
        Search for and repair missing file references.
        
        Args:
            missing: List of missing resources
            
        Returns:
            Tuple of (fixed_count, unfixed_resources)
        """
        if not missing:
            return 0, []
        
        self.logger.info(f"Searching for {len(missing)} missing files in {self.search_root}...")
        
        fixed = 0
        unfixed = []
        
        for res in missing:
            filename = Path(res.path).name
            self.logger.info(f"  Searching for: {filename}")
            
            matches = self.search_for_file(filename)
            
            if matches:
                if len(matches) == 1:
                    new_path = matches[0]
                    self.logger.info(f"    ✓ Found: {new_path}")
                    
                    if not self.dry_run:
                        if self.update_resource_path(res, new_path):
                            fixed += 1
                            self.logger.debug(f"    Updated resource UUID {res.uuid}")
                        else:
                            self.logger.error(f"    Failed to update resource in VPD data")
                            unfixed.append(res)
                    else:
                        self.logger.info(f"    [DRY RUN] Would update path to: {new_path}")
                        fixed += 1
                else:
                    self.logger.warning(f"    ! Multiple matches found ({len(matches)}):")
                    for i, match in enumerate(matches[:3], 1):
                        self.logger.warning(f"      {i}. {match}")
                    if len(matches) > 3:
                        self.logger.warning(f"      ... and {len(matches) - 3} more")
                    
                    # Use first match
                    new_path = matches[0]
                    self.logger.info(f"    Using first match: {new_path}")
                    
                    if not self.dry_run:
                        if self.update_resource_path(res, new_path):
                            fixed += 1
                        else:
                            unfixed.append(res)
                    else:
                        self.logger.info(f"    [DRY RUN] Would update path to: {new_path}")
                        fixed += 1
            else:
                self.logger.error(f"    ✗ Not found anywhere in search tree")
                unfixed.append(res)
        
        return fixed, unfixed
    
    def save_vpd(self, output_path: Path, backup_folder: Path = None):
        """
        Save updated VPD file.
        
        Args:
            output_path: Path to save file
            backup_folder: Path to backup .dvp folder (if provided)
        
        Returns:
            Path to backup folder if created, None otherwise
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would save to: {output_path}")
            return None
        
        backup_path = None
        
        # Create backup of entire .dvp folder if requested
        if backup_folder:
            self.logger.info(f"Creating backup: {backup_folder}")
            
            try:
                import shutil
                # Get the .dvp folder (parent of .vpd file)
                dvp_folder = self.vpd_path.parent
                
                # Copy entire .dvp folder to backup location
                shutil.copytree(dvp_folder, backup_folder, dirs_exist_ok=False)
                self.logger.info("✓ Backup created successfully")
                backup_path = backup_folder
            except Exception as e:
                self.logger.error(f"Failed to create backup: {e}")
                raise
        
        # Save updated VPD
        self.logger.info(f"Saving repaired project to: {output_path}")
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.vpd_data, f, indent=4)
            
            self.logger.info("✓ Project saved successfully")
            
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
        'source_dvp': ['source_dvp', 'source']
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
    
    # Setup logging with consistent pattern
    logger = parser.setup_logging(resolved_args, SCRIPT_NAME)

    # Determine search root
    search_root = resolved_args.get('search_root')
    if not search_root:
        # If source is a .dvp folder, search in its parent
        # If source is a .vpd file, search in the .dvp folder's parent (go up 2 levels)
        if source_path.suffix.lower() == '.vpd':
            search_root = source_path.parent.parent  # .vpd -> .dvp -> parent
        else:
            search_root = source_path.parent  # .dvp -> parent
        logger.debug(f"Using default search root: {search_root}")
    
    # Determine output path
    output_path = resolved_args.get('output_file')
    if output_path:
        output_path = Path(output_path)
    else:
        output_path = vpd_file
    
    # Determine backup behavior
    create_backup = True
    if resolved_args.get('no_backup'):
        create_backup = False
    elif resolved_args.get('backup'):
        create_backup = True
    elif output_path != vpd_file:
        # Different output file, no backup needed
        create_backup = False
    
    # Display configuration
    config_map = {
        'input_file': 'Input VPD file',
        'search_root': 'Search root directory',
        'output_file': 'Output file',
        'dry_run': 'Dry run mode',
        'backup': 'Create backup'
    }
    
    display_config = dict(resolved_args)
    display_config['search_root'] = str(search_root)
    display_config['output_file'] = str(output_path)
    display_config['backup'] = 'Yes' if create_backup else 'No'
    
    parser.display_configuration(display_config, config_map)
    
    try:
        # Initialize repair tool
        repairer = VPDRepair(
            vpd_path=str(vpd_file),
            search_root=str(search_root),
            dry_run=resolved_args.get('dry_run', False),
            logger=logger
        )
        
        # Load project file
        logger.info("================================================================================")
        logger.info(" STARTING VPD REPAIR PROCESS")
        logger.info("================================================================================")
        
        repairer.load_vpd()
        
        # Extract resources
        resources = repairer.extract_resources()
        
        if not resources:
            logger.warning("No media resources found in project file")
            if not resolved_args.get('quiet'):
                print("⚠️  No media resources found in project")
            return
        
        # Verify file existence
        existing, missing = repairer.verify_resources()
        
        if not missing:
            logger.info("================================================================================")
            logger.info(" NO REPAIRS NEEDED")
            logger.info("================================================================================")
            logger.info("All media files are present and accessible")
            
            if not resolved_args.get('quiet'):
                print(f"✅ Project is healthy - all {len(existing)} files found")
            return
        
        # Repair missing files
        logger.info("================================================================================")
        logger.info(" REPAIRING MISSING FILES")
        logger.info("================================================================================")
        
        fixed, unfixed = repairer.repair_missing_files(missing)
        
        # Summary
        logger.info("================================================================================")
        logger.info(" REPAIR SUMMARY")
        logger.info("================================================================================")
        logger.info(f"Total resources: {len(resources)}")
        logger.info(f"Existing files: {len(existing)}")
        logger.info(f"Missing files: {len(missing)}")
        logger.info(f"Fixed: {fixed}")
        logger.info(f"Unfixed: {len(unfixed)}")
        
        if unfixed:
            logger.warning("The following files could not be found:")
            for res in unfixed:
                logger.warning(f"  - {res.title} ({res.type})")
                logger.warning(f"    Original path: {res.path}")
        
        # Save if any changes were made
        if fixed > 0:
            logger.info("================================================================================")
            logger.info(" SAVING REPAIRED PROJECT")
            logger.info("================================================================================")
            
            # Create backup folder path with timestamp
            backup_folder_path = None
            if create_backup and output_path == vpd_file:
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                dvp_folder = source_path if source_path.suffix.lower() == '.dvp' else source_path.parent
                backup_name = f"{dvp_folder.stem}.backup.{timestamp}.dvp"
                backup_folder_path = dvp_folder.parent / backup_name
            
            backup_result = repairer.save_vpd(output_path, backup_folder_path)
            
            if not resolved_args.get('quiet'):
                if resolved_args.get('dry_run'):
                    print(f"🔍 [DRY RUN] Would fix {fixed} of {len(missing)} missing files")
                else:
                    print(f"✅ Repaired {fixed} of {len(missing)} missing files")
                    if backup_result:
                        print(f"📦 Backup saved: {backup_result}")
                    print(f"💾 Saved to: {output_path}")
        else:
            logger.warning("No files could be repaired - no changes saved")
            if not resolved_args.get('quiet'):
                print(f"❌ Could not find any of the {len(missing)} missing files")
        
        logger.info("================================================================================")
        logger.info(" REPAIR PROCESS COMPLETE")
        logger.info("================================================================================")
        
    except Exception as e:
        logger.error(f"Error during repair: {e}")
        if resolved_args.get('verbose'):
            import traceback
            logger.error(traceback.format_exc())
        
        if not resolved_args.get('quiet'):
            print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
