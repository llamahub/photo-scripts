Migrate designated script to use common pattern shown in example_script.py

Please take the script I ask you to migrate and refactor it to use the same consistent style and structure for defining and parsing command-line arguments as shown in the example_script.py file in both EXIF and COMMON.

Ensure that:
- All argument definitions are centralized and follow the same format.
- The argument parser is created in a consistent manner.
- Help text generation is uniform across scripts.
- Validation of required arguments is handled consistently.

I prefer you follow these steps:

1. Make a copy of the example script and modify it to match the name and purpose of the script being migrated.
2. Replace the argument definitions in the migrated script with those from the example script, adjusting names and help text as necessary to fit the new script's standards.
3. Ensure that the argument parser is created in a consistent manner, following the patterns established in the example script.
4. Ensure that all business logic is encapsulated in a separate class in the appropriate src/exif or src/common module.   If leveraging existing classes, make sure that all existing tests pass after the migration.
If new classes are created, ensure that they have appropriate unit tests.
5. Ensure that all audit level info required to understand image processing steps is logged using INFO level logging and can be played back from log files if necessary.
   **IMPORTANT**: When calling `parser.setup_logging(resolved_args, script_name)`, use the base script name (without extension) as the script_name parameter. For example, for `find_dups.py`, use `"find_dups"`. This ensures log files are named correctly (e.g., `find_dups_20251019_084113.log`) instead of using the generic `argument_parser_*` naming.
6. Once migrration is complete and tests pass, then remove the old version of the script that was migrated and rename the new migrated script to the original script name so that it replaces the old version seamlessly.
7. Verify that the new script runs correctly from the command line and that the --help output matches the description at the top of the file.
8. Make sure all tests pass successfully after migration.
9. Clean up the migrated script by removing template-specific sections from the docstring:
   - Remove the "Key features:" section (this is framework documentation, not script-specific)
   - Remove the "Follow this structure for all EXIF scripts to ensure consistency." line
   - Keep only the script-specific description, purpose, and usage information

## Scripts To Migrate

**IMPORTANT**: This list tracks migration progress. Remove scripts from the "To Migrate" sections and move them to "Already Migrated" as they are successfully converted to use ScriptArgumentParser.

### COMMON Scripts (Manual argparse → ScriptArgumentParser):
- [ ] `scan.py` - Directory scanning and analysis utility
- [ ] `space.py` - Disk space analysis tool

### EXIF Scripts (Manual argparse → ScriptArgumentParser):
- [ ] `delete_dups.py` - Delete duplicate files based on CSV input
- [ ] `dupgremove.py` - Duplicate removal utility
- [ ] `dupguru.py` - DupGuru integration utility
- [ ] `generate.py` - Image generation utility
- [ ] `migrate_xmp.py` - XMP metadata migration tool
- [ ] `select.py` - Image selection utility
- [ ] `set_image_dates.py` - Set image dates from EXIF data
- [ ] `takeout.py` - Google Takeout processor

### Already Migrated ✅:
- [x] `COMMON/scripts/clean.py` - Clean utility for removing unwanted files and empty folders
- [x] `COMMON/scripts/diff.py` - Directory comparison utility
- [x] `EXIF/scripts/analyze.py` - High-performance image organization and date analysis
- [x] `EXIF/scripts/find_dups.py` - Duplicate finder
- [x] `EXIF/scripts/organize.py` - Image organization tool
