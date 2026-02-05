#!/usr/bin/env python3
"""
Analyze photo library folder structure and create a sample subset.
"""

import sys
import os
from pathlib import Path
from collections import defaultdict
import random
import json

# File extensions to consider
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.gif', '.bmp', '.tiff', '.tif'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.mpg', '.mpeg'}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

def analyze_structure(base_path):
    """Analyze folder structure and file distribution."""
    base_path = Path(base_path)
    
    # Statistics
    nesting_levels = defaultdict(int)  # level -> count of files
    folder_file_counts = defaultdict(list)  # level -> list of file counts per folder
    all_files = []
    deviations = []
    
    print(f"Scanning {base_path}...")
    file_count = 0
    
    # Walk the directory tree
    for root, dirs, files in os.walk(base_path):
        root_path = Path(root)
        
        # Filter to media files only
        media_files = [f for f in files if Path(f).suffix.lower() in MEDIA_EXTENSIONS]
        
        if media_files:
            # Calculate nesting level
            try:
                rel_path = root_path.relative_to(base_path)
                parts = rel_path.parts
                level = len(parts)
            except ValueError:
                level = 0
            
            nesting_levels[level] += len(media_files)
            folder_file_counts[level].append(len(media_files))
            
            # Store file info
            for f in media_files:
                file_path = root_path / f
                all_files.append({
                    'path': str(file_path),
                    'rel_path': str(file_path.relative_to(base_path)),
                    'level': level,
                    'folder': str(root_path)
                })
            
            file_count += len(media_files)
            if file_count % 1000 == 0:
                print(f"  Processed {file_count} files...")
            
            # Check for pattern deviations
            # Expected pattern: <decade>/<year>/<month>/<event> or similar
            if level > 0:
                folder_name = root_path.name
                parent_name = root_path.parent.name if root_path.parent != base_path else ""
                
                # Check if pattern is violated
                if level == 1 and not (folder_name.endswith('+') or folder_name.isdigit()):
                    deviations.append({
                        'path': str(rel_path),
                        'level': level,
                        'reason': 'Top level folder not decade or year format'
                    })
    
    print(f"Total files found: {file_count}")
    
    return {
        'nesting_levels': dict(nesting_levels),
        'folder_file_counts': {k: {'min': min(v), 'max': max(v), 'avg': sum(v) / len(v), 'count': len(v)} 
                               for k, v in folder_file_counts.items()},
        'all_files': all_files,
        'deviations': deviations,
        'total_files': file_count
    }

def create_sample(all_files, sample_size=150):
    """Create a stratified sample of files maintaining folder structure."""
    
    # Group files by folder
    by_folder = defaultdict(list)
    for f in all_files:
        by_folder[f['folder']].append(f)
    
    # Calculate how many files to take from each folder
    folders = list(by_folder.keys())
    files_per_folder = max(1, sample_size // len(folders))
    
    sampled_files = []
    for folder in folders:
        folder_files = by_folder[folder]
        n_to_take = min(files_per_folder, len(folder_files))
        sampled_files.extend(random.sample(folder_files, n_to_take))
        
        if len(sampled_files) >= sample_size:
            break
    
    # If we haven't reached sample_size, randomly add more
    if len(sampled_files) < sample_size:
        remaining = [f for f in all_files if f not in sampled_files]
        n_more = min(sample_size - len(sampled_files), len(remaining))
        sampled_files.extend(random.sample(remaining, n_more))
    
    return sampled_files[:sample_size]

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_photo_structure.py <base_path> [sample_size]")
        print("  base_path: Path to photo library (e.g., /mnt/photo_drive/santee-images)")
        print("  sample_size: Number of files to sample (default: 150)")
        sys.exit(1)
    
    base_path = sys.argv[1]
    sample_size = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    
    if not os.path.exists(base_path):
        print(f"Error: Path does not exist: {base_path}")
        sys.exit(1)
    
    print("="*80)
    print("PHOTO LIBRARY STRUCTURE ANALYSIS")
    print("="*80)
    print()
    
    # Analyze structure
    analysis = analyze_structure(base_path)
    
    # Print results
    print("\n" + "="*80)
    print("NESTING LEVEL DISTRIBUTION")
    print("="*80)
    for level in sorted(analysis['nesting_levels'].keys()):
        count = analysis['nesting_levels'][level]
        print(f"Level {level}: {count:,} files")
    
    print("\n" + "="*80)
    print("FILES PER FOLDER STATISTICS")
    print("="*80)
    for level in sorted(analysis['folder_file_counts'].keys()):
        stats = analysis['folder_file_counts'][level]
        print(f"Level {level}:")
        print(f"  Folders: {stats['count']:,}")
        print(f"  Files per folder: min={stats['min']}, max={stats['max']}, avg={stats['avg']:.1f}")
    
    if analysis['deviations']:
        print("\n" + "="*80)
        print("PATTERN DEVIATIONS")
        print("="*80)
        for dev in analysis['deviations'][:20]:  # Show first 20
            print(f"  {dev['path']} - {dev['reason']}")
        if len(analysis['deviations']) > 20:
            print(f"  ... and {len(analysis['deviations']) - 20} more")
    
    # Create sample
    print("\n" + "="*80)
    print(f"CREATING SAMPLE ({sample_size} files)")
    print("="*80)
    sampled = create_sample(analysis['all_files'], sample_size)
    
    # Save results
    output_dir = Path.cwd() / '.log'
    output_dir.mkdir(exist_ok=True)
    
    analysis_file = output_dir / 'photo_structure_analysis.json'
    sample_file = output_dir / 'photo_sample_list.txt'
    
    # Save full analysis
    with open(analysis_file, 'w') as f:
        json.dump({
            'nesting_levels': analysis['nesting_levels'],
            'folder_file_counts': analysis['folder_file_counts'],
            'deviations': analysis['deviations'],
            'total_files': analysis['total_files']
        }, f, indent=2)
    print(f"\nAnalysis saved to: {analysis_file}")
    
    # Save sample list
    with open(sample_file, 'w') as f:
        f.write(f"# Sample of {len(sampled)} files from {base_path}\n")
        f.write(f"# Total files in library: {analysis['total_files']:,}\n\n")
        for item in sorted(sampled, key=lambda x: x['rel_path']):
            f.write(f"{item['rel_path']}\n")
    print(f"Sample list saved to: {sample_file}")
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

if __name__ == '__main__':
    main()
