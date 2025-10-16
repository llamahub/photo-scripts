#!/bin/bash

# Recovery script to move files back from accidental organize operation
# Generated on: 2025-10-16 08:58:41
# Log file: photo_organizer_20251016_085841.log

SOURCE_RECOVERY="/mnt/photo_drive/santee-recovered/"
TARGET_ACCIDENT="/mnt/photo_drive/Santee_Image_Library3/"

# Check for dry-run flag
DRY_RUN=false
if [ "$1" = "--dry-run" ] || [ "$1" = "-n" ]; then
    DRY_RUN=true
    echo "DRY RUN MODE - No files will be moved"
fi

echo "=============================================================================="
echo "Photo Organizer Recovery Script"
echo "=============================================================================="
echo "Recovering files from: $TARGET_ACCIDENT"
echo "                  to: $SOURCE_RECOVERY"
echo "=============================================================================="

# Count files to be moved back
FILE_COUNT=$(find "$TARGET_ACCIDENT" -type f | wc -l)
echo "Found $FILE_COUNT files to move back"

if [ "$FILE_COUNT" -eq 0 ]; then
    echo "No files found to recover. Recovery may have already been completed."
    exit 0
fi

if [ "$DRY_RUN" = false ]; then
    # Ask for confirmation only in real mode
    read -p "Do you want to proceed with moving $FILE_COUNT files back? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Recovery cancelled."
        exit 1
    fi
fi

if [ "$DRY_RUN" = true ]; then
    echo "DRY RUN - Showing what would be moved:"
    echo ""
else
    echo "Starting recovery..."
    # Create recovery directory if it doesn't exist
    mkdir -p "$SOURCE_RECOVERY"
    echo "Created recovery directory: $SOURCE_RECOVERY"
fi

# Move all files back to source, preserving filenames exactly
MOVED_COUNT=0
CONFLICTS=0
while IFS= read -r -d '' file; do
    filename=$(basename "$file")
    target_path="$SOURCE_RECOVERY$filename"
    
    # Check if target already exists in recovery directory
    if [ -f "$target_path" ]; then
        echo "WARNING: File already exists in recovery directory: $filename"
        echo "  From organized: $file"
        echo "  Recovery location: $target_path"
        if [ "$DRY_RUN" = true ]; then
            echo "  Would SKIP to prevent overwrite"
        else
            echo "  Skipping to prevent overwrite..."
        fi
        ((CONFLICTS++))
        continue
    fi
    
    if [ "$DRY_RUN" = true ]; then
        echo "Would move: $file"
        echo "       To: $target_path"
        echo ""
        ((MOVED_COUNT++))
    else
        if mv "$file" "$target_path"; then
            ((MOVED_COUNT++))
            echo "Recovered: $filename"
            
            # Progress update every 10 files
            if [ $((MOVED_COUNT % 10)) -eq 0 ]; then
                echo "Progress: $MOVED_COUNT/$FILE_COUNT files recovered"
            fi
        else
            echo "ERROR: Failed to recover $(basename "$file")"
        fi
    fi
done < <(find "$TARGET_ACCIDENT" -type f -print0)

echo "=============================================================================="
if [ "$DRY_RUN" = true ]; then
    echo "DRY RUN Complete!"
    echo "Files that would be recovered: $MOVED_COUNT"
    echo "Conflicts that would be found: $CONFLICTS"
    echo "Recovery directory: $SOURCE_RECOVERY"
else
    echo "Recovery Complete!"
    echo "Files recovered: $MOVED_COUNT"
    echo "Conflicts found: $CONFLICTS"
    echo "Recovery directory: $SOURCE_RECOVERY"
    echo ""
    echo "Next step: Use the organize script to move files from"
    echo "  $SOURCE_RECOVERY --> /mnt/photo_drive/santee-images"
fi
echo "=============================================================================="

if [ "$DRY_RUN" = false ]; then
    # Clean up empty directories in the accident target (only in real mode)
    echo "Cleaning up empty directories..."
    find "$TARGET_ACCIDENT" -type d -empty -delete 2>/dev/null
fi

# Check if target directory is now empty
if [ -d "$TARGET_ACCIDENT" ]; then
    REMAINING=$(find "$TARGET_ACCIDENT" -type f | wc -l)
    if [ "$REMAINING" -eq 0 ]; then
        echo "Removing empty target directory: $TARGET_ACCIDENT"
        rmdir "$TARGET_ACCIDENT" 2>/dev/null
    else
        echo "WARNING: $REMAINING files still remain in $TARGET_ACCIDENT"
    fi
fi

echo "Recovery script completed successfully!"