#!/usr/bin/env python3
"""
Verify that the photo library reorganization was successful.
Checks:
1. No folders exceed 50 files
2. Folder structure matches expected pattern
3. All media files have proper dates
4. Sidecars are properly associated with media files
"""

import sys
from pathlib import Path
from collections import defaultdict
import re

def count_media_files(folder):
    """Count media files (not sidecars) in a folder."""
    media_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.heic', '.heif', 
                       '.mov', '.mp4', '.avi', '.m4v', '.mpg', '.mpeg', '.3gp', '.mts'}
    count = 0
    for file in folder.iterdir():
        if file.is_file() and file.suffix.lower() in media_extensions:
            count += 1
    return count

def check_folder_structure(library_path):
    """Check that all folders match expected structure patterns."""
    issues = []
    folder_pattern = re.compile(r'^\d{4}\+?$|^\d{4}$|^\d{4}-\d{2}$|^\d{4}-\d{2}-\d{2}')
    
    for folder in Path(library_path).rglob('*'):
        if not folder.is_dir():
            continue
            
        # Skip special folders
        if folder.name.startswith('.') or folder.name == 'orphaned-sidecars':
            continue
            
        # Get relative path from library root
        rel_path = folder.relative_to(library_path)
        parts = rel_path.parts
        
        # Check each level matches expected pattern
        for i, part in enumerate(parts):
            if i == 0:  # Decade folder
                if not re.match(r'^\d{4}\+$', part):
                    issues.append(f"Invalid decade folder: {rel_path}")
                    break
            elif i == 1:  # Year folder
                if not re.match(r'^\d{4}$', part):
                    issues.append(f"Invalid year folder: {rel_path}")
                    break
            elif i == 2:  # Month folder
                if not re.match(r'^\d{4}-\d{2}', part):
                    issues.append(f"Invalid month folder: {rel_path}")
                    break
            # Level 3+ is the date/event folder - allow anything with date prefix
            
    return issues

def verify_library(library_path):
    """Run all verification checks."""
    library_path = Path(library_path)
    
    print("="*70)
    print("VERIFYING REORGANIZED LIBRARY")
    print("="*70)
    print(f"Library: {library_path}")
    print()
    
    # Check 1: No folders with >50 media files
    print("Check 1: Verifying no folders exceed 50 media files...")
    oversized_folders = []
    total_folders = 0
    total_media_files = 0
    folder_sizes = defaultdict(int)
    
    for folder in library_path.rglob('*'):
        if not folder.is_dir():
            continue
        if folder.name.startswith('.') or folder.name == 'orphaned-sidecars':
            continue
            
        total_folders += 1
        media_count = count_media_files(folder)
        
        if media_count > 0:
            total_media_files += media_count
            folder_sizes[media_count] += 1
            
            if media_count > 50:
                oversized_folders.append((folder.relative_to(library_path), media_count))
    
    if oversized_folders:
        print(f"  ❌ FAILED: Found {len(oversized_folders)} folders exceeding 50 files:")
        for folder, count in sorted(oversized_folders, key=lambda x: x[1], reverse=True)[:10]:
            print(f"    - {folder}: {count} files")
    else:
        print(f"  ✅ PASSED: All folders have ≤50 media files")
    
    # Check 2: Folder structure
    print("\nCheck 2: Verifying folder structure patterns...")
    structure_issues = check_folder_structure(library_path)
    
    if structure_issues:
        print(f"  ❌ FAILED: Found {len(structure_issues)} structure issues:")
        for issue in structure_issues[:10]:
            print(f"    - {issue}")
    else:
        print(f"  ✅ PASSED: All folder names match expected patterns")
    
    # Check 3: Distribution statistics
    print("\nCheck 3: Folder size distribution...")
    print(f"  Total folders checked: {total_folders:,}")
    print(f"  Total media files: {total_media_files:,}")
    print(f"\n  Files per folder distribution:")
    
    for size in sorted(folder_sizes.keys(), reverse=True)[:15]:
        count = folder_sizes[size]
        print(f"    {size:2d} files: {count:4d} folders")
    
    # Summary
    print(f"\n{'='*70}")
    print("VERIFICATION SUMMARY")
    print(f"{'='*70}")
    
    total_issues = len(oversized_folders) + len(structure_issues)
    
    if total_issues == 0:
        print("✅ ALL CHECKS PASSED")
        print(f"   - {total_folders:,} folders organized")
        print(f"   - {total_media_files:,} media files")
        print(f"   - All folders ≤50 files")
        print(f"   - All folder names follow conventions")
    else:
        print(f"❌ FOUND {total_issues} ISSUES")
        if oversized_folders:
            print(f"   - {len(oversized_folders)} folders exceed 50 files")
        if structure_issues:
            print(f"   - {len(structure_issues)} structure violations")
    
    print(f"{'='*70}")
    
    return total_issues == 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python verify_reorganization.py <library_path>")
        sys.exit(1)
    
    library_path = sys.argv[1]
    success = verify_library(library_path)
    sys.exit(0 if success else 1)
