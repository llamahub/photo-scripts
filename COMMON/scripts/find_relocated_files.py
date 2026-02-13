#!/usr/bin/env python3
"""
Find files from old structure in the new reorganized structure.
Takes lists of files from the old structure and locates them in the new structure.
"""

import sys
from pathlib import Path
from collections import defaultdict

def find_file_in_new_structure(filename, library_path):
    """Find a file by name in the new structure."""
    library_path = Path(library_path)
    
    # Search for the file
    matches = list(library_path.rglob(filename))
    
    # Filter out orphaned-sidecars folder
    matches = [m for m in matches if 'orphaned-sidecars' not in str(m)]
    
    return matches

def process_file_lists(input_files, library_path, output_file):
    """Process input file lists and create consolidated output."""
    
    results = []
    not_found = []
    multiple_matches = []
    
    # Read all input files
    all_old_paths = []
    for input_file in input_files:
        with open(input_file, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                all_old_paths.append(line)
    
    print(f"Processing {len(all_old_paths)} files...")
    
    for i, old_path in enumerate(all_old_paths):
        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(all_old_paths)}...")
        
        # Extract just the filename
        filename = Path(old_path).name
        
        # Find in new structure
        matches = find_file_in_new_structure(filename, library_path)
        
        if len(matches) == 0:
            not_found.append((old_path, filename))
        elif len(matches) == 1:
            # Get relative path from library root
            rel_path = matches[0].relative_to(library_path)
            results.append({
                'old_path': old_path,
                'new_path': str(rel_path),
                'full_path': str(matches[0])
            })
        else:
            # Multiple matches - include all
            multiple_matches.append((old_path, [str(m.relative_to(library_path)) for m in matches]))
            # Use first match for results
            rel_path = matches[0].relative_to(library_path)
            results.append({
                'old_path': old_path,
                'new_path': str(rel_path),
                'full_path': str(matches[0]),
                'note': f'Multiple matches ({len(matches)})'
            })
    
    # Write output file
    with open(output_file, 'w') as f:
        f.write("# Consolidated File Location List\n")
        f.write(f"# Generated after library reorganization on {Path.cwd()}\n")
        f.write(f"# Total files: {len(all_old_paths)}\n")
        f.write(f"# Found: {len(results)}\n")
        f.write(f"# Not found: {len(not_found)}\n")
        f.write(f"# Multiple matches: {len(multiple_matches)}\n")
        f.write("\n")
        
        f.write("# Format: OLD_PATH -> NEW_PATH\n")
        f.write("# Lines starting with ! indicate multiple matches\n")
        f.write("# Lines starting with X indicate file not found\n")
        f.write("\n")
        
        # Write successful matches
        for item in results:
            if 'note' in item:
                f.write(f"! {item['old_path']}\n")
                f.write(f"  -> {item['new_path']} ({item['note']})\n")
            else:
                f.write(f"{item['old_path']}\n")
                f.write(f"  -> {item['new_path']}\n")
        
        # Write not found
        if not_found:
            f.write("\n# FILES NOT FOUND\n")
            for old_path, filename in not_found:
                f.write(f"X {old_path}\n")
        
        # Write multiple matches detail
        if multiple_matches:
            f.write("\n# MULTIPLE MATCHES DETAIL\n")
            for old_path, matches in multiple_matches:
                f.write(f"\n{old_path}\n")
                for match in matches:
                    f.write(f"  - {match}\n")
    
    # Print summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total files processed:  {len(all_old_paths):>6}")
    print(f"Found (single match):   {len(results) - len(multiple_matches):>6}")
    print(f"Found (multiple):       {len(multiple_matches):>6}")
    print(f"Not found:              {len(not_found):>6}")
    print(f"\nOutput written to: {output_file}")
    print(f"{'='*70}")

if __name__ == "__main__":
    library_path = "/mnt/photo_drive/santee-images"
    
    input_files = [
        "/mnt/photo_drive/photo-scripts/IMMICH/.github/prompts/sample_file_list.txt",
        "/mnt/photo_drive/photo-scripts/.github/prompts/photo_sample_list.txt"
    ]
    
    output_file = "/mnt/photo_drive/photo-scripts/.github/prompts/consolidated_file_locations.txt"
    
    process_file_lists(input_files, library_path, output_file)
