---
mode: agent
---

I need to generate csv file with a list of test images with various EXIF data for testing purposes. The csv file should have the following columns:

- Root Path - this should be path from the base directory to the parent folder holding the image
- Parent Folder - this should be the name of the immediate parent folder of the image.  I need a mixture of some folders that are named with date like values (e.g., "2021-06", "2020s", "1995") and some that are not (e.g., "Vacation", "Family", "Misc").  Should include some with spaces and special characters.
- Filename - This should be the name of the image file without the extension.  Should include some with spaces and special characters.  Some filenames should include date-like values (e.g., "IMG_20210615", "Photo_1999").
- Source Ext - this should be the file extension of the image file (e.g., jpg, png, tif, heic).  Include a variety of common image formats. For some files, the extension will not match the actual image format (e.g., a .jpg file that is actually a PNG image).
- Actual Format - this should be the actual image format (e.g., JPEG, PNG, TIFF, HEIC).
- Image Width - this should be the width of the image in pixels.
- Image Height - this should be the height of the image in pixels.
- DateTimeOriginal - this should be a date that will be used as the DateTimeOriginal EXIF tag value.
- ExifIFD:DateTimeOriginal - this should be a date that will be used as the ExifIFD:DateTimeOriginal EXIF tag value.
- XMP-photoshop:DateCreated - this should be a date that will be used as the XMP-photoshop:DateCreated tag value.
- FileModifyDate - this should be a date that will be used as the FileModifyDate tag value.

I need a sampling of records where the 4 date fields are all the same, some where they differ and some where one or more are missing.  The dates should range from the 1990s to the present, with a good mix of years and months.

I also need a variety of images where the date of the image (based on the 4 fields above) is >, <, or = the date indicated by the parent folder name (if it is date-like).
Similarly I need a variety of images where the date of the image (based on the 4 fields above) is >, <, or = the date indicated by the filename (if it is date-like).
There should be some images where the parent folder name and filename are date-like and indicate different dates and some where they indicate the same date.

The csv file should have at least 50 records to provide a good variety of test cases.

I want to review the csv file before generating the actual images.  Please store this file in the EXIF/tests/test_data directory as test_images.csv.

