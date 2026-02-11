
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
    EXIF Date - EXIF date from the image file - see date priority list below
    EXIF Offset - UTC offset (if available) from EXIF
    EXIF Timezone - calculate timezone based on Date and Offset
    EXIF Description - EXIF Description from image file
    EXIF Tags - EXIF tags from image file
    EXIF Ext - "true" extension based on actual image file format
    Calc Date - see Calc Date Logic below
    Calc Filename - Format = YYYY-MM-DD_HHMM_WIDTHxHEIGHT_PARENT_BASENAME.EXT - use Calc Date to replace the date prefix 
    Calc Path - Format = <decade>/<year>/<year>-<month>/<parent event folder>/<filename> - look for an existing folder that matches the Calc Filename
    Calc Description - Combine Sidecar and EXIF descriptions with commma delimitter if they are different - or just use one non-blank description if they are the same or one of them is blank.
    Calc Tags - Consolidate to include all tags from both EXIF and Sidecar

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


# Calc Date Logic

- general principle is to use the oldest (non 0) date from these: EXIF, Sidecar, Filelname, Folder

Name Date:
    CASE month({Filename Date}) = month({Folder Date}) THEN {Filename Date}
    CASE year({Folder Date}) < year({Filename Date}) THEN {Folder Date}
    ELSE {Filename Date}

Metadata Date:
    CASE {EXIF Date} > 0 then {EXIF Date}
    ELSE {Sidecar Date}

Calc Date:
    CASE {Metadata Date} > 0 AND date({Metadata Date}) <= date({Name Date}) THEN {Metadata Date}
    ELSE {Name Date}


log file should include an AUDIT line for each file that matchest the row in the .csv file

Calc Status:
    MATCH - no change in file/path
    RENAME - same path but filename has changed
    MOVE - different path

Calc Date Used: EXIF, Sidecar, Filename or Folder
Calc Time Used: EXIF, Sidecar, Filename or Folder
Meta - Name:  Difference (years, months, days, hours, mins) between Meata Date and Name Date
