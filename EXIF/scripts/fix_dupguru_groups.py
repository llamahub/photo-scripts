#!/usr/bin/env python3
"""
Fix dupGuru CSV to ensure every group has at least one "Keep" decision.
"""

import csv
from collections import defaultdict

def fix_duplicate_groups():
    input_file = '.log/dupGuru_Results_2025-10-17_actions_filled.csv'
    output_file = '.log/dupGuru_Results_2025-10-17_actions_fixed.csv'
    
    # Read all data
    all_rows = []
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            all_rows.append(row)
    
    # Group by Group ID
    groups = defaultdict(list)
    for row in all_rows:
        groups[row['Group ID']].append(row)
    
    fixed_groups = 0
    
    # Fix each group
    for group_id, group_rows in groups.items():
        actions = [row['Action'].strip() for row in group_rows]
        
        # Check if group needs fixing
        has_keep = 'Keep' in actions
        all_empty = all(action == '' for action in actions)
        all_delete_or_empty = all(action in ['Delete', '', '????'] for action in actions)
        
        if not has_keep and not all_empty:
            print(f"Fixing Group {group_id}: {actions}")
            fixed_groups += 1
            
            # Find the best file to keep
            best_idx = 0
            best_score = -1
            
            for i, row in enumerate(group_rows):
                score = 0
                
                # Prefer organized filenames
                if '_' in row['Filename'] and 'x' in row['Filename']:
                    score += 10
                
                # Avoid invalid folders
                folder_lower = row['Folder'].lower()
                if any(bad in folder_lower for bad in ['0000-00', 'nptsi', 'new folder']):
                    score -= 5
                
                # Prefer larger files (quality)
                try:
                    size_kb = int(row['Size (KB)'])
                    score += size_kb / 100  # Add size bonus
                except:
                    pass
                
                # Prefer files with valid date folders
                if any(pattern in row['Folder'] for pattern in ['2020+', '2010+', '2000+', '1990+', '1980+', '1970+']):
                    score += 5
                
                if score > best_score:
                    best_score = score
                    best_idx = i
            
            # Set the best file to Keep, others to Delete
            for i, row in enumerate(group_rows):
                if i == best_idx:
                    row['Action'] = 'Keep'
                    if not row['Comments'].strip():
                        row['Comments'] = 'Best option in group (auto-selected to avoid losing all copies)'
                else:
                    if row['Action'].strip() not in ['Delete']:
                        row['Action'] = 'Delete'
                        if not row['Comments'].strip():
                            row['Comments'] = 'Not best option in group'
    
    # Write fixed data
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)
    
    print(f"Fixed {fixed_groups} groups")
    print(f"Output saved to: {output_file}")
    
    # Verify the fix
    verify_groups = defaultdict(list)
    with open(output_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            verify_groups[row['Group ID']].append(row['Action'].strip())
    
    groups_without_keep = 0
    for group_id, actions in verify_groups.items():
        if 'Keep' not in actions and not all(action == '' for action in actions):
            groups_without_keep += 1
    
    print(f"Verification: {groups_without_keep} groups still without Keep (should be 0)")
    
    return 0

if __name__ == '__main__':
    fix_duplicate_groups()