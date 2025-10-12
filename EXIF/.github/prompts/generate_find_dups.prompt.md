---
mode: agent
---

## Considerations
consider all relevant documentation linked to in the README.md file at the root level of this monorepo, including but not limited to the main documentation hub at docs/README.md, the setup guide at docs/setup/SETUP_GUIDE.md, the COMMON framework documentation at COMMON/docs/README.md, and the EXIF tools documentation at EXIF/docs/README.md.

## Script Identification
**Name:** find_dups.py
**Project:** EXIF
**Location:** EXIF/scripts/

## Arguments:
**--source** (required): The folder to for each source image
**--target** (required): The folder to search for duplicates of each source image
**--output** (optional): The file to write the results to. If not provided, use .log/find_dups_{current datetimestamp}.csv

**--help** (optional): Display usage information.

## Requirements:

Check for duplicates using the following strategies in this order:

1. Target Filename match: Check if the target filename (as determined by getTargetFilename) exists in the target folder (or subfolders). 
2. Exact match: Check if a file with the exact same name exists in the target folder (or subfolders).
3. Partial Filename match: Check if a file containing the same base name as part of its filename exists in the target folder (or subfolders).

## Output file format:
- csv file with columns:
  - source_file_path
  - target_file_path
  - match_type (Target Filename, Exact match, Partial Filename, none)
- If no duplicates are found for a source image, still include it in the output with match_type "none" and an appropriate note.

## Logic:
- Business logic should be encapsulated in a class (e.g., DuplicateFinder) in a separate module (e.g., duplicate_finder.py) within EXIF/src/exif/.
- The script (find_dups.py) should handle argument parsing, logging setup, and invoking the business logic class.

## Logging:
- Use ScriptLogging from COMMON for detailed logging of the process.
- Log start and end of the script, number of files processed, number of duplicates found, and any errors encountered.
- Log the name of the genearated output file.
- Ensure logs are written to both console and a log file in .log/ directory.
- Log file should be named find_dups_{current datetimestamp}.log