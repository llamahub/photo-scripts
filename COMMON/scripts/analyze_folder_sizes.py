#!/usr/bin/env python3
"""Count folders by size thresholds."""
import sys
import os
from pathlib import Path
from collections import defaultdict

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.gif', '.bmp', '.tiff', '.tif'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.mpg', '.mpeg'}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

base_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/mnt/photo_drive/santee-images')

folder_counts = {}

for root, dirs, files in os.walk(base_path):
    media_files = [f for f in files if Path(f).suffix.lower() in MEDIA_EXTENSIONS]
    if media_files:
        folder_counts[root] = len(media_files)

over_50 = [f for f, c in folder_counts.items() if c > 50]
over_100 = [f for f, c in folder_counts.items() if c > 100]

print(f"Total folders with media files: {len(folder_counts)}")
print(f"Folders with > 50 files: {len(over_50)}")
print(f"Folders with > 100 files: {len(over_100)}")

if len(over_100) <= 20:
    print("\nFolders with > 100 files:")
    for folder in sorted(over_100):
        rel = Path(folder).relative_to(base_path)
        print(f"  {rel}: {folder_counts[folder]} files")
