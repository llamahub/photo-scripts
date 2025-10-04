# Test Images CSV Analysis

## Overview
The `test_images.csv` file contains 55 test image records designed to thoroughly test EXIF date handling, file format detection, and organizational logic.

## Test Case Coverage

### Date Scenarios
- **Complete dates**: 39 records with all 4 date fields populated
- **Missing dates**: 16 records with one or more missing date fields
- **Date conflicts**: Various records where different date fields have different values
- **Date range**: Covers 1990s through 2025

### Folder Name Patterns
- **Date-like folders**: 29 unique folders with date patterns (e.g., "2021-06", "1995", "2020s")
- **Non-date folders**: 25 unique descriptive folders (e.g., "Vacation", "Family Photos", "Kitchen Renovations")
- **Special characters**: Includes spaces, hyphens, and ampersands

### File Extension Testing
- **Format variety**: jpg, png, tiff, tif, heic extensions
- **Mismatched extensions**: 17 files where Source Ext ≠ True Ext (e.g., .jpg files that are actually PNG)
- **Actual formats**: JPEG (28), PNG (14), TIFF (8), HEIC (5)

### Date Comparison Scenarios
The data includes various combinations where:
- Image dates match/differ from parent folder dates
- Image dates match/differ from filename dates  
- Parent folder and filename indicate same/different dates
- Some files have no date information for testing fallback behavior

### Special Test Cases
- Zero-height images (corrupted files)
- Missing metadata fields
- Historical dates (1990s)
- Recent dates (2024-2025)
- Various image dimensions and orientations

## Usage
This CSV can be used to generate actual test image files with the specified EXIF metadata, or for testing organizational algorithms without requiring physical files.

## Fields Description
- **Root Path**: Directory path from base to parent folder
- **Parent Folder**: Immediate parent folder name (mix of date-like and descriptive)
- **Filename**: Image filename without extension (some with date patterns)
- **Source Ext**: File extension as it appears in filesystem
- **Actual Format**: True image format
- **Image Width/Height**: Pixel dimensions
- **True Ext**: Correct extension based on actual format
- **DateTimeOriginal**: Primary EXIF date field
- **ExifIFD:DateTimeOriginal**: Alternative EXIF date field
- **XMP-photoshop:DateCreated**: XMP date metadata
- **FileModifyDate**: File system modification date