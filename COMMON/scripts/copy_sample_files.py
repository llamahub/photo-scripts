#!/usr/bin/env python3
"""
Copy sample files from reorganized library to test directory.
Maintains the same folder structure.
"""

import sys
from pathlib import Path
import shutil

def copy_sample_files(consolidated_list_file, source_root, target_root):
    """Copy files from source to target maintaining folder structure."""
    
    source_root = Path(source_root)
    target_root = Path(target_root)
    
    # Create target root if it doesn't exist
    target_root.mkdir(parents=True, exist_ok=True)
    
    # Parse the consolidated list
    files_to_copy = []
    
    with open(consolidated_list_file, 'r') as f:
        for line in f:
            stripped = line.strip()
            # Skip comments, empty lines, and markers
            if not stripped or stripped.startswith('#') or stripped.startswith('X'):
                continue
            
            # Lines starting with ! are multiple matches
            if stripped.startswith('!'):
                continue
                
            # Lines that start with " -> " or contain it contain the new relative path
            if stripped.startswith('->') or ' -> ' in line:
                # Extract path after the arrow
                if '->' in stripped:
                    rel_path = stripped.split('->', 1)[1].strip()
                    # Remove any notes in parentheses
                    if ' (' in rel_path:
                        rel_path = rel_path[:rel_path.index(' (')]
                    files_to_copy.append(rel_path.strip())
    
    print(f"Found {len(files_to_copy)} files to copy")
    print(f"Source: {source_root}")
    print(f"Target: {target_root}")
    print()
    
    copied = 0
    errors = []
    
    for i, rel_path in enumerate(files_to_copy):
        if (i + 1) % 50 == 0:
            print(f"  Copied {i + 1}/{len(files_to_copy)}...")
        
        source_file = source_root / rel_path
        target_file = target_root / rel_path
        
        # Check if source exists
        if not source_file.exists():
            errors.append(f"Source not found: {rel_path}")
            continue
        
        # Create target directory
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        try:
            shutil.copy2(source_file, target_file)
            copied += 1
        except Exception as e:
            errors.append(f"Error copying {rel_path}: {e}")
    
    # Summary
    print(f"\n{'='*70}")
    print("COPY SUMMARY")
    print(f"{'='*70}")
    print(f"Files to copy:      {len(files_to_copy):>6}")
    print(f"Successfully copied: {copied:>6}")
    print(f"Errors:             {len(errors):>6}")
    
    if errors:
        print(f"\nErrors:")
        for error in errors[:10]:
            print(f"  - {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
    
    print(f"{'='*70}")
    print(f"\nTarget directory: {target_root}")
    
    return copied, errors

if __name__ == "__main__":
    consolidated_list = "/mnt/photo_drive/photo-scripts/.github/prompts/consolidated_file_locations.txt"
    source_root = "/mnt/photo_drive/santee-images"
    target_root = "/mnt/photo_drive/santee-samples"
    
    copied, errors = copy_sample_files(consolidated_list, source_root, target_root)
    sys.exit(0 if len(errors) == 0 else 1)
