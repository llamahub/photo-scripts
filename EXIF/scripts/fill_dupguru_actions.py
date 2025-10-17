#!/usr/bin/env python3
"""
Fill in missing Action/Comments columns in dupGuru CSV file based on user's decision patterns.

Decision Rules:
1. Prefer older files if they're in valid date folders (manually corrected dates)
2. Prefer organized format filenames (YYYY-MM-DD_HHMM_PERSON_DIMxDIM_original.ext)
3. Avoid invalid folder structures (0000-00, NPTSI-Z, "Photos from YYYY", "New Folder")
4. For scanned photos: prefer original scans in _Scans folders over later copies
5. For size differences >50KB: prefer larger file (better quality)
6. For size differences ≤50KB: prefer organized format (just metadata differences)
"""

import csv
import re
import sys
from pathlib import Path
from datetime import datetime

def extract_date_from_filename(filename):
    """Extract date from filename in YYYY-MM-DD format."""
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', filename)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None
    return None

def extract_date_from_folder(folder_path):
    """Extract date from folder path and determine if it's valid."""
    # Look for YYYY-MM or YYYY-MM-DD patterns in folder
    folder_parts = folder_path.replace('\\', '/').split('/')
    
    for part in folder_parts:
        # Check for YYYY-MM-DD pattern
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', part)
        if match:
            try:
                date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                return date, True
            except ValueError:
                continue
        
        # Check for YYYY-MM pattern
        match = re.search(r'(\d{4})-(\d{2})', part)
        if match:
            try:
                date = datetime(int(match.group(1)), int(match.group(2)), 1)
                return date, True
            except ValueError:
                continue
    
    return None, False

def is_organized_filename(filename):
    """Check if filename follows organize.py target format."""
    pattern = r'\d{4}-\d{2}-\d{2}_\d{4}_[A-Z]+_\d+x\d+_.*\.(jpg|jpeg|png|gif)$'
    return bool(re.match(pattern, filename, re.IGNORECASE))

def is_invalid_folder(folder_path):
    """Check if folder path contains invalid patterns."""
    folder_lower = folder_path.lower()
    invalid_patterns = [
        '0000-00',
        'nptsi',
        'new folder',
        'photos from 20',
    ]
    return any(pattern in folder_lower for pattern in invalid_patterns)

def is_scanned_file(folder_path, filename):
    """Check if this is a scanned file in a _Scans folder."""
    return '_scans' in folder_path.lower()

def analyze_duplicate_pair(file1, file2):
    """Analyze a pair of duplicate files and determine which to keep."""
    
    # Extract key information
    f1_date = extract_date_from_filename(file1['Filename'])
    f2_date = extract_date_from_filename(file2['Filename'])
    
    f1_folder_date, f1_valid_folder = extract_date_from_folder(file1['Folder'])
    f2_folder_date, f2_valid_folder = extract_date_from_folder(file2['Folder'])
    
    f1_organized = is_organized_filename(file1['Filename'])
    f2_organized = is_organized_filename(file2['Filename'])
    
    f1_invalid_folder = is_invalid_folder(file1['Folder'])
    f2_invalid_folder = is_invalid_folder(file2['Folder'])
    
    f1_scanned = is_scanned_file(file1['Folder'], file1['Filename'])
    f2_scanned = is_scanned_file(file2['Folder'], file2['Filename'])
    
    f1_size = int(file1['Size (KB)'])
    f2_size = int(file2['Size (KB)'])
    size_diff = abs(f1_size - f2_size)
    
    # Decision logic
    decisions = []
    
    # Rule 1: Invalid folder structures
    if f1_invalid_folder and not f2_invalid_folder:
        decisions.append(('file2', 'File 1 in invalid folder structure'))
    elif f2_invalid_folder and not f1_invalid_folder:
        decisions.append(('file1', 'File 2 in invalid folder structure'))
    
    # Rule 2: Prefer older files in valid folders (manually corrected dates)
    if f1_date and f2_date and f1_valid_folder and f2_valid_folder:
        if f1_date < f2_date:
            decisions.append(('file1', 'Older file with valid folder structure'))
        elif f2_date < f1_date:
            decisions.append(('file2', 'Older file with valid folder structure'))
    
    # Rule 3: Scanned photos - prefer original scans
    if f1_scanned and not f2_scanned:
        decisions.append(('file1', 'Original scanned file'))
    elif f2_scanned and not f1_scanned:
        decisions.append(('file2', 'Original scanned file'))
    
    # Rule 4: Organized filename format
    if f1_organized and not f2_organized:
        decisions.append(('file1', 'Organized filename format'))
    elif f2_organized and not f1_organized:
        decisions.append(('file2', 'Organized filename format'))
    
    # Rule 5: File size considerations
    if size_diff > 50:  # Significant quality difference
        if f1_size > f2_size:
            decisions.append(('file1', f'Larger file size ({f1_size}KB vs {f2_size}KB, {size_diff}KB difference)'))
        else:
            decisions.append(('file2', f'Larger file size ({f2_size}KB vs {f1_size}KB, {size_diff}KB difference)'))
    
    # Rule 6: Valid folder structure as tiebreaker
    if f1_valid_folder and not f2_valid_folder:
        decisions.append(('file1', 'Valid folder date structure'))
    elif f2_valid_folder and not f1_valid_folder:
        decisions.append(('file2', 'Valid folder date structure'))
    
    # Return the most important decision
    if decisions:
        keep_file, reason = decisions[0]  # First decision has highest priority
        if keep_file == 'file1':
            return 'Keep', 'Delete', reason, f'Not keeping: {reason.lower()}'
        else:
            return 'Delete', 'Keep', f'Not keeping: {reason.lower()}', reason
    
    # If no clear decision, need manual review
    return '', '', 'Manual review needed', 'Manual review needed'

def main():
    input_file = '.log/dupGuru_Results_2025-10-17_actions.csv'
    output_file = '.log/dupGuru_Results_2025-10-17_actions_filled.csv'
    
    if not Path(input_file).exists():
        print(f"Input file {input_file} not found!")
        return 1
    
    filled_count = 0
    total_pairs = 0
    
    with open(input_file, 'r', encoding='utf-8-sig') as infile, \
         open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        current_group = None
        group_files = []
        
        for row in reader:
            group_id = row['Group ID']
            
            if group_id != current_group:
                # Process previous group
                if len(group_files) == 2:
                    total_pairs += 1
                    file1, file2 = group_files
                    
                    # Only fill if both Action fields are empty
                    if not file1['Action'].strip() and not file2['Action'].strip():
                        action1, action2, comment1, comment2 = analyze_duplicate_pair(file1, file2)
                        file1['Action'] = action1
                        file1['Comments'] = comment1
                        file2['Action'] = action2
                        file2['Comments'] = comment2
                        filled_count += 1
                    
                    # Write both files
                    writer.writerow(file1)
                    writer.writerow(file2)
                
                elif len(group_files) == 1:
                    # Single file, just write it
                    writer.writerow(group_files[0])
                
                current_group = group_id
                group_files = [row]
            else:
                group_files.append(row)
        
        # Handle last group
        if len(group_files) == 2:
            total_pairs += 1
            file1, file2 = group_files
            
            if not file1['Action'].strip() and not file2['Action'].strip():
                action1, action2, comment1, comment2 = analyze_duplicate_pair(file1, file2)
                file1['Action'] = action1
                file1['Comments'] = comment1
                file2['Action'] = action2
                file2['Comments'] = comment2
                filled_count += 1
            
            writer.writerow(file1)
            writer.writerow(file2)
        elif len(group_files) == 1:
            writer.writerow(group_files[0])
    
    print(f"Processing complete!")
    print(f"Total duplicate pairs: {total_pairs}")
    print(f"Pairs with actions filled: {filled_count}")
    print(f"Output saved to: {output_file}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())