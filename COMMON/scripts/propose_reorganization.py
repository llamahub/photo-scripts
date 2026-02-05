#!/usr/bin/env python3
"""
Analyze photo library and propose reorganization to standardized structure.
Target: <decade>/<YYYY>/<YYYY-MM>/<YYYY-MM-DD (optional event name) (optional seq#)>/
"""

import os
import sys
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Image extensions
IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
    '.heic', '.heif', '.webp', '.cr2', '.nef', '.arw', '.dng', '.raw'
}

# Sidecar extensions
SIDECAR_EXTENSIONS = {'.xmp', '.json'}

# Non-media files to preserve
OTHER_EXTENSIONS = {'.uuid', '.heic_original'}


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
    
    # Pattern 3: YYYYMMDD
    match = re.search(r'(\d{4})(\d{2})(\d{2})', stem)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    
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
            return result.stdout.strip()
    except:
        pass
    
    return None


def extract_event_name(folder_name):
    """Extract event name from folder, removing date prefix if present."""
    # Remove leading date patterns
    folder = folder_name
    
    # Pattern: YYYY-MM-DD event name
    folder = re.sub(r'^\d{4}-\d{2}-\d{2}\s+', '', folder)
    # Pattern: YYYY-MM-DD_event name
    folder = re.sub(r'^\d{4}-\d{2}-\d{2}_', '', folder)
    
    # If what remains is just a date pattern, no event name
    if re.match(r'^\d{4}-\d{2}(-\d{2})?$', folder):
        return None
    
    return folder if folder else None


def analyze_current_structure(library_path):
    """Analyze current folder structure and file organization."""
    library = Path(library_path)
    
    print(f"Analyzing library: {library_path}")
    print("This may take a few minutes...\n")
    
    stats = {
        'total_files': 0,
        'total_folders': 0,
        'files_by_level': defaultdict(int),
        'folders_with_files': [],
        'files_without_dates': [],
        'large_folders': [],
        'non_standard_structure': [],
        'month_folders_with_files': [],
        'files_at_month_level': 0
    }
    
    # Walk through library
    for root, dirs, files in os.walk(library):
        # Skip hidden and special folders
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'orphaned-sidecars']
        
        rel_path = Path(root).relative_to(library)
        level = len(rel_path.parts)
        
        if level > 0:
            stats['total_folders'] += 1
        
        # Count files
        media_files = []
        sidecar_files = []
        other_files = []
        
        for filename in files:
            if filename.startswith('.'):
                continue
            
            ext = Path(filename).suffix.lower()
            
            if ext in IMAGE_EXTENSIONS:
                media_files.append(filename)
                stats['total_files'] += 1
            elif ext in SIDECAR_EXTENSIONS or filename.endswith(('.unknown', '.possible')):
                sidecar_files.append(filename)
            else:
                other_files.append(filename)
        
        if not media_files:
            continue
        
        stats['files_by_level'][level] += len(media_files)
        
        folder_info = {
            'path': str(rel_path),
            'level': level,
            'media_count': len(media_files),
            'sidecar_count': len(sidecar_files),
            'other_count': len(other_files),
            'has_subdirs': len(dirs) > 0
        }
        
        stats['folders_with_files'].append(folder_info)
        
        # Identify large folders
        if len(media_files) > 50:
            stats['large_folders'].append(folder_info)
        
        # Identify month-level folders with files (level 3)
        if level == 3 and len(media_files) > 0:
            stats['month_folders_with_files'].append(folder_info)
            stats['files_at_month_level'] += len(media_files)
        
        # Check for files without extractable dates
        sample_files = media_files[:5]
        files_without_dates = []
        for filename in sample_files:
            file_date = extract_date_from_filename(filename)
            if not file_date:
                full_path = Path(root) / filename
                exif_date = extract_date_from_exif(full_path)
                if not exif_date:
                    files_without_dates.append(filename)
        
        if files_without_dates:
            stats['files_without_dates'].append({
                'folder': str(rel_path),
                'sample_files': files_without_dates
            })
    
    return stats


def propose_reorganization(library_path):
    """Propose reorganization plan."""
    
    stats = analyze_current_structure(library_path)
    
    print(f"{'='*70}")
    print(f"LIBRARY REORGANIZATION PROPOSAL")
    print(f"{'='*70}\n")
    
    print(f"CURRENT STATE:")
    print(f"  Total media files:        {stats['total_files']:>6,}")
    print(f"  Total folders with files: {len(stats['folders_with_files']):>6,}")
    print(f"  Folders > 50 files:       {len(stats['large_folders']):>6,}")
    
    print(f"\n  Files by nesting level:")
    for level in sorted(stats['files_by_level'].keys()):
        count = stats['files_by_level'][level]
        pct = 100 * count / stats['total_files']
        print(f"    Level {level}: {count:>6,} files ({pct:>5.1f}%)")
    
    print(f"\n  Files at month level (need date folders): {stats['files_at_month_level']:>6,}")
    
    # Analyze target structure
    print(f"\n{'='*70}")
    print(f"TARGET STRUCTURE:")
    print(f"{'='*70}")
    print(f"  <decade>/<YYYY>/<YYYY-MM>/<YYYY-MM-DD (event) (seq)>/")
    print(f"  Maximum 50 media files per folder")
    print(f"  Sidecars travel with media files")
    print(f"  Non-media files preserved in original folders")
    
    # Calculate reorganization needs
    print(f"\n{'='*70}")
    print(f"REORGANIZATION REQUIREMENTS:")
    print(f"{'='*70}\n")
    
    print(f"1. FOLDERS NEEDING SPLITTING (> 50 files):")
    print(f"   {len(stats['large_folders'])} folders need splitting")
    
    # Show largest folders
    large_sorted = sorted(stats['large_folders'], key=lambda x: x['media_count'], reverse=True)
    print(f"\n   Top 10 largest folders:")
    for folder in large_sorted[:10]:
        num_splits = (folder['media_count'] + 49) // 50
        print(f"     {folder['media_count']:>4} files → {num_splits} folders: {folder['path']}")
    
    print(f"\n2. MONTH-LEVEL FILES NEEDING DATE FOLDERS:")
    print(f"   {len(stats['month_folders_with_files'])} month folders have files")
    print(f"   {stats['files_at_month_level']:>6,} files need date-specific folders")
    
    if stats['month_folders_with_files']:
        print(f"\n   Examples:")
        for folder in stats['month_folders_with_files'][:5]:
            print(f"     {folder['media_count']:>4} files in: {folder['path']}")
    
    print(f"\n3. FILES WITHOUT EXTRACTABLE DATES:")
    if stats['files_without_dates']:
        print(f"   {len(stats['files_without_dates'])} folders have files without dates")
        print(f"\n   Examples (sample files checked):")
        for item in stats['files_without_dates'][:5]:
            print(f"     {item['folder']}")
            for filename in item['sample_files'][:2]:
                print(f"       • {filename}")
    else:
        print(f"   None found (all files have extractable dates)")
    
    # Identify potential issues
    print(f"\n{'='*70}")
    print(f"POTENTIAL ISSUES & QUESTIONS:")
    print(f"{'='*70}\n")
    
    issues = []
    
    # Issue 1: Month folders with both files and subdirs
    month_with_both = [f for f in stats['month_folders_with_files'] if f['has_subdirs']]
    if month_with_both:
        issues.append({
            'issue': 'Month folders containing BOTH files and event subfolders',
            'count': len(month_with_both),
            'description': 'These folders have files at the month level AND event subfolders.',
            'question': 'Should month-level files be moved to a dated folder or kept separate?',
            'examples': [f['path'] for f in month_with_both[:5]]
        })
    
    # Issue 2: Event name conflicts
    issues.append({
        'issue': 'Event name preservation',
        'description': 'Many folders have descriptive event names.',
        'question': 'How to handle folders with same date but different events?',
        'examples': ['2024-11-20 Thanksgiving', '2024-11-20 Family Photos']
    })
    
    # Issue 3: Files without dates
    if stats['files_without_dates']:
        issues.append({
            'issue': 'Files without extractable dates',
            'count': len(stats['files_without_dates']),
            'description': 'Some files lack dates in filename or EXIF.',
            'question': 'Should these use folder date or be flagged for manual review?',
            'examples': [f['folder'] for f in stats['files_without_dates'][:3]]
        })
    
    # Issue 4: Large splits
    very_large = [f for f in stats['large_folders'] if f['media_count'] > 200]
    if very_large:
        issues.append({
            'issue': 'Very large folders requiring many splits',
            'count': len(very_large),
            'description': f'Some folders have 200+ files (largest: {large_sorted[0]["media_count"]} files).',
            'question': 'Should split sequentially or try to group by time/sub-events?',
            'examples': [f"{f['media_count']} files in {f['path']}" for f in very_large[:3]]
        })
    
    # Print issues
    for i, issue in enumerate(issues, 1):
        print(f"{i}. {issue['issue'].upper()}")
        print(f"   {issue['description']}")
        print(f"   Question: {issue['question']}")
        if 'count' in issue:
            print(f"   Affected: {issue['count']} folders")
        if 'examples' in issue:
            print(f"   Examples:")
            for ex in issue['examples']:
                print(f"     • {ex}")
        print()
    
    # Recommendations
    print(f"{'='*70}")
    print(f"RECOMMENDATIONS:")
    print(f"{'='*70}\n")
    
    print(f"1. DATE EXTRACTION STRATEGY:")
    print(f"   • First try: Extract from filename")
    print(f"   • Second try: Extract from EXIF")
    print(f"   • Fallback: Use parent folder date")
    print(f"   • Manual review: Flag files with uncertain dates")
    
    print(f"\n2. EVENT NAME HANDLING:")
    print(f"   • Preserve existing event names from folder names")
    print(f"   • For same-date different events: Keep distinct folders")
    print(f"   • Format: YYYY-MM-DD Event Name_01, YYYY-MM-DD Event Name_02")
    
    print(f"\n3. SPLITTING STRATEGY:")
    print(f"   • Sort files by datetime (filename, then EXIF)")
    print(f"   • Split chronologically into groups of 50")
    print(f"   • Sequence number if multiple folders needed")
    
    print(f"\n4. MONTH-LEVEL FILES:")
    print(f"   • Create dated folders based on file dates")
    print(f"   • Keep in same month directory structure")
    print(f"   • If mixed dates, create multiple date folders")
    
    print(f"\n5. NON-MEDIA FILES:")
    print(f"   • Preserve in same folder as they appear")
    print(f"   • Move with media if entire folder reorganized")
    
    print(f"\n{'='*70}")
    print(f"EXECUTION PLAN:")
    print(f"{'='*70}\n")
    
    print(f"Phase 1: DRY RUN - Generate reorganization plan")
    print(f"  • Analyze all files and determine target folders")
    print(f"  • Detect conflicts and issues")
    print(f"  • Create detailed operation log (JSON)")
    print(f"  • Estimate: ~10-15 minutes for {stats['total_files']:,} files")
    
    print(f"\nPhase 2: REVIEW - Manual inspection")
    print(f"  • Review generated plan")
    print(f"  • Check flagged issues")
    print(f"  • Approve or adjust strategy")
    
    print(f"\nPhase 3: EXECUTE - Perform reorganization")
    print(f"  • Create new folder structure")
    print(f"  • Move files to target locations")
    print(f"  • Move sidecars with media files")
    print(f"  • Verify all files moved successfully")
    print(f"  • Generate completion report")
    
    # Save analysis
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(__file__).parent.parent / '.log'
    log_dir.mkdir(exist_ok=True)
    
    analysis_file = log_dir / f"reorg_analysis_{timestamp}.json"
    with open(analysis_file, 'w') as f:
        # Convert to serializable format
        output = {
            'timestamp': timestamp,
            'total_files': stats['total_files'],
            'total_folders': len(stats['folders_with_files']),
            'large_folders': stats['large_folders'],
            'month_folders': stats['month_folders_with_files'],
            'files_without_dates': stats['files_without_dates'],
            'issues': issues
        }
        json.dump(output, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"ANALYSIS SAVED TO:")
    print(f"  {analysis_file}")
    print(f"{'='*70}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze photo library and propose reorganization'
    )
    parser.add_argument('library_path', help='Path to photo library')
    
    args = parser.parse_args()
    
    propose_reorganization(args.library_path)
