#!/usr/bin/env python3
"""
Find all remaining unmatched sidecars in the photo library and move them to orphaned-sidecars folder.
Excludes sidecars with .unknown or .possible suffixes.
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

# Image extensions
IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
    '.heic', '.heif', '.webp', '.cr2', '.nef', '.arw', '.dng', '.raw'
}

# Video extensions
VIDEO_EXTENSIONS = {
    '.mov', '.mp4', '.avi', '.m4v', '.mpg', '.mpeg', '.wmv', '.mkv', '.flv', '.webm', '.3gp'
}

# Sidecar extensions
SIDECAR_EXTENSIONS = {'.xmp', '.json'}


def find_orphaned_sidecars(library_path):
    """Find all sidecars without matching media files."""
    library = Path(library_path)
    
    if not library.exists():
        print(f"Error: Library path does not exist: {library_path}")
        sys.exit(1)
    
    print(f"Scanning for orphaned sidecars in: {library_path}")
    print("This may take a few minutes...\n")
    
    orphaned = []
    total_sidecars = 0
    matched_sidecars = 0
    excluded_sidecars = 0
    
    # Walk through all directories
    for root, dirs, files in os.walk(library):
        # Skip hidden directories and orphaned-sidecars folder
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'orphaned-sidecars']
        
        if not files:
            continue
        
        # Collect media files in this directory
        media_files = []
        sidecar_files = []
        
        for filename in files:
            if filename.startswith('.'):
                continue
            
            ext = Path(filename).suffix.lower()
            
            if ext in IMAGE_EXTENSIONS or ext in VIDEO_EXTENSIONS:
                media_files.append(filename)
            elif ext in SIDECAR_EXTENSIONS:
                sidecar_files.append(filename)
        
        if not sidecar_files:
            continue
        
        # Create set of media base names
        media_stems = {Path(f).stem.lower() for f in media_files}
        
        # Check each sidecar
        for sidecar_file in sidecar_files:
            total_sidecars += 1
            
            # Skip .unknown and .possible sidecars
            if sidecar_file.endswith('.unknown') or sidecar_file.endswith('.possible'):
                excluded_sidecars += 1
                continue
            
            # Get base name of sidecar (without .xmp or .json)
            sidecar_stem = Path(sidecar_file).stem.lower()
            
            # Check if there's a matching media file
            if sidecar_stem in media_stems:
                matched_sidecars += 1
                continue
            
            # This is an orphaned sidecar
            full_path = Path(root) / sidecar_file
            orphaned.append(full_path)
    
    return orphaned, total_sidecars, matched_sidecars, excluded_sidecars


def move_orphaned_sidecars(library_path, dry_run=True):
    """Move orphaned sidecars to a dedicated folder."""
    library = Path(library_path)
    
    # Find orphaned sidecars
    orphaned, total_sidecars, matched_sidecars, excluded_sidecars = find_orphaned_sidecars(library_path)
    
    print(f"{'='*70}")
    print(f"ORPHANED SIDECAR CLEANUP")
    print(f"{'='*70}")
    print(f"Total sidecars found:         {total_sidecars:>6,}")
    print(f"Matched (with media):         {matched_sidecars:>6,}")
    print(f"Excluded (.unknown/.possible): {excluded_sidecars:>6,}")
    print(f"Orphaned (no match):          {len(orphaned):>6,}")
    print(f"\nMode: {'DRY RUN' if dry_run else 'LIVE - WILL MOVE FILES'}")
    print(f"{'='*70}\n")
    
    if not orphaned:
        print("No orphaned sidecars found!")
        return
    
    # Create orphaned-sidecars directory
    orphaned_dir = library / 'orphaned-sidecars'
    
    if not dry_run:
        orphaned_dir.mkdir(exist_ok=True)
        print(f"Created directory: {orphaned_dir}\n")
    
    # Track statistics
    stats = {
        'success': 0,
        'error': 0,
        'dest_exists': 0
    }
    
    operations = []
    errors = []
    
    # Process orphaned sidecars
    for sidecar_path in orphaned:
        # Preserve folder structure to avoid name conflicts
        rel_path = sidecar_path.relative_to(library)
        
        # Create subdirectory structure in orphaned-sidecars
        # Convert path separators to underscores for flat structure
        new_name = str(rel_path).replace('/', '_')
        new_path = orphaned_dir / new_name
        
        operation = {
            'old_path': str(sidecar_path),
            'new_path': str(new_path),
            'original_location': str(rel_path.parent),
            'status': 'pending'
        }
        
        # Check if destination already exists
        if new_path.exists():
            stats['dest_exists'] += 1
            operation['status'] = 'dest_exists'
            errors.append(operation)
            continue
        
        # Perform move if not dry run
        if not dry_run:
            try:
                shutil.move(str(sidecar_path), str(new_path))
                operation['status'] = 'success'
                stats['success'] += 1
            except Exception as e:
                operation['status'] = 'error'
                operation['error'] = str(e)
                stats['error'] += 1
                errors.append(operation)
        else:
            operation['status'] = 'would_move'
        
        operations.append(operation)
    
    # Save operation log
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(__file__).parent.parent / '.log'
    log_dir.mkdir(exist_ok=True)
    
    import json
    operations_file = log_dir / f"orphaned_sidecar_cleanup_{timestamp}.json"
    
    with open(operations_file, 'w') as f:
        json.dump(operations, f, indent=2)
    
    if errors:
        errors_file = log_dir / f"orphaned_sidecar_cleanup_errors_{timestamp}.json"
        with open(errors_file, 'w') as f:
            json.dump(errors, f, indent=2)
    
    # Print summary
    print(f"{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    
    if not dry_run:
        print(f"Moved successfully:   {stats['success']:>6,}")
        print(f"Errors:               {stats['error']:>6,}")
        print(f"Destination exists:   {stats['dest_exists']:>6,}")
        
        print(f"\nOrphaned sidecars moved to:")
        print(f"  {orphaned_dir}")
    else:
        print(f"Would move {len(operations):,} orphaned sidecars to:")
        print(f"  {orphaned_dir}")
    
    print(f"\n{'='*70}")
    print(f"LOG FILE")
    print(f"{'='*70}")
    print(f"Operations: {operations_file}")
    if errors:
        print(f"Errors:     {errors_file}")
    
    # Show examples
    if operations:
        print(f"\n{'='*70}")
        print(f"EXAMPLE OPERATIONS (showing up to 15):")
        print(f"{'='*70}")
        
        for op in operations[:15]:
            print(f"\n{op['status'].upper()}")
            print(f"  From: {op['old_path']}")
            print(f"  To:   {op['new_path']}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Move orphaned sidecars to dedicated folder'
    )
    parser.add_argument('library_path', help='Path to photo library')
    parser.add_argument(
        '--live',
        action='store_true',
        help='Perform actual moves (default is dry-run mode)'
    )
    
    args = parser.parse_args()
    
    move_orphaned_sidecars(args.library_path, dry_run=not args.live)
