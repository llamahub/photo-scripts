#!/usr/bin/env python3
"""
Analyze orphaned sidecar files to check if they're due to image file renaming.
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
import re

# Image extensions to check
IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
    '.heic', '.heif', '.webp', '.cr2', '.nef', '.arw', '.dng', '.raw'
}

# Sidecar extensions
SIDECAR_EXTENSIONS = {'.xmp', '.json'}


def extract_base_name_variations(filename):
    """
    Extract possible base name variations from a filename.
    Returns a list of possible original names if the file appears to be renamed.
    """
    stem = Path(filename).stem
    variations = [stem]
    
    # Check if filename contains dimensions pattern like "IMG_1234-1920x1080"
    # Common patterns: IMG_1234-WIDTHxHEIGHT, IMG_1234_WIDTHxHEIGHT, etc.
    dimension_patterns = [
        r'^(.+?)[-_](\d{3,5})x(\d{3,5})$',  # name-1920x1080 or name_1920x1080
        r'^(.+?)[-_]\d+x\d+[-_](.+)$',       # name-1920x1080-suffix
    ]
    
    for pattern in dimension_patterns:
        match = re.match(pattern, stem)
        if match:
            # Extract the original name without dimensions
            original = match.group(1)
            variations.append(original)
    
    return variations


def analyze_orphaned_sidecars(library_path: str):
    """Analyze orphaned sidecar files."""
    library = Path(library_path)
    
    if not library.exists():
        print(f"Error: Library path does not exist: {library_path}")
        sys.exit(1)
    
    # Track statistics
    stats = {
        'total_xmp': 0,
        'total_json': 0,
        'orphaned_xmp': 0,
        'orphaned_json': 0,
        'matched_xmp': 0,
        'matched_json': 0,
    }
    
    orphaned_examples = []
    dimension_pattern_examples = []
    
    print(f"Scanning library: {library_path}")
    print("This may take a few minutes...\n")
    
    # Walk through all directories
    for root, dirs, files in os.walk(library):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        if not files:
            continue
        
        # Collect all files in this directory
        image_files = []
        sidecar_files = []
        
        for filename in files:
            if filename.startswith('.'):
                continue
            
            ext = Path(filename).suffix.lower()
            
            if ext in IMAGE_EXTENSIONS:
                image_files.append(filename)
            elif ext in SIDECAR_EXTENSIONS:
                sidecar_files.append((filename, ext))
        
        if not sidecar_files:
            continue
        
        # Create a set of image base names and their variations
        image_base_names = set()
        image_name_to_variations = {}
        
        for img_file in image_files:
            variations = extract_base_name_variations(img_file)
            for var in variations:
                image_base_names.add(var.lower())
            image_name_to_variations[img_file] = variations
        
        # Check each sidecar file
        for sidecar_file, sidecar_ext in sidecar_files:
            if sidecar_ext == '.xmp':
                stats['total_xmp'] += 1
            else:
                stats['total_json'] += 1
            
            # Get base name of sidecar (without .xmp or .json)
            sidecar_base = Path(sidecar_file).stem
            
            # Check if there's a matching image
            matched = False
            
            # Direct match
            if sidecar_base.lower() in image_base_names:
                matched = True
            else:
                # Check if any image has this as an original name variation
                for img_file, variations in image_name_to_variations.items():
                    if sidecar_base.lower() in [v.lower() for v in variations]:
                        matched = True
                        break
            
            if matched:
                if sidecar_ext == '.xmp':
                    stats['matched_xmp'] += 1
                else:
                    stats['matched_json'] += 1
            else:
                # Orphaned sidecar
                if sidecar_ext == '.xmp':
                    stats['orphaned_xmp'] += 1
                else:
                    stats['orphaned_json'] += 1
                
                # Check if this looks like an original filename that might have been renamed
                has_dimension_pattern = False
                potential_match = None
                
                for img_file in image_files:
                    img_stem = Path(img_file).stem
                    # Check if image has dimensions and sidecar base might be original
                    if re.search(r'[-_]\d{3,5}x\d{3,5}', img_stem):
                        has_dimension_pattern = True
                        # See if sidecar base is a substring or close match
                        if sidecar_base.lower() in img_stem.lower():
                            potential_match = img_file
                            break
                
                if len(orphaned_examples) < 20:
                    rel_path = Path(root).relative_to(library)
                    example = {
                        'folder': str(rel_path),
                        'sidecar': sidecar_file,
                        'type': sidecar_ext,
                        'has_dimension_images': has_dimension_pattern,
                        'potential_match': potential_match,
                        'sample_images': image_files[:3] if image_files else []
                    }
                    orphaned_examples.append(example)
                    
                    if has_dimension_pattern and potential_match:
                        dimension_pattern_examples.append(example)
    
    # Print results
    print("="*70)
    print("ORPHANED SIDECAR ANALYSIS")
    print("="*70)
    
    print(f"\n.XMP Files:")
    print(f"  Total:      {stats['total_xmp']:>6,}")
    print(f"  Matched:    {stats['matched_xmp']:>6,} ({100*stats['matched_xmp']/stats['total_xmp'] if stats['total_xmp'] > 0 else 0:5.1f}%)")
    print(f"  Orphaned:   {stats['orphaned_xmp']:>6,} ({100*stats['orphaned_xmp']/stats['total_xmp'] if stats['total_xmp'] > 0 else 0:5.1f}%)")
    
    print(f"\n.JSON Files:")
    print(f"  Total:      {stats['total_json']:>6,}")
    print(f"  Matched:    {stats['matched_json']:>6,} ({100*stats['matched_json']/stats['total_json'] if stats['total_json'] > 0 else 0:5.1f}%)")
    print(f"  Orphaned:   {stats['orphaned_json']:>6,} ({100*stats['orphaned_json']/stats['total_json'] if stats['total_json'] > 0 else 0:5.1f}%)")
    
    # Show examples
    if dimension_pattern_examples:
        print(f"\n{'='*70}")
        print(f"POTENTIAL RENAMING PATTERNS (showing up to 10):")
        print(f"{'='*70}")
        for example in dimension_pattern_examples[:10]:
            print(f"\nFolder: {example['folder']}")
            print(f"  Orphaned sidecar: {example['sidecar']}")
            if example['potential_match']:
                print(f"  Potential match:  {example['potential_match']}")
            print(f"  Sample images in folder:")
            for img in example['sample_images']:
                print(f"    • {img}")
    
    if orphaned_examples and not dimension_pattern_examples:
        print(f"\n{'='*70}")
        print(f"EXAMPLES OF ORPHANED SIDECARS (showing up to 10):")
        print(f"{'='*70}")
        for example in orphaned_examples[:10]:
            print(f"\nFolder: {example['folder']}")
            print(f"  Orphaned sidecar: {example['sidecar']}")
            print(f"  Has dimension-pattern images: {example['has_dimension_images']}")
            if example['sample_images']:
                print(f"  Sample images in folder:")
                for img in example['sample_images']:
                    print(f"    • {img}")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: analyze_orphaned_sidecars.py <library_path>")
        sys.exit(1)
    
    analyze_orphaned_sidecars(sys.argv[1])
