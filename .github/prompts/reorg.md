

I need a proposal for re-organizing this library so that:

1. All folders match the structure:
<decade>/<YYYY>/<YYYY-MM>/<YYYY-MM-DD (optional event name) (optional seq#)>/<files>

2. no date/event folder has more than 50 files
3. if > 50 files exist for a date/event - multiple folders are created with the same name +  seq # (_01,_02,_03, etc)
4. any non image files are preserved in the same folder where they were originally stored
5. sidecar files (.xmp, .json, .possible, .unknown) are stored in same folder alongside image files (and not counted towards the 50 limit)

Please ask for any clarification needed to do this and highlight any instances where this reorganization might cause problematic results.



1 - A) Move month-level files into dated folders based on their EXIF dates
2 - A) Use parent folder date (e.g., file in 2025-06/ → 2025-06-01)
3 - A) Split chronologically by file datetime into sequential folders (_01, _02, etc.).
4 - A) Keep separate: 2024-11-20 Thanksgiving and 2024-11-20 Family Photos


dates:

Folder
Filename
Sidecar
EXIF
File date

if EXIF > Filename - probably a more recent scan of an older photo - take the older date


YYYY-MM-DD_HHMM_WIDTHxHEIGHT_PARENT_BASENAME.EXT


Date
Offset
Timezone
Description
