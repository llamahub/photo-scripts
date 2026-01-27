#!/usr/bin/env python3
"""
================================================================================
=== [Extract Videos Script] - Extract video files to organized structure
================================================================================

Extracts all video files from subdirectories of a source directory and copies/moves
them to matching subdirectories in a target directory, preserving the folder
structure.

Processes:
  - Video files: .mp4, .mov, .avi, .mkv, .wmv, .flv, .webm, .m4v, etc.

Preserves original files unless --move is used.
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

# Script metadata
SCRIPT_INFO = {
    'name': 'Extract Videos Script',
    'description': '''Extract video files to organized structure

Copies/moves all video files from subdirectories of source directory to matching
subdirectories in target directory, preserving folder structure.

Supports copy (preserve originals) or move (remove originals) modes.''',
    'examples': [
        '/mnt/photo_drive/santee-images /mnt/photo_drive/santee-videos',
        '/source/photos --target /target/videos --move',
        '. run extract_videos /media/photos /media/videos --dry-run',
        '/photos /videos --verbose'
    ]
}

# Script-specific arguments
SCRIPT_ARGUMENTS = {
    'source': {
        'positional': True,
        'help': 'Source directory containing images/media with videos in subdirectories'
    },
    'target': {
        'positional': True,
        'help': 'Target directory where extracted videos will be organized',
        'nargs': '?',
        'default': '/mnt/photo_drive/santee-videos'
    },
    'move': {
        'flag': '--move',
        'action': 'store_true',
        'help': 'Move video files instead of copying (removes originals)'
    }
}

# Merge with standard arguments (verbose, quiet, dry_run)
ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)

# Supported video file extensions
VIDEO_EXTENSIONS = {
    '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm',
    '.m4v', '.3gp', '.mts', '.m2ts', '.ts', '.mpg', '.mpeg'
}

# Sidecar file extensions
SIDECAR_EXTENSIONS = {
    '.xmp', '.aae'
}


def is_video_file(file_path: Path) -> bool:
    """Check if file is a supported video format."""
    ext = file_path.suffix.lower()
    return ext in VIDEO_EXTENSIONS


def find_sidecar_file(video_file: Path) -> Path | None:
    """Find sidecar file associated with video file."""
    for ext in SIDECAR_EXTENSIONS:
        sidecar = video_file.with_suffix(ext)
        if sidecar.exists():
            return sidecar
    return None


def find_video_files(source_dir: Path, logger) -> dict:
    """
    Find all video files in source directory recursively.
    Returns dict mapping relative subdirectory to list of video files.
    """
    videos_by_dir = {}
    
    logger.info(f"Scanning source directory: {source_dir}")
    
    try:
        for root, dirs, files in os.walk(source_dir):
            root_path = Path(root)
            
            relative_path = root_path.relative_to(source_dir)
            
            videos_in_dir = []
            for filename in files:
                file_path = root_path / filename
                if is_video_file(file_path):
                    videos_in_dir.append(file_path)
            
            if videos_in_dir:
                videos_by_dir[str(relative_path)] = videos_in_dir
    
    except PermissionError as e:
        logger.error(f"Permission denied accessing {source_dir}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while scanning {source_dir}: {e}")
    
    # Count total videos
    total_videos = sum(len(v) for v in videos_by_dir.values())
    logger.info(f"Found {total_videos} video files in {len(videos_by_dir)} subdirectories")
    
    return videos_by_dir


def extract_video_file(source_path: Path, target_path: Path, dry_run: bool, move: bool, logger) -> bool:
    """Extract (copy or move) video file to target path."""
    try:
        if source_path == target_path:
            logger.debug(f"Skipping (already at target): {source_path.name}")
            return False
        
        if target_path.exists():
            logger.warning(f"Target already exists, skipping: {target_path.name}")
            return False
        
        if not dry_run:
            # Ensure parent directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            if move:
                source_path.rename(target_path)
                logger.audit(f"MOVED: {source_path} → {target_path}")
            else:
                import shutil
                shutil.copy2(source_path, target_path)
                logger.audit(f"COPIED: {source_path} → {target_path}")
        else:
            action = "move" if move else "copy"
            logger.audit(f"[DRY RUN] Would {action.upper()}: {source_path} → {target_path}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error extracting {source_path.name}: {e}")
        return False


def extract_sidecar_file(source_sidecar: Path, target_sidecar: Path, dry_run: bool, move: bool, logger) -> bool:
    """Extract (copy or move) sidecar file to target path."""
    try:
        if source_sidecar == target_sidecar:
            return False
        
        if target_sidecar.exists():
            logger.debug(f"Sidecar target already exists, skipping: {target_sidecar.name}")
            return False
        
        if not dry_run:
            # Ensure parent directory exists
            target_sidecar.parent.mkdir(parents=True, exist_ok=True)
            
            if move:
                source_sidecar.rename(target_sidecar)
                logger.audit(f"MOVED SIDECAR: {source_sidecar} → {target_sidecar}")
            else:
                import shutil
                shutil.copy2(source_sidecar, target_sidecar)
                logger.audit(f"COPIED SIDECAR: {source_sidecar} → {target_sidecar}")
        else:
            action = "move" if move else "copy"
            logger.debug(f"[DRY RUN] Would {action} sidecar: {source_sidecar.name}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error extracting sidecar {source_sidecar.name}: {e}")
        return False


def main():
    """Main entry point with consistent argument parsing and structure."""
    
    # Create argument parser
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    
    # Print standardized header
    parser.print_header()
    
    # Parse arguments
    args = parser.parse_args()
    
    # Resolve positional arguments
    source = getattr(args, 'source', None)
    target = getattr(args, 'target', None) or '/mnt/photo_drive/santee-videos'
    
    if not source:
        print("Error: source directory is required", file=sys.stderr)
        sys.exit(1)
    
    # Setup logging with consistent pattern
    resolved_args = {
        'source_dir': source,
        'target_dir': target,
        'move': getattr(args, 'move', False),
        'dry_run': getattr(args, 'dry_run', False),
        'verbose': getattr(args, 'verbose', False),
        'quiet': getattr(args, 'quiet', False)
    }
    
    logger = parser.setup_logging(resolved_args, "extract_videos")
    
    # Display configuration
    if not resolved_args['quiet']:
        print(f"Source directory: {source}")
        print(f"Target directory: {target}")
        if resolved_args['move']:
            print("Operation: MOVE video files (remove originals)")
        else:
            print("Operation: COPY video files (preserve originals)")
        if resolved_args['dry_run']:
            print("Mode: DRY RUN (simulation only)")
        print()
    
    try:
        source_dir = Path(source).resolve()
        target_dir = Path(target).resolve()
        dry_run = resolved_args['dry_run']
        move = resolved_args['move']
        
        # Validate directories
        if not source_dir.exists():
            raise FileNotFoundError(f"Source directory does not exist: {source_dir}")
        if not source_dir.is_dir():
            raise NotADirectoryError(f"Source is not a directory: {source_dir}")
        
        logger.info("Starting video extraction process")
        logger.info(f"Source directory: {source_dir}")
        logger.info(f"Target directory: {target_dir}")
        logger.info(f"Operation mode: {'MOVE' if move else 'COPY'}")
        logger.info(f"Dry run: {dry_run}")
        
        # Find all video files
        videos_by_dir = find_video_files(source_dir, logger)
        
        if not videos_by_dir:
            logger.info("No video files found to extract")
            if not resolved_args['quiet']:
                print("No video files found in subdirectories")
            return 0
        
        # Statistics
        stats = {
            'dirs_processed': 0,
            'videos_copied': 0,
            'videos_moved': 0,
            'sidecars_copied': 0,
            'sidecars_moved': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # Process each subdirectory
        logger.info(f"Processing {len(videos_by_dir)} subdirectories...")
        
        total_videos = sum(len(v) for v in videos_by_dir.values())
        processed = 0
        
        for subdir, video_files in sorted(videos_by_dir.items()):
            stats['dirs_processed'] += 1
            
            logger.debug(f"Processing subdirectory: {subdir} ({len(video_files)} videos)")
            
            # Create target subdirectory path
            target_subdir = target_dir / subdir
            
            for video_file in video_files:
                processed += 1
                target_video = target_subdir / video_file.name
                
                try:
                    if extract_video_file(video_file, target_video, dry_run, move, logger):
                        if move:
                            stats['videos_moved'] += 1
                        else:
                            stats['videos_copied'] += 1
                        
                        # Check for and extract sidecar file
                        sidecar = find_sidecar_file(video_file)
                        if sidecar:
                            target_sidecar = target_video.with_suffix(sidecar.suffix)
                            if extract_sidecar_file(sidecar, target_sidecar, dry_run, move, logger):
                                if move:
                                    stats['sidecars_moved'] += 1
                                else:
                                    stats['sidecars_copied'] += 1
                                logger.debug(f"Extracted sidecar: {sidecar.name} → {target_sidecar.name}")
                    else:
                        stats['skipped'] += 1
                    
                    if processed % 50 == 0 or processed == total_videos:
                        logger.info(f"Progress: {processed}/{total_videos} videos processed")
                
                except Exception as e:
                    logger.error(f"Error processing {video_file}: {e}")
                    stats['errors'] += 1
        
        # Log final statistics
        logger.info("=" * 80)
        logger.info(" EXTRACTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Subdirectories processed: {stats['dirs_processed']}")
        logger.info(f"Videos copied: {stats['videos_copied']}")
        logger.info(f"Videos moved: {stats['videos_moved']}")
        logger.info(f"Sidecar files copied: {stats['sidecars_copied']}")
        logger.info(f"Sidecar files moved: {stats['sidecars_moved']}")
        logger.info(f"Videos skipped: {stats['skipped']}")
        logger.info(f"Errors encountered: {stats['errors']}")
        
        if dry_run:
            logger.info("NOTE: This was a dry run - no files were actually extracted")
        
        logger.info("=" * 80)
        
        if not resolved_args['quiet']:
            print("✅ Video extraction completed successfully")
            print(f"Subdirectories processed: {stats['dirs_processed']}")
            print(f"Videos copied: {stats['videos_copied']}")
            if stats['videos_moved'] > 0:
                print(f"Videos moved: {stats['videos_moved']}")
            if stats['sidecars_copied'] > 0:
                print(f"Sidecar files copied: {stats['sidecars_copied']}")
            if stats['sidecars_moved'] > 0:
                print(f"Sidecar files moved: {stats['sidecars_moved']}")
            if stats['skipped'] > 0:
                print(f"Videos skipped: {stats['skipped']}")
            if stats['errors'] > 0:
                print(f"⚠️  Errors encountered: {stats['errors']}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error during extraction process: {e}")
        if not resolved_args['quiet']:
            print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
