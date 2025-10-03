---
mode: agent
---
create a new script file in EXIF/scripts that organizes photos from a source directory into target directory and subdirectories based on format using EXIF ImageData class

The script should:

- Accept command-line arguments for source directory, target directory, and dry-run mode
- Use logging for progress and error reporting
- Handle errors gracefully and log them
- Include a main function and be executable as a script 
- Follow the existing code style and structure in the project

The date of the photo should be obtained using the getImageDate method of the ImageData class.

The target directory structure should be:

<decade>/<year>/<year>-<month>/<parent folder>/<filename>

- <decade> is the decade of the photo (e.g., 1990s, 2000s) in the format "YYYY+"
- <year> is the 4-digit year (e.g., 1995, 2021)
- <month> is the 2-digit month (e.g., 01 for January, 02 for February, etc.)
- <parent folder> is the name of the immediate parent folder of the photo in the source directory
- <filename> is the original filename of the photo
