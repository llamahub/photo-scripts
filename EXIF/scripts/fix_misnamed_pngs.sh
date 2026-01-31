#!/bin/bash
# Script to rename .PNG files that are actually JPEGs to .jpg extension
# Usage: ./fix_misnamed_pngs.sh [--dry-run]

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "=== DRY RUN MODE - No files will be renamed ==="
fi

count=0
renamed=0
errors=0

echo "Scanning for .PNG files that are actually JPEGs..."
echo ""

# Find all .PNG files and check if they're actually JPEGs
while IFS= read -r -d '' file; do
    ((count++))
    
    # Check if file is actually a JPEG
    file_type=$(file -b "$file")
    if [[ "$file_type" =~ ^JPEG ]]; then
        # Generate new filename with .jpg extension
        new_file="${file%.PNG}.jpg"
        
        # Check if new_file already exists
        if [[ -e "$new_file" ]]; then
            echo "ERROR: Target already exists: $new_file"
            ((errors++))
            continue
        fi
        
        if $DRY_RUN; then
            echo "[DRY RUN] Would rename: $file -> $new_file"
            ((renamed++))
        else
            if mv "$file" "$new_file"; then
                echo "Renamed: $file -> $new_file"
                ((renamed++))
            else
                echo "ERROR: Failed to rename: $file"
                ((errors++))
            fi
        fi
    fi
done < <(find . -iname "*.png" -type f -print0)

echo ""
echo "=== SUMMARY ==="
echo "Total .PNG files scanned: $count"
echo "Files renamed: $renamed"
echo "Errors: $errors"

if $DRY_RUN && [[ $renamed -gt 0 ]]; then
    echo ""
    echo "Run without --dry-run to perform the actual rename operations"
fi
