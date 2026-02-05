#!/usr/bin/env python3
"""
Move orphaned sidecars to their matched images across folders.
Different confidence levels get different treatments.
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime


def move_sidecars(matches_file, dry_run=True):
    """
    Move sidecars based on confidence levels.
    
    Args:
        matches_file: JSON file with cross-folder matches
        dry_run: If True, only simulate moves without actually changing files
    """
    
    if not Path(matches_file).exists():
        print(f"Error: Matches file not found: {matches_file}")
        sys.exit(1)
    
    # Load matches
    with open(matches_file, 'r') as f:
        matches = json.load(f)
    
    print(f"{'='*70}")
    print(f"CROSS-FOLDER SIDECAR RELOCATION")
    print(f"{'='*70}")
    print(f"Matches file: {matches_file}")
    print(f"Total matches: {len(matches):,}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE - WILL MOVE FILES'}")
    print(f"{'='*70}\n")
    
    # Categorize by confidence
    high_conf = [m for m in matches if m['category'] == 'high_confidence']
    medium_conf = [m for m in matches if m['category'] == 'medium_confidence']
    low_conf = [m for m in matches if m['category'] == 'low_confidence']
    
    print(f"High confidence (≥80%):    {len(high_conf):>6,} (will move)")
    print(f"Medium confidence (60-79%): {len(medium_conf):>6,} (will move + .possible)")
    print(f"Low confidence (<60%):     {len(low_conf):>6,} (will move + .unknown)")
    print(f"\n{'='*70}\n")
    
    # Track statistics
    stats = {
        'high_success': 0,
        'high_error': 0,
        'medium_success': 0,
        'medium_error': 0,
        'low_success': 0,
        'low_error': 0,
        'dest_exists': 0,
        'source_missing': 0
    }
    
    operations = []
    errors = []
    
    # Process all matches
    all_matches = [
        (high_conf, 'high', ''),
        (medium_conf, 'medium', '.possible'),
        (low_conf, 'low', '.unknown')
    ]
    
    for match_list, category, suffix in all_matches:
        for match in match_list:
            sidecar_path = Path(match['sidecar_path'])
            image_path = Path(match['image_path'])
            
            # Construct new sidecar name and path
            image_stem = image_path.stem
            sidecar_ext = sidecar_path.suffix
            
            new_sidecar_name = f"{image_stem}{sidecar_ext}{suffix}"
            new_sidecar_path = image_path.parent / new_sidecar_name
            
            operation = {
                'category': category,
                'old_path': str(sidecar_path),
                'new_path': str(new_sidecar_path),
                'old_folder': match['original_folder'],
                'new_folder': match['matched_folder'],
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
                    if category == 'high':
                        stats['high_success'] += 1
                    elif category == 'medium':
                        stats['medium_success'] += 1
                    else:
                        stats['low_success'] += 1
                        
                except Exception as e:
                    operation['status'] = 'error'
                    operation['error'] = str(e)
                    if category == 'high':
                        stats['high_error'] += 1
                    elif category == 'medium':
                        stats['medium_error'] += 1
                    else:
                        stats['low_error'] += 1
                    errors.append(operation)
            else:
                operation['status'] = 'would_move'
            
            operations.append(operation)
    
    # Save operation log
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(matches_file).parent
    
    operations_file = log_dir / f"sidecar_relocations_{timestamp}.json"
    errors_file = log_dir / f"sidecar_relocation_errors_{timestamp}.json"
    
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
        print(f"\nHigh Confidence:")
        print(f"  Moved successfully:   {stats['high_success']:>6,}")
        print(f"  Errors:               {stats['high_error']:>6,}")
        
        print(f"\nMedium Confidence (.possible suffix):")
        print(f"  Moved successfully:   {stats['medium_success']:>6,}")
        print(f"  Errors:               {stats['medium_error']:>6,}")
        
        print(f"\nLow Confidence (.unknown suffix):")
        print(f"  Moved successfully:   {stats['low_success']:>6,}")
        print(f"  Errors:               {stats['low_error']:>6,}")
        
        print(f"\nIssues:")
        print(f"  Destination exists:   {stats['dest_exists']:>6,}")
        print(f"  Source missing:       {stats['source_missing']:>6,}")
        
        total_success = stats['high_success'] + stats['medium_success'] + stats['low_success']
        total_errors = stats['high_error'] + stats['medium_error'] + stats['low_error'] + stats['dest_exists'] + stats['source_missing']
        
        print(f"\nTotal:")
        print(f"  Moved:                {total_success:>6,}")
        print(f"  Failed:               {total_errors:>6,}")
    else:
        print(f"Would move {len(operations):,} sidecars")
        print(f"  High confidence:      {len(high_conf):>6,}")
        print(f"  Medium confidence:    {len(medium_conf):>6,}")
        print(f"  Low confidence:       {len(low_conf):>6,}")
    
    print(f"\n{'='*70}")
    print(f"LOG FILES")
    print(f"{'='*70}")
    print(f"Operations: {operations_file}")
    if errors:
        print(f"Errors:     {errors_file}")
    
    # Show examples
    if operations:
        print(f"\n{'='*70}")
        print(f"EXAMPLE OPERATIONS (showing up to 10):")
        print(f"{'='*70}")
        
        # Show high confidence first
        high_ops = [op for op in operations if op['category'] == 'high']
        for op in high_ops[:5]:
            print(f"\n[{op['confidence']}%] {op['status'].upper()}")
            print(f"  From: {op['old_path']}")
            print(f"  To:   {op['new_path']}")
        
        # Show medium confidence examples
        medium_ops = [op for op in operations if op['category'] == 'medium']
        if medium_ops:
            print(f"\n--- Medium Confidence Examples ---")
            for op in medium_ops[:3]:
                print(f"\n[{op['confidence']}%] {op['status'].upper()}")
                print(f"  From: {op['old_path']}")
                print(f"  To:   {op['new_path']}")
        
        # Show low confidence examples
        low_ops = [op for op in operations if op['category'] == 'low']
        if low_ops:
            print(f"\n--- Low Confidence Examples ---")
            for op in low_ops[:2]:
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
        description='Move orphaned sidecars to their matched images across folders'
    )
    parser.add_argument('matches_file', help='Path to cross-folder matches JSON file')
    parser.add_argument(
        '--live',
        action='store_true',
        help='Perform actual moves (default is dry-run mode)'
    )
    
    args = parser.parse_args()
    
    move_sidecars(args.matches_file, dry_run=not args.live)
