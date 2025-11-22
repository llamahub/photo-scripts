#!/usr/bin/env python3
"""
================================================================================
=== [Rename Script] - Rename files using EXIF metadata and structured naming
================================================================================

Renames image, video, and sidecar files in a target directory using standardized
naming conventions based on EXIF metadata. Uses ImageData.getTargetFilename to
generate new filenames with the pattern:

  YYYY-MM-DD_HHMM_WIDTHxHEIGHT_PARENT_BASENAME.EXT

Where:
  - YYYY-MM-DD: Date from EXIF metadata
  - HHMM: Time from EXIF metadata
  - WIDTHxHEIGHT: Image/video dimensions
  - PARENT: Original parent folder name (if applicable)
  - BASENAME: Original filename (cleaned)
  - EXT: True file extension from EXIF

Processes:
  - Image files: .jpg, .jpeg, .png, .gif, .bmp, .tif, .tiff, .heic, .raw, etc.
  - Video files: .mp4, .mov, .avi, .mkv, .wmv, .flv, .webm, .m4v, etc.
  - Sidecar files: .xmp, .aae (renamed to match their associated media file)
"""

import sys
import os
from pathlib import Path

# Add COMMON to path for shared utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'COMMON', 'src'))

# Add project source paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

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

# Import EXIF modules
try:
    from exif.image_data import ImageData
except ImportError as e:
    print(f"Error importing required modules: {e}", file=sys.stderr)
    sys.exit(1)

# Script metadata
SCRIPT_INFO = {
    'name': 'Rename Script',
    'description': '''Rename files using EXIF metadata and structured naming conventions

Generates standardized filenames: YYYY-MM-DD_HHMM_WIDTHxHEIGHT_PARENT_BASENAME.EXT

Processes image files, video files, and their sidecar files (.xmp, .aae).
Preserves original files unless --move is used.''',
    'examples': [
        '/path/to/photos',
        '--target /path/to/photos --dry-run',
        '/path/to/photos --move --verbose',
        '/path/to/organized --label vacation',
        '. run rename .tmp/sorted'
    ]
}

# Script-specific arguments
SCRIPT_ARGUMENTS = {
    'target': {
        'positional': True,
        'help': 'Target directory containing files to rename'
    },
    'label': {
        'flag': '--label',
        'help': 'Optional label to include in renamed filenames'
    },
    'move': {
        'flag': '--move',
        'action': 'store_true',
        'help': 'Rename files in place (move) instead of copying with new names'
    }
}

# Merge with standard arguments (verbose, quiet, dry_run)
ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)

# Supported file extensions
IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff',
    '.heic', '.raw', '.cr2', '.nef', '.arw', '.dng', '.orf', '.rw2'
}

VIDEO_EXTENSIONS = {
    '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm',
    '.m4v', '.3gp', '.mts', '.m2ts', '.ts'
}

SIDECAR_EXTENSIONS = {
    '.xmp', '.aae'
}


def is_media_file(file_path: Path) -> bool:
    """Check if file is a supported media format (image or video)."""
    ext = file_path.suffix.lower()
    return ext in IMAGE_EXTENSIONS or ext in VIDEO_EXTENSIONS


def is_sidecar_file(file_path: Path) -> bool:
    """Check if file is a sidecar file."""
    return file_path.suffix.lower() in SIDECAR_EXTENSIONS


def find_media_files(target_dir: Path, logger) -> list:
    """Find all media files in target directory recursively."""
    media_files = []
    
    logger.info(f"Scanning target directory: {target_dir}")
    
    try:
        for root, dirs, files in os.walk(target_dir):
            root_path = Path(root)
            
            for filename in files:
                file_path = root_path / filename
                if is_media_file(file_path):
                    media_files.append(file_path)
                    
                    if len(media_files) % 100 == 0:
                        logger.debug(f"Found {len(media_files)} media files so far...")
    
    except PermissionError as e:
        logger.error(f"Permission denied accessing {target_dir}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while scanning {target_dir}: {e}")
    
    logger.info(f"Found {len(media_files)} media files to process")
    return media_files


def find_sidecar_file(media_file: Path) -> Path | None:
    """Find sidecar file associated with media file."""
    for ext in SIDECAR_EXTENSIONS:
        sidecar = media_file.with_suffix(ext)
        if sidecar.exists():
            return sidecar
    return None


def rename_file(source_path: Path, target_path: Path, dry_run: bool, move: bool, logger) -> bool:
    """Rename or copy file to new path."""
    try:
        if source_path == target_path:
            logger.debug(f"Skipping (already has target name): {source_path.name}")
            return False
        
        if target_path.exists():
            logger.warning(f"Target already exists, skipping: {target_path.name}")
            return False
        
        if not dry_run:
            # Ensure parent directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            if move:
                source_path.rename(target_path)
                logger.info(f"Renamed: {source_path.name} → {target_path.name}")
            else:
                import shutil
                shutil.copy2(source_path, target_path)
                logger.info(f"Copied with new name: {source_path.name} → {target_path.name}")
        else:
            action = "rename" if move else "copy"
            logger.info(f"[DRY RUN] Would {action}: {source_path.name} → {target_path.name}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error renaming {source_path.name}: {e}")
        return False


def main():
    """Main entry point with consistent argument parsing and structure."""
    
    # Create argument parser
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    
    # Print standardized header
    parser.print_header()
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate and resolve required arguments
    try:
        resolved_args = parser.validate_required_args(args, {
            'target_dir': ['target_file', 'target']
        })
    except SystemExit:
        # Handle missing arguments
        target = getattr(args, 'target_file', None) or getattr(args, 'target', None)
        
        if not target:
            print("target directory is required", file=sys.stderr)
            sys.exit(1)
    
    # Setup logging with consistent pattern
    logger = parser.setup_logging(resolved_args, "rename")
    
    # Display configuration
    config_map = {
        'target_dir': 'Target directory',
        'label': 'Label for filenames'
    }
    parser.display_configuration(resolved_args, config_map)
    
    # Additional configuration display
    if not resolved_args.get('quiet'):
        if resolved_args.get('move'):
            print("Operation: RENAME in place (move)")
        else:
            print("Operation: COPY with new names (preserve originals)")
        print()
    
    try:
        target_dir = Path(resolved_args['target_dir']).resolve()
        label = resolved_args.get('label', '')
        dry_run = resolved_args.get('dry_run', False)
        move = resolved_args.get('move', False)
        
        # Validate target directory
        if not target_dir.exists():
            raise FileNotFoundError(f"Target directory does not exist: {target_dir}")
        if not target_dir.is_dir():
            raise NotADirectoryError(f"Target is not a directory: {target_dir}")
        
        logger.info("Starting file rename process")
        logger.info(f"Target directory: {target_dir}")
        logger.info(f"Label: {label if label else '(none)'}")
        logger.info(f"Operation mode: {'RENAME' if move else 'COPY'}")
        logger.info(f"Dry run: {dry_run}")
        
        # Find all media files
        media_files = find_media_files(target_dir, logger)
        
        if not media_files:
            logger.info("No media files found to process")
            if not resolved_args.get('quiet'):
                print("No media files found in target directory")
            return 0
        
        # Statistics
        stats = {
            'processed': 0,
            'renamed': 0,
            'skipped': 0,
            'errors': 0,
            'sidecars': 0
        }
        
        # Process each media file
        logger.info(f"Processing {len(media_files)} media files...")
        
        for i, media_file in enumerate(media_files, 1):
            stats['processed'] += 1
            
            if i % 50 == 0 or i == len(media_files):
                logger.info(f"Progress: {i}/{len(media_files)} files processed")
            
            try:
                # Generate new normalized filename (just the filename, not full path)
                logger.debug(f"Generating normalized filename for: {media_file}")
                new_filename = ImageData.getNormalizedFilename(
                    str(media_file),
                    label
                )
                
                # Keep file in same directory, just rename it
                new_path = media_file.parent / new_filename
                
                # Rename the media file
                if rename_file(media_file, new_path, dry_run, move, logger):
                    stats['renamed'] += 1
                    
                    # Check for sidecar file
                    sidecar = find_sidecar_file(media_file)
                    if sidecar:
                        # Generate matching sidecar name
                        new_sidecar = new_path.with_suffix(sidecar.suffix)
                        
                        if rename_file(sidecar, new_sidecar, dry_run, move, logger):
                            stats['sidecars'] += 1
                            logger.debug(f"Renamed sidecar: {sidecar.name} → {new_sidecar.name}")
                else:
                    stats['skipped'] += 1
            
            except Exception as e:
                logger.error(f"Error processing {media_file}: {e}")
                stats['errors'] += 1
        
        # Log final statistics
        logger.info("=" * 80)
        logger.info(" RENAME COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Files processed: {stats['processed']}")
        logger.info(f"Files renamed: {stats['renamed']}")
        logger.info(f"Sidecar files renamed: {stats['sidecars']}")
        logger.info(f"Files skipped: {stats['skipped']}")
        logger.info(f"Errors encountered: {stats['errors']}")
        
        if dry_run:
            logger.info("NOTE: This was a dry run - no files were actually renamed")
        
        logger.info("=" * 80)
        
        if not resolved_args.get('quiet'):
            print("✅ Rename process completed successfully")
            print(f"Files processed: {stats['processed']}")
            print(f"Files renamed: {stats['renamed']}")
            if stats['sidecars'] > 0:
                print(f"Sidecar files renamed: {stats['sidecars']}")
            if stats['skipped'] > 0:
                print(f"Files skipped: {stats['skipped']}")
            if stats['errors'] > 0:
                print(f"⚠️  Errors encountered: {stats['errors']}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error during rename process: {e}")
        if not resolved_args.get('quiet'):
            print(f"❌ Error: {e}")
            print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
