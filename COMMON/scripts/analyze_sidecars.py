#!/usr/bin/env python3
"""
Analyze sidecar file distribution in photo library.
Identifies images with multiple sidecar files (.xmp and .json).
"""

import os
import sys
from pathlib import Path
from collections import defaultdict

# Image extensions to check
IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
    '.heic', '.heif', '.webp', '.cr2', '.nef', '.arw', '.dng', '.raw'
}

# Sidecar extensions
SIDECAR_EXTENSIONS = {'.xmp', '.json'}


def analyze_sidecars(library_path: str):
    """Analyze sidecar file distribution."""
    library = Path(library_path)
    
    if not library.exists():
        print(f"Error: Library path does not exist: {library_path}")
        sys.exit(1)
    
    # Track statistics
    stats = {
        'total_images': 0,
        'images_with_xmp': 0,
        'images_with_json': 0,
        'images_with_both': 0,
        'images_with_neither': 0,
        'images_with_multiple_of_same_type': 0
    }
    
    examples_both = []
    examples_multiple = []
    
    print(f"Scanning library: {library_path}")
    print("This may take a few minutes...\n")
    
    # Walk through all files
    for root, dirs, files in os.walk(library):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        # Group files by base name
        file_groups = defaultdict(list)
        for filename in files:
            # Skip hidden files
            if filename.startswith('.'):
                continue
            
            path = Path(root) / filename
            ext = path.suffix.lower()
            
            # Identify base name
            if ext in SIDECAR_EXTENSIONS:
                # Sidecar file: base name is filename without sidecar extension
                base_name = path.stem
                file_groups[base_name].append(('sidecar', ext, filename))
            elif ext in IMAGE_EXTENSIONS:
                # Image file: base name is the filename without extension
                base_name = path.stem
                file_groups[base_name].append(('image', ext, filename))
        
        # Analyze each group
        for base_name, group_files in file_groups.items():
            image_files = [f for f in group_files if f[0] == 'image']
            sidecar_files = [f for f in group_files if f[0] == 'sidecar']
            
            if not image_files:
                continue  # Only process if there's an image file
            
            stats['total_images'] += len(image_files)
            
            # Check for sidecars
            has_xmp = any(f[1] == '.xmp' for f in sidecar_files)
            has_json = any(f[1] == '.json' for f in sidecar_files)
            
            if has_xmp:
                stats['images_with_xmp'] += len(image_files)
            if has_json:
                stats['images_with_json'] += len(image_files)
            if has_xmp and has_json:
                stats['images_with_both'] += len(image_files)
                if len(examples_both) < 10:
                    rel_path = Path(root).relative_to(library)
                    examples_both.append(f"{rel_path}/{image_files[0][2]}")
            if not has_xmp and not has_json:
                stats['images_with_neither'] += len(image_files)
            
            # Check for multiple sidecars of the same type
            xmp_count = sum(1 for f in sidecar_files if f[1] == '.xmp')
            json_count = sum(1 for f in sidecar_files if f[1] == '.json')
            
            if xmp_count > 1 or json_count > 1:
                stats['images_with_multiple_of_same_type'] += len(image_files)
                if len(examples_multiple) < 10:
                    rel_path = Path(root).relative_to(library)
                    examples_multiple.append({
                        'folder': str(rel_path),
                        'image': image_files[0][2],
                        'xmp_count': xmp_count,
                        'json_count': json_count,
                        'files': [f[2] for f in group_files]
                    })
    
    # Print results
    print("="*70)
    print("SIDECAR FILE ANALYSIS")
    print("="*70)
    print(f"\nTotal image files: {stats['total_images']:,}")
    print(f"\nSidecar Distribution:")
    print(f"  Images with .xmp sidecar:    {stats['images_with_xmp']:>6,} ({100*stats['images_with_xmp']/stats['total_images']:5.1f}%)")
    print(f"  Images with .json sidecar:   {stats['images_with_json']:>6,} ({100*stats['images_with_json']/stats['total_images']:5.1f}%)")
    print(f"  Images with BOTH sidecars:   {stats['images_with_both']:>6,} ({100*stats['images_with_both']/stats['total_images']:5.1f}%)")
    print(f"  Images with NO sidecars:     {stats['images_with_neither']:>6,} ({100*stats['images_with_neither']/stats['total_images']:5.1f}%)")
    
    if stats['images_with_multiple_of_same_type'] > 0:
        print(f"\n⚠️  Images with multiple sidecars of same type: {stats['images_with_multiple_of_same_type']:,}")
    
    # Show examples
    if examples_both:
        print(f"\nExamples of images with BOTH .xmp and .json sidecars (showing {len(examples_both)}):")
        for example in examples_both[:10]:
            print(f"  • {example}")
    
    if examples_multiple:
        print(f"\n⚠️  Examples of images with multiple sidecars of same type:")
        for example in examples_multiple[:5]:
            print(f"\n  Folder: {example['folder']}")
            print(f"  Image: {example['image']}")
            print(f"  XMP count: {example['xmp_count']}, JSON count: {example['json_count']}")
            print(f"  All files: {', '.join(example['files'])}")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: analyze_sidecars.py <library_path>")
        sys.exit(1)
    
    analyze_sidecars(sys.argv[1])
