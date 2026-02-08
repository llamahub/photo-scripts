# Calc Columns Implementation - Complete ✅

## Summary

Successfully implemented three new calculated columns for the `analyze.py` CSV output:

1. **Calc Date** - Intelligent date selection using the oldest reliable date
2. **Calc Filename** - Normalized filename format with metadata components
3. **Calc Path** - Organized folder hierarchy structure

## Implementation Details

### Files Modified

1. **[src/image_analyzer.py](src/image_analyzer.py)** - 200+ lines added
   - Updated `ImageRow` dataclass: added `calc_date`, `calc_filename`, `calc_path` fields
   - Added 9 new private methods for calculations and helper utilities
   - Updated `_analyze_file()` to compute calculated fields
   - Updated `_csv_headers()` and `_row_to_dict()` for 3 new columns

2. **[tests/test_image_analyzer.py](tests/test_image_analyzer.py)** - 140+ lines added
   - Added 11 comprehensive test functions
   - Coverage: 91% (382 statements, 34 missed)
   - All 22 tests passing

### New Methods Added

#### Core Calculation Methods

1. **`_get_year_month(date_str: str) -> Optional[str]`**
   - Extracts YYYY-MM from date strings
   - Returns None for invalid/missing dates (1900-01-01, 0000-00-00, empty)

2. **`_calculate_name_date(folder_date: str, filename_date: str) -> str`**
   - Implements "Name Date" spec logic
   - Prioritizes folder vs filename dates based on month/year matching

3. **`_calculate_calc_date(exif_date: str, name_date: str) -> str`**
   - Implements "Calc Date" spec logic
   - Uses EXIF date if valid and <= Name Date, else Name Date
   - Compares date-only (ignores time component)

4. **`_get_image_dimensions(image_exif: Dict) -> str`**
   - Extracts and formats image dimensions from EXIF
   - Returns format: "WIDTHxHEIGHT" or "0x0" if missing

5. **`_calculate_calc_filename(...) -> str`**
   - Builds normalized filename: `YYYY-MM-DD_HHMM_WIDTHxHEIGHT_PARENT_BASENAME.EXT`
   - Intelligently strips duplicate info from basename
   - Includes parent folder if non-date-only

6. **`_calculate_calc_path(...) -> str`**
   - Builds organized path: `<decade>/<year>/<year>-<month>/<parent>/<filename>`
   - Calculates decade from year (e.g., 2020 → 2020+)
   - Skips parent folder if purely date-based

#### Helper Methods

7. **`_is_date_only(folder_name: str) -> bool`**
   - Detects if folder name is purely date-based (YYYY, YYYY-MM, YYYY-MM-DD)
   - Returns True if no descriptive text remains after removing date patterns

8. **`_extract_descriptive_parent_folder(parent_name: str) -> str`**
   - Returns parent folder name only if it contains non-date text
   - Returns empty string for date-only folder names

9. **`_strip_duplicate_info_from_basename(basename: str, parent_folder: str, dimensions: str) -> str`**
   - Removes parent folder name if it appears in basename
   - Removes existing dimension patterns (WIDTHxHEIGHT)
   - Removes leading date patterns that would duplicate Calc Date
   - Cleans up multiple underscores/hyphens

### Test Coverage

**22 tests, 91% coverage:**

#### New Calculation Tests
- `test_is_date_only()` - Date-only detection (7 cases)
- `test_extract_descriptive_parent_folder()` - Parent folder extraction (5 cases)
- `test_strip_duplicate_info_from_basename()` - Basename deduplication (3 cases)
- `test_get_image_dimensions()` - Dimension extraction (3 cases)
- `test_get_year_month()` - Year-month extraction (5 cases)
- `test_calculate_name_date()` - Name Date logic (6 cases)
- `test_calculate_calc_date()` - Calc Date logic (7 cases)
- `test_calculate_calc_filename()` - Filename generation (4 cases)
- `test_calculate_calc_path()` - Path generation (3 cases)
- `test_calculate_calc_filename_with_real_exif()` - Real image integration (PIL)
- `test_csv_output_includes_calc_columns()` - End-to-end CSV validation

#### Existing Tests (Still Passing)
- All 11 original ImageAnalyzer tests continue to pass

### CSV Output Example

**Headers (18 total):**
```
Filenanme, Folder Date, Filename Date, Sidecar File, Sidecar Date, Sidecar Offset, 
Sidecar Timezone, Sidecar Description, Sidecar Tags, EXIF Date, EXIF Offset, 
EXIF Timezone, EXIF Description, EXIF Tags, EXIF Ext, Calc Date, Calc Filename, Calc Path
```

**Sample Data:**
```
Calc Date:     2008-05-08
Calc Filename: 2008-05-08_0000_600x450_2008-05-03 Cub Scouts Photos from Janice_1704_CIMG3926.jpg
Calc Path:     2000+/2008/2008-05/2008-05-03 Cub Scouts Photos from Janice/2008-05-08_0000_600x450_2008-05-03 Cub Scouts Photos from Janice_1704_CIMG3926.jpg
```

## Implementation Logic

### Calc Date Algorithm

**Name Date (intermediate):**
```
IF month(Filename Date) == month(Folder Date) THEN
    return Filename Date
ELSE IF year(Folder Date) < year(Filename Date) THEN
    return Folder Date
ELSE
    return Filename Date
```

**Calc Date (final):**
```
IF EXIF Date is valid AND date(EXIF Date) <= date(Name Date) THEN
    return EXIF Date
ELSE
    return Name Date
```

### Calc Filename Format

```
YYYY-MM-DD_HHMM_WIDTHxHEIGHT_PARENT_BASENAME.EXT
```

- **YYYY-MM-DD**: Date portion from Calc Date
- **HHMM**: Time portion from Calc Date (or 0000 if missing)
- **WIDTHxHEIGHT**: Image dimensions from EXIF (or 0x0 if missing)
- **PARENT**: Parent folder name (omitted if date-only)
- **BASENAME**: Original filename stem (deduplicated)
- **EXT**: True file extension

### Calc Path Format

```
<decade>/<year>/<year>-<month>/<parent>/<calc_filename>
```

- **decade**: Year rounded down to nearest 10 (e.g., 2020+, 2010+, 1990+)
- **year**: 4-digit year
- **year-month**: YYYY-MM format
- **parent**: Parent folder name (omitted if date-only)
- **calc_filename**: Normalized filename from Calc Filename column

## User-Specified Behaviors Implemented

✅ **Q1: Date Comparison** - Option B (date-only comparison, ignore time)
- If EXIF date is same day, trust its time over filename time

✅ **Q2: Parent Folder Naming** - Intelligent filtering
- Keep parent folder if it contains non-date text (e.g., "2024-10-Events")
- Skip parent if purely date-based (e.g., "2024-10" or "2024-10-01")

✅ **Q3: Width × Height Format** - Padded format
- Use padded format (1920x1080, not 1920x 1080)
- Returns "0x0" if dimensions missing from EXIF

✅ **Q4: Parent Folder Extraction** - As-is with date detection
- Use immediate parent directory name as-is
- But skip in path if purely date-based

✅ **Q5: Timestamp in Calc Filename** - Conditional
- If Calc Date has HHMM: use extracted time
- Otherwise: use "0000"

✅ **Q6: Test Approach** - Real exiftool integration
- Tests use real exiftool + real image files (PIL)
- 91% code coverage achieved

## Validation Results

**Test Execution:**
```
============================= 22 passed in 0.17s ==============================
coverage: platform linux, python 3.12.3-final-0
Name                    Stmts   Miss  Cover   Missing
-----------------------------------------------------
src/image_analyzer.py     382     34    91%
-----------------------------------------------------
TOTAL                     382     34    91%
```

**Real Photo Analysis (415 files):**
```
✅ Analysis complete. Rows written: 415
```

Sample Calc Columns verified:
- Calc Date: Properly formatted dates (e.g., 2008-05-08)
- Calc Filename: Normalized format with all components (e.g., 2008-05-08_0000_600x450_...)
- Calc Path: Organized hierarchy with decade, year, month, and parent folder

## Edge Cases Handled

- ✅ Missing image dimensions → "0x0" in Calc Filename and path
- ✅ Date-only parent folders → Skipped in Calc Path
- ✅ Duplicate parent folder names in basename → Stripped intelligently
- ✅ Empty/invalid dates (1900-01-01, 0000-00-00) → Treated as missing
- ✅ Partial dates (MM or DD missing) → Handled with YYYY-MM-DD format
- ✅ Files with no time component → Uses "0000" for HHMM
- ✅ Special characters in parent folder names → Preserved in path
- ✅ Unicode folder names → Handled correctly

## Performance Impact

- ✅ No additional exiftool calls (uses cached EXIF data)
- ✅ Lightweight string parsing and comparison operations
- ✅ No filesystem lookups (Calc Path is virtual/calculated)
- ✅ Multi-threaded analysis unchanged (same performance characteristics)

## Next Steps

1. Integrate into CI/CD pipeline via `inv test`
2. Update documentation to describe new Calc columns
3. Consider adding Calc Path lookup feature (find existing matching folders)
4. Monitor performance on large photo libraries (10k+ files)

## Success Criteria Met

- ✅ All 18 CSV columns present in output (15 existing + 3 new Calc columns)
- ✅ Calc Date correctly implements spec logic (Name Date → Calc Date)
- ✅ Calc Filename matches format: YYYY-MM-DD_HHMM_WIDTHxHEIGHT_PARENT_BASENAME.EXT
- ✅ Calc Path matches format: <decade>/<year>/<year>-<month>/<parent>/<calc_filename>
- ✅ Test coverage 91% for image_analyzer.py (exceeds 80% target)
- ✅ No runtime errors with edge cases
- ✅ CSV output validates against schema (all rows have 18 columns)
- ✅ AUDIT log entries maintained (one per file)
- ✅ Real photo analysis (415 files) succeeded without errors
- ✅ All user clarification questions addressed and implemented
