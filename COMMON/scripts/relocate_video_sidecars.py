#!/usr/bin/env python3
"""
Move video sidecars to their matched videos in the video library.
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime


def move_video_sidecars(matches_file, dry_run=True):
    """
    Move video sidecars to the video library.
    
    Args:
        matches_file: JSON file with video sidecar matches
        dry_run: If True, only simulate moves without actually changing files
    """
    
    if not Path(matches_file).exists():
        print(f"Error: Matches file not found: {matches_file}")
        sys.exit(1)
    
    # Load matches
    with open(matches_file, 'r') as f:
        matches = json.load(f)
    
    print(f"{'='*70}")
    print(f"VIDEO SIDECAR RELOCATION")
    print(f"{'='*70}")
    print(f"Matches file: {matches_file}")
    print(f"Total matches: {len(matches):,}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE - WILL MOVE FILES'}")
    print(f"{'='*70}\n")
    
    # All video matches are medium confidence, so add .possible suffix
    print(f"All sidecars will be moved with .possible suffix")
    print(f"\n{'='*70}\n")
    
    # Track statistics
    stats = {
        'success': 0,
        'error': 0,
        'dest_exists': 0,
        'source_missing': 0
    }
    
    operations = []
    errors = []
    
    # Process all matches
    for match in matches:
        sidecar_path = Path(match['sidecar_path'])
        video_path = Path(match['video_path'])
        
        # Construct new sidecar name and path
        video_stem = video_path.stem
        sidecar_ext = sidecar_path.suffix
        
        # Add .possible suffix for medium confidence
        new_sidecar_name = f"{video_stem}{sidecar_ext}.possible"
        new_sidecar_path = video_path.parent / new_sidecar_name
        
        operation = {
            'old_path': str(sidecar_path),
            'new_path': str(new_sidecar_path),
            'video': match['video'],
            'video_folder': match['video_folder'],
            'confidence': match['confidence'],
            'status': 'pending'
        }
        
        # Check if source exists
        if not sidecar_path.exists():
            stats['source_missing'] += 1
            operation['status'] = 'source_missing'
            errors.append(operation)
            continue
        
        # Check if destination already exists
        if new_sidecar_path.exists():
            stats['dest_exists'] += 1
            operation['status'] = 'dest_exists'
            errors.append(operation)
            continue
        
        # Perform move if not dry run
        if not dry_run:
            try:
                # Ensure destination directory exists
                new_sidecar_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Move the file
                shutil.move(str(sidecar_path), str(new_sidecar_path))
                
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
    log_dir = Path(matches_file).parent
    
    operations_file = log_dir / f"video_sidecar_relocations_{timestamp}.json"
    errors_file = log_dir / f"video_sidecar_relocation_errors_{timestamp}.json"
    
    with open(operations_file, 'w') as f:
        json.dump(operations, f, indent=2)
    
    if errors:
        with open(errors_file, 'w') as f:
            json.dump(errors, f, indent=2)
    
    # Print summary
    print(f"{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    
    if not dry_run:
        print(f"\nMoved successfully:   {stats['success']:>6,}")
        print(f"Errors:               {stats['error']:>6,}")
        print(f"Destination exists:   {stats['dest_exists']:>6,}")
        print(f"Source missing:       {stats['source_missing']:>6,}")
        
        total_failed = stats['error'] + stats['dest_exists'] + stats['source_missing']
        print(f"\nTotal:")
        print(f"  Moved:              {stats['success']:>6,}")
        print(f"  Failed:             {total_failed:>6,}")
    else:
        print(f"Would move {len(operations):,} video sidecars")
    
    print(f"\n{'='*70}")
    print(f"LOG FILES")
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
            print(f"\n[{op['confidence']}%] {op['status'].upper()}")
            print(f"  From: {op['old_path']}")
            print(f"  To:   {op['new_path']}")
    
    if errors and not dry_run:
        print(f"\n{'='*70}")
        print(f"ERRORS (showing up to 5):")
        print(f"{'='*70}")
        for err in errors[:5]:
            print(f"\n{err['status'].upper()}: {err.get('error', err['status'])}")
            print(f"  Path: {err['old_path']}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Move video sidecars to their matched videos in the video library'
    )
    parser.add_argument('matches_file', help='Path to video sidecar matches JSON file')
    parser.add_argument(
        '--live',
        action='store_true',
        help='Perform actual moves (default is dry-run mode)'
    )
    
    args = parser.parse_args()
    
    move_video_sidecars(args.matches_file, dry_run=not args.live)
