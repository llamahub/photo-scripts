---
mode: agent
---

## Considerations
consider all relevant documentation linked to in the README.md file at the root level of this monorepo, including but not limited to the main documentation hub at docs/README.md, the setup guide at docs/setup/SETUP_GUIDE.md, the COMMON framework documentation at COMMON/docs/README.md, and the EXIF tools documentation at EXIF/docs/README.md.

## Script Identification
**Name:** delete_dups.py
**Project:** EXIF
**Location:** EXIF/scripts/

## Arguments:
**--input** (required): path to .csv file containing list of images to potentially delete.
**--status-col** (optional): name of the column in the input csv that contains the status of each image. IF not provided, default to "match_type".
**--status-val** (optional): the value in the status column that indicates an image should be deleted. If not provided, default to "Exact match".
**--file=col** (optional): name of the column in the input csv that contains the file paths of the images to potentially delete. If not provided, default to "source_file_path".

**--dry-run** (optional): If specified, the script will only log the files that would be deleted without actually deleting them.

**--help** (optional): Display usage information.

All required arguments must be both positional and named.

## Requirements:

Scan the input CSV file and delete all files where the value in the specified status column matches the specified status value.

## Logic:
- Business logic should be encapsulated in a class in a separate module within src/ folder.
- The CLI script should handle argument parsing, logging setup, and invoking the business logic class.
- Wherever possible, use COMMON framework features for logging and configuration, etc

## Logging:
- Use ScriptLogging from COMMON for detailed logging of the process.
- Log start and end of the script, number of files processed, number of duplicates found, and any errors encountered.
- Log the name of any genearated output files.
- Ensure logs are written to both console and a log file in .log/ directory.
- Log file should be named {CLI script name without ext}_{current datetimestamp}.log