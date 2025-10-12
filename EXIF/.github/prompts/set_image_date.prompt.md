I want a script in EXIF/script called set_image_dates.py that follows the common architecture framework and guidelines + testing with these args:

consider these documens:

COMMON/ARCHITECTURE.md
COMMON/README.md
.vscode/ai-assistant-prompt.md
EXIF/TESTING_STRATEGY.md

- target = first required positional argument (can also be a named arg) =  path to target folder to update EXIF dates in
- input = path to csv file with at least two columns (for file path and date)
- file_col = header in csv file that indicates column used to determine path to file to set EXIF dates for - default this to "Source Path"
- date_col = header in csv file that indicates coluimn used to determine the date to use for setting EXIF dates - default this to "Set Date"

I want to also make sure that the analyze.py script adds an empty "Set Date" column to the end of the csv file it produces

I intend to use that csv file to add a date in the column for any images that I want to update the EXIF date for.

The script should then scan the designated date_col column in the input csv file and for any filled in valid dates and then update the following dates for the file designated in the file_col:

    "-DateTimeOriginal",
    "-ExifIFD:DateTimeOriginal",
    "-XMP-photoshop:DateCreated",
    "-FileModifyDate"
