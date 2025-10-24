Migrate designated script to use common pattern shown in example_script.py

Please take the script I ask you to migrate and refactor it to use the same consistent style and structure for defining and parsing command-line arguments as shown in the example_script.py file in both EXIF and COMMON.

## Standard Argument Naming Convention

**CRITICAL**: All scripts MUST follow this standardized argument naming pattern:

### Core Argument Types:
- `--input` / `input` (positional) → Input file(s) or data source
- `--source` / `source` (positional) → Source directory or location  
- `--target` / `target` (named only) → Target/destination directory or output location
- `--output` / `output` (positional) → Output file(s) when different from target

### Standard Pattern Examples:
```python
# For scripts that process files from a directory:
'input': {
    'positional': True,
    'help': 'Input CSV/data file'
},
'source': {
    'positional': True,
    'help': 'Source directory containing files to process'
},
'target': {
    'flag': '--target',
    'help': 'Target directory for processed files'
}

# For scripts that generate output files:
'source': {
    'positional': True,
    'help': 'Source directory to analyze'
},
'output': {
    'positional': True,
    'help': 'Output file for results'
}
```

### Argument Resolution Pattern:
**NEVER use `_alt` patterns!** The ScriptArgumentParser framework automatically handles both positional and named arguments for the same logical parameter.

```python
# CORRECT - Use the clean organize.py pattern:
resolved_args = parser.validate_required_args(args, {
    'input_file': ['input_file', 'input'],     # Maps --input and positional input
    'source_dir': ['source_file', 'source'],   # Maps --source and positional source  
    'target_dir': ['target_file', 'target']    # Maps --target (named only)
})

# WRONG - Don't use _alt patterns:
# 'input_alt': {'flag': '--input', 'dest': 'input_alt'}  # ❌ Never do this
```

### Real Examples from Successfully Migrated Scripts:

**organize.py** (source→target pattern):
```python
SCRIPT_ARGUMENTS = {
    'source': {
        'positional': True,
        'help': 'Source directory containing photos/videos'
    },
    'target': {
        'positional': True,
        'help': 'Target directory for organized photos/videos'
    }
}
# Maps to: source_dir, target_dir
```

**dupgremove.py** (input→source→target pattern):
```python
SCRIPT_ARGUMENTS = {
    'input': {
        'positional': True,
        'help': 'dupGuru CSV file with Action column'
    },
    'source': {
        'positional': True,
        'help': 'Root directory where files to remove are located'
    },
    'target': {
        'flag': '--target',
        'help': 'Directory to move duplicates to'
    }
}
# Maps to: input_file, source_dir, target
```

**find_dups.py** (source→output pattern):
```python
SCRIPT_ARGUMENTS = {
    'source': {
        'positional': True,
        'help': 'Source directory to scan for duplicates'
    },
    'output': {
        'positional': True,
        'help': 'Output CSV file for duplicate results'
    }
}
# Maps to: source_dir, output_file
```

## Migration Steps

Ensure that:
- All argument definitions are centralized and follow the same format.
- The argument parser is created in a consistent manner.
- Help text generation is uniform across scripts.
- Validation of required arguments is handled consistently.
- **Standard argument naming conventions are followed exactly**

I prefer you follow these steps:

1. **Apply Standard Naming**: Update all arguments to use the standard `--input`/`--source`/`--target`/`--output` naming convention before starting migration.
2. Make a copy of the example script and modify it to match the name and purpose of the script being migrated.
3. Replace the argument definitions in the migrated script with those from the example script, adjusting names and help text as necessary to fit the new script's standards.
4. **Use Clean Argument Pattern**: Follow the organize.py pattern for handling positional+named arguments - use `validate_required_args` with proper mapping, never `_alt` patterns.
5. Ensure that the argument parser is created in a consistent manner, following the patterns established in the example script.
6. Ensure that all business logic is encapsulated in a separate class in the appropriate src/exif or src/common module.   If leveraging existing classes, make sure that all existing tests pass after the migration.
If new classes are created, ensure that they have appropriate unit tests.
7. Ensure that all audit level info required to understand image processing steps is logged using INFO level logging and can be played back from log files if necessary.
   **IMPORTANT**: When calling `parser.setup_logging(resolved_args, script_name)`, use the base script name (without extension) as the script_name parameter. For example, for `find_dups.py`, use `"find_dups"`. This ensures log files are named correctly (e.g., `find_dups_20251019_084113.log`) instead of using the generic `argument_parser_*` naming.
8. Once migrration is complete and tests pass, then remove the old version of the script that was migrated and rename the new migrated script to the original script name so that it replaces the old version seamlessly.
9. Verify that the new script runs correctly from the command line and that the --help output matches the description at the top of the file.
10. Make sure all tests pass successfully after migration.
11. **Update all test files** to use the new standardized argument names (e.g., change `--dup-path` to `--target`, etc.).
12. Clean up the migrated script by removing template-specific sections from the docstring:
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
- [x] `EXIF/scripts/dupgremove.py` - Duplicate removal utility
- [x] `EXIF/scripts/find_dups.py` - Duplicate finder
- [x] `EXIF/scripts/move_folders.py` - Move files between folders based on CSV instructions
- [x] `EXIF/scripts/organize.py` - Image organization tool
