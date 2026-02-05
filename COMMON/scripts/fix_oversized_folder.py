#!/usr/bin/env python3
"""Fix the one oversized folder that was missed."""

import sys
from pathlib import Path
import shutil
from collections import defaultdict

def split_folder(folder_path, max_files=50):
    """Split a folder with >50 media files into date-based subfolders."""
    folder_path = Path(folder_path)
    
    # Get all files grouped by date
    media_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.heic', '.heif', 
                       '.mov', '.mp4', '.avi', '.m4v', '.mpg', '.mpeg', '.3gp', '.mts'}
    
    files_by_date = defaultdict(list)
    
    for file in sorted(folder_path.iterdir()):
        if not file.is_file():
            continue
        
        # Extract date from filename (format: YYYY-MM-DD)
        name = file.name
        if len(name) >= 10 and name[4] == '-' and name[7] == '-':
            date = name[:10]
            files_by_date[date].append(file)
        else:
            files_by_date['unknown'].append(file)
    
    print(f"Found {len(files_by_date)} different dates in {folder_path.name}")
    
    # Group dates into chunks of max_files
    all_files = []
    for date in sorted(files_by_date.keys()):
        all_files.extend(files_by_date[date])
    
    # Calculate how many splits we need
    num_splits = (len(all_files) + max_files - 1) // max_files
    
    print(f"Total files: {len(all_files)}, will create {num_splits} folders")
    
    # Create subfolders and move files
    for i in range(num_splits):
        start_idx = i * max_files
        end_idx = min(start_idx + max_files, len(all_files))
        chunk_files = all_files[start_idx:end_idx]
        
        # Create subfolder with sequence number
        subfolder_name = f"{folder_path.name}_{i+1:02d}"
        subfolder = folder_path.parent / subfolder_name
        subfolder.mkdir(exist_ok=True)
        
        print(f"\n  Creating {subfolder_name} with {len(chunk_files)} files...")
        
        # Move files
        for file in chunk_files:
            dest = subfolder / file.name
            shutil.move(str(file), str(dest))
            print(f"    Moved: {file.name}")
    
    # Remove original folder if empty
    remaining = list(folder_path.iterdir())
    if not remaining:
        folder_path.rmdir()
        print(f"\n  Removed empty folder: {folder_path.name}")
    else:
        print(f"\n  WARNING: {len(remaining)} files remain in original folder")

if __name__ == "__main__":
    folder = "/mnt/photo_drive/santee-images/2020+/2025/2025-05/2025-05-31"
    split_folder(folder)
