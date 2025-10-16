---
mode: agent
---

## Considerations
consider all relevant documentation linked to in the README.md file at the root level of this monorepo, including but not limited to the main documentation hub at docs/README.md, the setup guide at docs/setup/SETUP_GUIDE.md, the COMMON framework documentation at COMMON/docs/README.md, and the EXIF tools documentation at EXIF/docs/README.md.

## Script Identification
**Name:** takeout.py
**Project:** EXIF
**Location:** EXIF/scripts/

## Arguments:
**--source** (required): path to .zip file created by Google Takeout containing images.
**--target** (required): path to directory where extracted images should be saved.

**--help** (optional): Display usage information.

All required arguments must be both positional and named.

## Requirements:

Extract all images and sidecar files from the provided Google Takeout .zip file into the specified target directory, preserving the original directory structure.  Update EXIF metadata of each extracted image/video to include data from the associated sidecar file, if present.

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