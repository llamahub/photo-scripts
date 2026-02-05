#!/usr/bin/env python3
"""
Reorganize photo library to standardized structure.
Target: <decade>/<YYYY>/<YYYY-MM>/<YYYY-MM-DD (optional event name) (optional seq#)>/

Strategy (based on user preferences):
1. Folders with ≤50 files → Keep as-is (can be YYYY-MM or YYYY-MM-DD format)
2. Folders with >50 files → Split chronologically into ~50 file groups with seq# (_01, _02, etc.)
3. Files without dates → use parent folder date
4. Same-date events → keep separate folders
5. Month-level loose files → group into dated folders based on EXIF
"""

import os
import sys
import re
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Image extensions
IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
    '.heic', '.heif', '.webp', '.cr2', '.nef', '.arw', '.dng', '.raw'
}

# Sidecar extensions (including suffixes)
SIDECAR_PATTERNS = ['.xmp', '.json', '.unknown', '.possible']

# Max files per folder
MAX_FILES_PER_FOLDER = 50


def is_sidecar(filename):
    """Check if file is a sidecar."""
    name_lower = filename.lower()
    for pattern in SIDECAR_PATTERNS:
        if name_lower.endswith(pattern):
            return True
    return False


def extract_date_from_filename(filename):
    """Extract date from filename."""
    stem = Path(filename).stem
    
    # Pattern 1: YYYY-MM-DD at start
    match = re.search(r'^(\d{4})-(\d{2})-(\d{2})', stem)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    
    # Pattern 2: YYYY_MM_DD
    match = re.search(r'(\d{4})_(\d{2})_(\d{2})', stem)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    
    # Pattern 3: YYYYMMDD (8 digits)
    match = re.search(r'(\d{4})(\d{2})(\d{2})', stem)
    if match:
        try:
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}"
        except:
            pass
    
    return None


def extract_datetime_from_filename(filename):
    """Extract datetime from filename for sorting."""
    stem = Path(filename).stem
    
    # Pattern: YYYY-MM-DD_HHMM
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})_(\d{4})', stem)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)} {match.group(4)[:2]}:{match.group(4)[2:]}:00"
    
    # Pattern: YYYY-MM-DD (no time)
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', stem)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)} 12:00:00"
    
    return None


def extract_date_from_exif(filepath):
    """Extract date from EXIF data using exiftool."""
    try:
        result = subprocess.run(
            ['exiftool', '-DateTimeOriginal', '-d', '%Y-%m-%d', '-s3', str(filepath)],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            date_str = result.stdout.strip()
            # Validate date format
            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                return date_str
    except:
        pass
    
    return None


def extract_datetime_from_exif(filepath):
    """Extract full datetime from EXIF for sorting."""
    try:
        result = subprocess.run(
            ['exiftool', '-DateTimeOriginal', '-d', '%Y-%m-%d %H:%M:%S', '-s3', str(filepath)],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    
    return None


def extract_date_from_folder(folder_path):
    """Extract date from parent folder path using MM-01 as default day."""
    parts = folder_path.parts
    
    # Look for YYYY-MM pattern in path
    for part in reversed(parts):
        match = re.match(r'^(\d{4})-(\d{2})$', part)
        if match:
            return f"{match.group(1)}-{match.group(2)}-01"
    
    return None


def get_file_date(filepath, relative_path):
    """Get file date using strategy: filename → EXIF → folder."""
    filename = filepath.name
    
    # Strategy 1: Filename
    date = extract_date_from_filename(filename)
    if date:
        return date, 'filename'
    
    # Strategy 2: EXIF (only for image files)
    if filepath.suffix.lower() in IMAGE_EXTENSIONS:
        date = extract_date_from_exif(filepath)
        if date:
            return date, 'exif'
    
    # Strategy 3: Parent folder
    date = extract_date_from_folder(relative_path.parent)
    if date:
        return date, 'folder'
    
    return None, 'unknown'


def get_sort_key(filepath, relative_path):
    """Get datetime for sorting files chronologically."""
    filename = filepath.name
    
    # Try filename datetime first
    dt = extract_datetime_from_filename(filename)
    if dt:
        return dt
    
    # Try EXIF datetime
    if filepath.suffix.lower() in IMAGE_EXTENSIONS:
        dt = extract_datetime_from_exif(filepath)
        if dt:
            return dt
    
    # Fallback: use filename for alphabetical sort
    return filename


def extract_event_name(folder_name):
    """Extract event name from folder, removing date prefix."""
    folder = folder_name
    
    # Remove date patterns
    folder = re.sub(r'^\d{4}-\d{2}-\d{2}\s+', '', folder)
    folder = re.sub(r'^\d{4}-\d{2}-\d{2}_', '', folder)
    folder = re.sub(r'^\d{4}-\d{2}\s+', '', folder)
    folder = re.sub(r'^\d{4}-\d{2}_', '', folder)
    
    # If what remains is just a date pattern or empty, no event name
    if not folder or re.match(r'^\d{4}-\d{2}(-\d{2})?$', folder):
        return None
    
    # Remove trailing underscores and clean up
    folder = folder.strip('_').strip()
    
    return folder if folder else None


def get_decade_folder(date_str):
    """Get decade folder name from date (e.g., 2020+ for 2020-2029)."""
    year = int(date_str[:4])
    decade_start = (year // 10) * 10
    return f"{decade_start}+"


def normalize_folder_structure(folder_path):
    """Normalize folder path to target structure."""
    parts = folder_path.parts
    
    if len(parts) < 3:
        return None
    
    # Target: <decade>/<YYYY>/<YYYY-MM>/...
    # Extract decade, year, month from existing path
    decade_pattern = r'^(\d{4})\+$'
    year_pattern = r'^(\d{4})$'
    month_pattern = r'^(\d{4})-(\d{2})$'
    
    decade = None
    year = None
    month = None
    event_level_start = 0
    
    # Look for decade folder
    for i, part in enumerate(parts):
        if re.match(decade_pattern, part):
            decade = part
            event_level_start = i + 1
            break
    
    if not decade:
        return None
    
    # Look for year folder
    if event_level_start < len(parts):
        if re.match(year_pattern, parts[event_level_start]):
            year = parts[event_level_start]
            event_level_start += 1
    
    # Look for month folder
    if event_level_start < len(parts):
        if re.match(month_pattern, parts[event_level_start]):
            month = parts[event_level_start]
            event_level_start += 1
    
    # Remaining path is event folders
    event_folders = parts[event_level_start:] if event_level_start < len(parts) else ()
    
    return {
        'decade': decade,
        'year': year,
        'month': month,
        'event_folders': event_folders,
        'event_level_start': event_level_start,
        'needs_restructure': not (decade and year and month)
    }


def analyze_and_plan_reorganization(library_path):
    """Analyze library and create reorganization plan."""
    library = Path(library_path)
    
    print(f"{'='*70}")
    print(f"ANALYZING LIBRARY FOR REORGANIZATION")
    print(f"{'='*70}")
    print(f"Library: {library_path}")
    print(f"This will take several minutes...")
    print(f"{'='*70}\n")
    
    # Track all files and their target locations
    stats = {
        'total_media': 0,
        'total_sidecars': 0,
        'total_other': 0,
        'date_sources': defaultdict(int),
        'folders_to_split': 0,
        'folders_kept_as_is': 0,
        'moves_needed': 0
    }
    
    # Group files by their current folder first
    folders_with_files = defaultdict(lambda: {
        'media_files': [],
        'sidecar_files': [],
        'other_files': []
    })
    
    # Walk through library
    processed_folders = 0
    for root, dirs, files in os.walk(library):
        # Skip hidden and special folders
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'orphaned-sidecars']
        
        rel_path = Path(root).relative_to(library)
        processed_folders += 1
        
        if processed_folders % 100 == 0:
            print(f"  Processed {processed_folders} folders...")
        
        # Categorize files in this folder
        for filename in files:
            if filename.startswith('.'):
                continue
            
            filepath = Path(root) / filename
            ext = filepath.suffix.lower()
            
            if ext in IMAGE_EXTENSIONS:
                folders_with_files[str(rel_path)]['media_files'].append(filepath)
                stats['total_media'] += 1
            elif is_sidecar(filename):
                folders_with_files[str(rel_path)]['sidecar_files'].append(filepath)
                stats['total_sidecars'] += 1
            else:
                folders_with_files[str(rel_path)]['other_files'].append(filepath)
                stats['total_other'] += 1
    
    print(f"  Completed scanning {processed_folders} folders\n")
    print("Determining folder restructuring needs...")
    
    # Process each folder
    final_operations = []
    folder_splits = {}
    
    for folder_rel_path, files_dict in folders_with_files.items():
        media_files = files_dict['media_files']
        sidecar_files = files_dict['sidecar_files']
        other_files = files_dict['other_files']
        
        if not media_files:
            # Preserve other files in place
            for other_file in other_files:
                final_operations.append({
                    'type': 'preserve',
                    'source_path': str(other_file.relative_to(library)),
                    'filename': other_file.name
                })
            continue
        
        folder_path = Path(folder_rel_path)
        structure = normalize_folder_structure(folder_path)
        
        # Determine target folder structure
        if structure and not structure['needs_restructure']:
            # Folder already has correct decade/year/month structure
            decade = structure['decade']
            year = structure['year']
            month = structure['month']
            
            # Keep the current event folder name (last part of path)
            current_folder_name = folder_path.name
            
            # Build target base folder
            if structure['event_folders']:
                # Has event subfolder - use it
                target_base = f"{decade}/{year}/{month}/{current_folder_name}"
            else:
                # Is at month level - this is month-level files
                # Need to check if we should keep at month or move to dated folders
                target_base = f"{decade}/{year}/{month}"
                current_folder_name = month  # Use month as folder name for month-level files
        else:
            # Folder needs restructuring - extract date info from files
            # Get representative date from first file
            sample_file = media_files[0]
            file_date, date_source = get_file_date(sample_file, sample_file.relative_to(library))
            
            if not file_date:
                # Can't determine date - skip
                continue
            
            decade = get_decade_folder(file_date)
            year = file_date[:4]
            month = file_date[:7]
            
            # Try to preserve current folder name as event name
            current_folder_name = folder_path.name
            event_name = extract_event_name(current_folder_name)
            
            if event_name:
                target_base = f"{decade}/{year}/{month}/{month} {event_name}"
            else:
                target_base = f"{decade}/{year}/{month}"
            
            current_folder_name = folder_path.name
        
        # Check if folder needs splitting
        num_media_files = len(media_files)
        
        if num_media_files <= MAX_FILES_PER_FOLDER:
            # Keep folder as-is (no split needed)
            stats['folders_kept_as_is'] += 1
            target_folder = target_base if structure and not structure['needs_restructure'] else f"{target_base}/{current_folder_name}" if event_name else target_base
            
            # Process all media files in this folder
            for media_file in media_files:
                file_rel_path = media_file.relative_to(library)
                file_date, date_source = get_file_date(media_file, file_rel_path)
                stats['date_sources'][date_source] += 1
                
                # Get sort key
                sort_key = get_sort_key(media_file, file_rel_path)
                
                # Find associated sidecars
                media_stem = media_file.stem.lower()
                associated_sidecars = []
                for sidecar in sidecar_files:
                    sidecar_stem_lower = sidecar.name.lower()
                    if sidecar_stem_lower.startswith(media_stem):
                        associated_sidecars.append(str(sidecar.relative_to(library)))
                
                file_entry = {
                    'source_path': str(file_rel_path),
                    'filename': media_file.name,
                    'date': file_date,
                    'date_source': date_source,
                    'sort_key': sort_key,
                    'sidecars': associated_sidecars,
                    'current_folder': str(file_rel_path.parent),
                    'target_folder': target_folder
                }
                
                final_operations.append(file_entry)
        
        else:
            # Folder needs splitting - split chronologically
            stats['folders_to_split'] += 1
            
            # Collect all media files with their metadata
            files_with_metadata = []
            for media_file in media_files:
                file_rel_path = media_file.relative_to(library)
                file_date, date_source = get_file_date(media_file, file_rel_path)
                stats['date_sources'][date_source] += 1
                sort_key = get_sort_key(media_file, file_rel_path)
                
                # Find associated sidecars
                media_stem = media_file.stem.lower()
                associated_sidecars = []
                for sidecar in sidecar_files:
                    sidecar_stem_lower = sidecar.name.lower()
                    if sidecar_stem_lower.startswith(media_stem):
                        associated_sidecars.append(str(sidecar.relative_to(library)))
                
                files_with_metadata.append({
                    'path': media_file,
                    'rel_path': file_rel_path,
                    'date': file_date,
                    'date_source': date_source,
                    'sort_key': sort_key,
                    'sidecars': associated_sidecars
                })
            
            # Sort chronologically
            sorted_files = sorted(files_with_metadata, key=lambda x: x['sort_key'])
            
            # Split into groups
            num_splits = (len(sorted_files) + MAX_FILES_PER_FOLDER - 1) // MAX_FILES_PER_FOLDER
            
            for i in range(num_splits):
                start_idx = i * MAX_FILES_PER_FOLDER
                end_idx = min(start_idx + MAX_FILES_PER_FOLDER, len(sorted_files))
                split_files = sorted_files[start_idx:end_idx]
                
                # Create target folder with sequence number
                if structure and not structure['needs_restructure']:
                    target_folder = f"{target_base}_{i+1:02d}"
                else:
                    target_folder = f"{target_base}/{current_folder_name}_{i+1:02d}"
                
                for file_meta in split_files:
                    file_entry = {
                        'source_path': str(file_meta['rel_path']),
                        'filename': file_meta['path'].name,
                        'date': file_meta['date'],
                        'date_source': file_meta['date_source'],
                        'sort_key': file_meta['sort_key'],
                        'sidecars': file_meta['sidecars'],
                        'current_folder': str(file_meta['rel_path'].parent),
                        'target_folder': target_folder
                    }
                    
                    final_operations.append(file_entry)
            
            folder_splits[target_base] = num_splits
        
        # Preserve other files
        for other_file in other_files:
            final_operations.append({
                'type': 'preserve',
                'source_path': str(other_file.relative_to(library)),
                'filename': other_file.name
            })
    
    # Calculate move statistics
    for entry in final_operations:
        if entry.get('type') == 'preserve':
            continue
        
        source_folder = entry['current_folder']
        target_folder = entry.get('target_folder', '')
        
        if source_folder != target_folder:
            stats['moves_needed'] += 1
    
    return final_operations, stats, folder_splits


def save_reorganization_plan(operations, stats, folder_splits, output_file):
    """Save detailed reorganization plan to JSON."""
    plan = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'statistics': {
            'total_media_files': stats['total_media'],
            'total_sidecars': stats['total_sidecars'],
            'total_other_files': stats['total_other'],
            'files_needing_move': stats['moves_needed'],
            'folders_to_split': stats['folders_to_split'],
            'date_sources': dict(stats['date_sources'])
        },
        'folder_splits': folder_splits,
        'operations': operations
    }
    
    with open(output_file, 'w') as f:
        json.dump(plan, f, indent=2)
    
    return plan


def execute_reorganization(plan, library_path, dry_run=True):
    """Execute the reorganization plan."""
    library = Path(library_path)
    operations = plan['operations']
    
    print(f"\n{'='*70}")
    print(f"{'DRY RUN - ' if dry_run else ''}EXECUTING REORGANIZATION")
    print(f"{'='*70}\n")
    
    if dry_run:
        print("DRY RUN MODE: No files will be moved\n")
    
    stats = {
        'moved': 0,
        'preserved': 0,
        'errors': 0,
        'sidecars_moved': 0
    }
    
    errors = []
    
    # Create target folders and move files
    target_folders_created = set()
    
    for i, entry in enumerate(operations):
        if (i + 1) % 1000 == 0:
            print(f"  Processed {i+1}/{len(operations)} operations...")
        
        # Skip preserve operations (keep in place)
        if entry.get('type') == 'preserve':
            stats['preserved'] += 1
            continue
        
        source_path = library / entry['source_path']
        target_folder = entry.get('target_folder')
        
        if not target_folder:
            continue
        
        target_dir = library / target_folder
        target_path = target_dir / entry['filename']
        
        # Skip if already in correct location
        if source_path.parent == target_dir:
            continue
        
        # Create target directory
        if not dry_run:
            if target_folder not in target_folders_created:
                target_dir.mkdir(parents=True, exist_ok=True)
                target_folders_created.add(target_folder)
        
        # Move media file
        try:
            if not dry_run:
                if target_path.exists():
                    errors.append({
                        'file': str(entry['source_path']),
                        'error': 'destination_exists',
                        'target': str(target_path)
                    })
                    stats['errors'] += 1
                    continue
                
                shutil.move(str(source_path), str(target_path))
            
            stats['moved'] += 1
            
            # Move sidecars
            for sidecar_rel in entry.get('sidecars', []):
                sidecar_source = library / sidecar_rel
                sidecar_target = target_dir / Path(sidecar_rel).name
                
                if sidecar_source.exists():
                    if not dry_run:
                        if not sidecar_target.exists():
                            shutil.move(str(sidecar_source), str(sidecar_target))
                    stats['sidecars_moved'] += 1
        
        except Exception as e:
            errors.append({
                'file': str(entry['source_path']),
                'error': str(e)
            })
            stats['errors'] += 1
    
    return stats, errors


def reorganize_library(library_path, dry_run=True):
    """Main reorganization function."""
    
    # Phase 1: Analyze and plan
    print("Phase 1: Analyzing library and creating reorganization plan...")
    operations, stats, folder_splits = analyze_and_plan_reorganization(library_path)
    
    # Save plan
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(__file__).parent.parent / '.log'
    log_dir.mkdir(exist_ok=True)
    
    plan_file = log_dir / f"reorg_plan_{timestamp}.json"
    plan = save_reorganization_plan(operations, stats, folder_splits, plan_file)
    
    print(f"\n{'='*70}")
    print(f"REORGANIZATION PLAN SUMMARY")
    print(f"{'='*70}")
    print(f"Total media files:      {stats['total_media']:>8,}")
    print(f"Total sidecars:         {stats['total_sidecars']:>8,}")
    print(f"Total other files:      {stats['total_other']:>8,}")
    print(f"Files needing move:     {stats['moves_needed']:>8,}")
    print(f"Folders kept as-is:     {stats['folders_kept_as_is']:>8,}")
    print(f"Folders to split:       {stats['folders_to_split']:>8,}")
    
    print(f"\nDate source breakdown:")
    for source, count in stats['date_sources'].items():
        pct = 100 * count / stats['total_media'] if stats['total_media'] > 0 else 0
        print(f"  {source:10s}: {count:>8,} ({pct:>5.1f}%)")
    
    print(f"\nTop 10 folders being split:")
    sorted_splits = sorted(folder_splits.items(), key=lambda x: x[1], reverse=True)
    for folder, num_splits in sorted_splits[:10]:
        print(f"  {num_splits:>2} splits: {folder}")
    
    print(f"\n{'='*70}")
    print(f"PLAN SAVED TO:")
    print(f"  {plan_file}")
    print(f"{'='*70}")
    
    # Phase 2: Execute (no confirmation needed when --live is explicitly passed)
    exec_stats, errors = execute_reorganization(plan, library_path, dry_run)
    
    print(f"\n{'='*70}")
    print(f"EXECUTION SUMMARY")
    print(f"{'='*70}")
    print(f"Files moved:            {exec_stats['moved']:>8,}")
    print(f"Sidecars moved:         {exec_stats['sidecars_moved']:>8,}")
    print(f"Files preserved:        {exec_stats['preserved']:>8,}")
    print(f"Errors:                 {exec_stats['errors']:>8,}")
    
    if errors:
        errors_file = log_dir / f"reorg_errors_{timestamp}.json"
        with open(errors_file, 'w') as f:
            json.dump(errors, f, indent=2)
        print(f"\nErrors saved to: {errors_file}")
    
    print(f"{'='*70}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Reorganize photo library to standardized structure'
    )
    parser.add_argument('library_path', help='Path to photo library')
    parser.add_argument(
        '--live',
        action='store_true',
        help='Perform actual reorganization (default is dry-run mode)'
    )
    
    args = parser.parse_args()
    
    reorganize_library(args.library_path, dry_run=not args.live)
