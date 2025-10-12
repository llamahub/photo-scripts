# EXIF Date Setting Workflow

## Overview

The new `set_image_dates.py` script complements the existing analyze script to provide a complete workflow for EXIF date correction:

1. **Analyze images** with `analyze.py` - creates CSV with "Set Date" column
2. **Edit CSV** - user fills in desired dates in "Set Date" column  
3. **Update EXIF** with `set_image_dates.py` - applies the dates to image files

## Workflow Example

### Step 1: Analyze Your Photos
```bash
# Analyze a folder of photos
inv r -n analyze -a '/path/to/photos --output analysis.csv'

# This creates a CSV file with columns including:
# - Source Path: path to each image file
# - Image Date: current EXIF date (if any)
# - Set Date: empty column for you to fill in
```

### Step 2: Edit the CSV File
Open `analysis.csv` in a spreadsheet program and:
- Review the "Image Date" column to see current EXIF dates
- Fill in the "Set Date" column with corrected dates for images that need updating
- Leave "Set Date" empty for images that don't need changes

Supported date formats for "Set Date" column:
- `2023-08-20 15:45:30` (full datetime)
- `2023-08-20 15:45` (date and time)
- `2023-08-20` (date only)
- `2023/08/20` (alternate format)
- `08/20/2023` (US format)

### Step 3: Update EXIF Dates
```bash
# Preview changes (recommended first run)
inv r -n set_image_dates -a '/path/to/photos analysis.csv --dry-run'

# Apply the changes
inv r -n set_image_dates -a '/path/to/photos analysis.csv'

# With debug output
inv r -n set_image_dates -a '/path/to/photos analysis.csv --debug'
```

## What Gets Updated

The script updates these EXIF fields:
- `DateTimeOriginal` - The primary EXIF date field
- `ExifIFD:DateTimeOriginal` - EXIF metadata date  
- `XMP-photoshop:DateCreated` - Adobe XMP date
- `FileModifyDate` - File system modification date

## Advanced Usage

### Custom Column Names
If your CSV uses different column headers:
```bash
inv r -n set_image_dates -a '/path/to/photos data.csv --file-col "File Path" --date-col "New Date"'
```

### Processing Statistics
The script provides detailed statistics:
- Total files processed
- Successfully updated files
- Skipped files (no date specified)
- Error count and success rate

## Requirements

- **ExifTool** must be installed (`sudo apt install libimage-exiftool-perl`)
- CSV file must contain file path and date columns
- Target images must exist and be writable
- Dates must be in recognized formats

## Error Handling

The script gracefully handles:
- Missing or invalid image files
- Unparseable date formats  
- ExifTool failures
- Permission issues
- Network timeouts

## Integration with Existing Tools

This script integrates seamlessly with:
- **analyze.py** - generates CSV with "Set Date" column
- **organize.py** - organize photos after date correction
- **generate.py** - create test images for validation

The complete photo management workflow becomes:
1. Analyze → 2. Edit dates → 3. Set dates → 4. Organize photos