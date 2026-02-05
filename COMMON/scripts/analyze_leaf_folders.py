#!/usr/bin/env python3
"""Analyze folder structure - leaf vs non-leaf folders."""
import sys
import os
from pathlib import Path

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.gif', '.bmp', '.tiff', '.tif'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.mpg', '.mpeg'}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

base_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/mnt/photo_drive/santee-images')

folder_info = {}

# First pass: collect all folders with files and their subdirectories
for root, dirs, files in os.walk(base_path):
    media_files = [f for f in files if Path(f).suffix.lower() in MEDIA_EXTENSIONS]
    if media_files:
        folder_info[root] = {
            'file_count': len(media_files),
            'has_subdirs': len(dirs) > 0,
            'is_leaf': len(dirs) == 0
        }

# Analyze folders with > 50 files
over_50 = {f: info for f, info in folder_info.items() if info['file_count'] > 50}

leaf_over_50 = [f for f, info in over_50.items() if info['is_leaf']]
non_leaf_over_50 = [f for f, info in over_50.items() if not info['is_leaf']]

print(f"=== FOLDERS WITH > 50 FILES ===")
print(f"Total: {len(over_50)}")
print(f"Leaf nodes (no subfolders): {len(leaf_over_50)}")
print(f"Non-leaf (has subfolders): {len(non_leaf_over_50)}")

if len(non_leaf_over_50) <= 30:
    print(f"\nNon-leaf folders with > 50 files:")
    for folder in sorted(non_leaf_over_50):
        rel = Path(folder).relative_to(base_path)
        print(f"  {rel}: {folder_info[folder]['file_count']} files")

# Same for > 100
over_100 = {f: info for f, info in folder_info.items() if info['file_count'] > 100}
leaf_over_100 = [f for f, info in over_100.items() if info['is_leaf']]
non_leaf_over_100 = [f for f, info in over_100.items() if not info['is_leaf']]

print(f"\n=== FOLDERS WITH > 100 FILES ===")
print(f"Total: {len(over_100)}")
print(f"Leaf nodes (no subfolders): {len(leaf_over_100)}")
print(f"Non-leaf (has subfolders): {len(non_leaf_over_100)}")

if len(non_leaf_over_100) <= 20:
    print(f"\nNon-leaf folders with > 100 files:")
    for folder in sorted(non_leaf_over_100):
        rel = Path(folder).relative_to(base_path)
        print(f"  {rel}: {folder_info[folder]['file_count']} files")
