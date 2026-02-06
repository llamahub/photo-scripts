
## Script Details:

script name:  analyze.py
description:  Gathers info on all files in image library and outputs to a CSV file

args: --source (positional/named/required) - path to root folder of source image library
      --output (positional/named/optional) - output CSV file for analysis - default to .log/analyze_{timestamp}.csv

log file: ./log/analyze_{timestamp}.log

business class in src/image_analyzer.py = ImageAnalyzer

csv file should contain one row for each file with these columns:

## CSV File Columns:

    Filenanme - full path filename
    Folder Date - date derived from parent folder name - use YYYY-MM-DD and set MM or DD to 00 if these are not available
    Filename Date - date derived from parsing date like values in the filename - if file starts with a date in format YYYY-MM-DD that is the priority date to use for this field
    Sidecar File - filename of sidecar file for this image (if available)
    Sidecar Date - EXIF date from sidecar file if available - see date priority list below
    Sidecar Offset - UTC offset (if available) from sidecar file
    Sidecar Timezone - calculate timezone based on Date and Offset
    Sidecar Description
    Sidecar Tags
    Image Date - EXIF date from the image file - see date priority list below
    Image Offset - UTC offset (if available) from sidecar file
    Image Timezone - calculate timezone based on Date and Offset
    Image Description - EXIF Description from image file
    Image Tags - EXIF tags from image file
    Image Ext - "true" extension based on actual image file format

## EXIF Date Priority:
 
    Check for these dates in this order and use the first available:

    "DateTimeOriginal"
    "ExifIFD:DateTimeOriginal"
    "XMP-photoshop:DateCreated"
    "CreateDate"
    "ModifyDate"
    "MediaCreateDate"
    "MediaModifyDate"
    "TrackCreateDate"
    "TrackModifyDate"
    "FileModifyDate"


log file should include an AUDIT line for each file that matchest the row in the .csv file