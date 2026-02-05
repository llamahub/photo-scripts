#!/usr/bin/env python3
"""Find non-media, non-sidecar files in the photo library."""
import sys
import os
from pathlib import Path
from collections import defaultdict

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.gif', '.bmp', '.tiff', '.tif'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.mpg', '.mpeg'}
SIDECAR_EXTENSIONS = {'.xmp', '.json'}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

base_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/mnt/photo_drive/santee-images')

other_files = defaultdict(list)
extension_counts = defaultdict(int)
folder_other_counts = {}

print("Scanning for non-media, non-sidecar files...")

for root, dirs, files in os.walk(base_path):
    other_count = 0
    for f in files:
        ext = Path(f).suffix.lower()
        
        # Skip known extensions
        if ext in MEDIA_EXTENSIONS or ext in SIDECAR_EXTENSIONS:
            continue
        
        # Skip .bak files (disabled sidecars)
        if f.endswith('.bak'):
            continue
        
        # This is an "other" file
        file_path = Path(root) / f
        other_files[ext].append(str(file_path.relative_to(base_path)))
        extension_counts[ext] += 1
        other_count += 1
    
    if other_count > 0:
        folder_other_counts[root] = other_count

print(f"\n=== SUMMARY ===")
print(f"Total non-media, non-sidecar files: {sum(extension_counts.values())}")
print(f"Folders with such files: {len(folder_other_counts)}")

print(f"\n=== FILE TYPES FOUND ===")
for ext in sorted(extension_counts.keys(), key=lambda x: extension_counts[x], reverse=True):
    count = extension_counts[ext]
    print(f"  {ext if ext else '(no extension)'}: {count} files")

print(f"\n=== FOLDERS WITH > 10 NON-MEDIA FILES ===")
large_folders = {f: c for f, c in folder_other_counts.items() if c > 10}
if large_folders:
    for folder in sorted(large_folders.keys(), key=lambda x: folder_other_counts[x], reverse=True)[:20]:
        rel = Path(folder).relative_to(base_path)
        print(f"  {rel}: {folder_other_counts[folder]} files")
else:
    print("  None")

# Show some examples of each type
print(f"\n=== EXAMPLE FILES (first 3 of each type) ===")
for ext in sorted(extension_counts.keys(), key=lambda x: extension_counts[x], reverse=True)[:10]:
    print(f"\n{ext if ext else '(no extension)'} ({extension_counts[ext]} total):")
    for path in other_files[ext][:3]:
        print(f"  {path}")
    if len(other_files[ext]) > 3:
        print(f"  ... and {len(other_files[ext]) - 3} more")
