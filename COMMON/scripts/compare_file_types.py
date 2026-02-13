#!/usr/bin/env python3
"""
Compare file types in main library vs sample library.
Identifies any file types not represented in the sample set.
"""

import sys
from pathlib import Path
from collections import defaultdict

def scan_file_types(directory):
    """Scan directory and return dictionary of extensions and their counts."""
    directory = Path(directory)
    extensions = defaultdict(int)
    
    for file_path in directory.rglob('*'):
        if file_path.is_file():
            # Skip hidden files and special folders
            if any(part.startswith('.') for part in file_path.parts):
                continue
            if 'orphaned-sidecars' in str(file_path):
                continue
                
            ext = file_path.suffix.lower()
            if ext:  # Only count files with extensions
                extensions[ext] += 1
    
    return extensions

def compare_libraries(main_library, sample_library):
    """Compare file types between main and sample libraries."""
    
    print("Scanning main library...")
    main_types = scan_file_types(main_library)
    
    print("Scanning sample library...")
    sample_types = scan_file_types(sample_library)
    
    print(f"\n{'='*70}")
    print("FILE TYPE COMPARISON")
    print(f"{'='*70}")
    
    # Calculate totals
    main_total = sum(main_types.values())
    sample_total = sum(sample_types.values())
    
    print(f"\nMain library:   {main_total:>8,} files with {len(main_types):>3} different extensions")
    print(f"Sample library: {sample_total:>8,} files with {len(sample_types):>3} different extensions")
    
    # Find missing types
    missing_types = set(main_types.keys()) - set(sample_types.keys())
    
    if missing_types:
        print(f"\n{'='*70}")
        print(f"MISSING FILE TYPES IN SAMPLES ({len(missing_types)} types)")
        print(f"{'='*70}")
        
        # Sort by count in main library
        missing_sorted = sorted(missing_types, 
                               key=lambda x: main_types[x], 
                               reverse=True)
        
        for ext in missing_sorted:
            count = main_types[ext]
            print(f"  {ext:15s} {count:>8,} files in main library")
        
        # Find example files for each missing type
        print(f"\n{'='*70}")
        print("EXAMPLE FILES FOR MISSING TYPES")
        print(f"{'='*70}")
        
        main_path = Path(main_library)
        for ext in missing_sorted[:10]:  # Show examples for top 10
            print(f"\n{ext} ({main_types[ext]:,} files):")
            examples = list(main_path.rglob(f'*{ext}'))
            # Filter out orphaned-sidecars
            examples = [e for e in examples if 'orphaned-sidecars' not in str(e)][:3]
            for example in examples:
                rel_path = example.relative_to(main_path)
                print(f"  - {rel_path}")
    else:
        print(f"\n✅ All file types from main library are represented in samples!")
    
    # Show common types distribution
    print(f"\n{'='*70}")
    print("FILE TYPES IN BOTH LIBRARIES")
    print(f"{'='*70}")
    print(f"{'Extension':<15} {'Main Count':>12} {'Sample Count':>12}")
    print(f"{'-'*15} {'-'*12} {'-'*12}")
    
    common_types = sorted(set(main_types.keys()) & set(sample_types.keys()),
                         key=lambda x: main_types[x], reverse=True)
    
    for ext in common_types[:15]:  # Top 15
        main_count = main_types[ext]
        sample_count = sample_types[ext]
        print(f"{ext:<15} {main_count:>12,} {sample_count:>12,}")
    
    if len(common_types) > 15:
        print(f"... and {len(common_types) - 15} more")
    
    print(f"{'='*70}")

if __name__ == "__main__":
    main_library = "/mnt/photo_drive/santee-images"
    sample_library = "/mnt/photo_drive/santee-samples"
    
    compare_libraries(main_library, sample_library)
