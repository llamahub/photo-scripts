# Implementation Plan: Calc Columns for analyze.py

## Executive Summary

Add three calculated columns to the CSV output of `analyze.py`:
1. **Calc Date** - Intelligent date selection using file's oldest reliable date
2. **Calc Filename** - Normalized filename with metadata-based naming convention  
3. **Calc Path** - Organized folder structure matching photo organization pattern

## Current State

**ImageAnalyzer** currently outputs 15 columns:
- Filenanme, Folder Date, Filename Date, Sidecar File
- Sidecar Date/Offset/Timezone/Description/Tags
- EXIF Date/Offset/Timezone/Description/Tags
- EXIF Ext

Missing: Calc Date, Calc Filename, Calc Path

## Requirements Analysis

### Calc Date Logic (from script_analyze.md)

**Name Date** (intermediate calculation):
```
IF month(Filename Date) == month(Folder Date) THEN
    return Filename Date
ELSE IF year(Folder Date) < year(Filename Date) THEN
    return Folder Date
ELSE
    return Filename Date
```

**Calc Date** (final calculation):
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
- Uses Calc Date for date prefix (YYYY-MM-DD_HHMM)
- Requires image dimensions (WIDTH x HEIGHT)
- PARENT = parent folder name
- BASENAME = original filename without extension
- EXT = exif_ext from ImageAnalyzer

### Calc Path Format
```
<decade>/<year>/<year>-<month>/<parent event folder>/<calc_filename>
```
- decade = YYYY0+ (e.g., 2020+, 2010+)
- year = 4-digit year
- year-month = YYYY-MM
- parent folder = source file's parent directory name
- filename = Calc Filename

## Key Insights from EXIF Project

The EXIF project (image_data.py, photo_organizer.py) provides useful patterns:

1. **Date Normalization**: Already handled by existing `_extract_folder_date()` and `_extract_filename_date()`

2. **Month/Year Extraction**: Can extract using string slicing (YYYY-MM = date_str[:7], YYYY = date_str[:4])

3. **Image Dimensions**: EXIF field "ImageWidth" and "ImageHeight" available via exiftool

4. **Decade Calculation**: `decade = (year // 10) * 10` then format as f"{decade}+"

5. **Normalized Filename**: Photo organizer uses pattern: `YYYY-MM-DD_HHMM_WIDTHxHEIGHT_PARENT_BASENAME.EXT`

## Implementation Strategy

### Phase 1: Core Calculation Methods (ImageAnalyzer class)

Add 5 new private methods to ImageAnalyzer:

#### 1. `_get_year_month(date_str: str) -> Optional[str]`
- Extract YYYY-MM from date string
- Return None if date is "0000-00-00" or empty
- Return None if date starts with "1900" (marker for invalid/missing)

#### 2. `_calculate_name_date(folder_date: str, filename_date: str) -> str`
- Implements "Name Date" logic from spec
- Compares month and year of folder_date vs filename_date
- Returns selected date string (YYYY-MM-DD format)

#### 3. `_calculate_calc_date(exif_date: str, name_date: str) -> str`
- Implements "Calc Date" logic from spec
- Checks if EXIF date is valid and <= name date
- Handles empty/zero-padded dates gracefully
- Returns selected date string (YYYY-MM-DD format)

#### 4. `_get_image_dimensions(image_exif: Dict) -> str`
- Extracts ImageWidth and ImageHeight from exif dict
- Returns formatted string: "WIDTHxHEIGHT"
- Returns "0x0" if not available

#### 5. `_calculate_calc_filename(calc_date: str, image_exif: Dict, parent_folder: str, original_filename: str, ext: str) -> str`
- Builds normalized filename: YYYY-MM-DD_HHMM_WIDTHxHEIGHT_PARENT_BASENAME.EXT
- Extracts date (YYYY-MM-DD) and time (HHMM) from calc_date
- Gets dimensions via `_get_image_dimensions()`
- Uses parent_folder and original filename stem
- Returns formatted string

#### 6. `_calculate_calc_path(calc_date: str, parent_folder: str, calc_filename: str) -> str`
- Builds path: <decade>/<year>/<year>-<month>/<parent>/<calc_filename>
- Extracts year from calc_date, calculates decade
- Returns path string (relative, not searching filesystem)
- Example: `2020+/2023/2023-10/MyEvent/2023-10-15_1430_1920x1080_MyEvent_IMG_4120.jpg`

### Phase 2: Update ImageRow Dataclass

Add 3 fields to ImageRow:
```python
@dataclass
class ImageRow:
    # ... existing 15 fields ...
    calc_date: str
    calc_filename: str
    calc_path: str
```

### Phase 3: Update ImageAnalyzer._analyze_file()

In `_analyze_file()` method, after building image_row values:

```python
# Calculate derived fields
name_date = self._calculate_name_date(folder_date, filename_date)
calc_date = self._calculate_calc_date(exif_date, name_date)
calc_filename = self._calculate_calc_filename(
    calc_date, 
    image_exif, 
    file_path.parent.name,
    file_path.stem,
    exif_ext
)
calc_path = self._calculate_calc_path(
    calc_date,
    file_path.parent.name,
    calc_filename
)

return ImageRow(
    # ... existing 15 fields ...
    calc_date=calc_date,
    calc_filename=calc_filename,
    calc_path=calc_path,
)
```

### Phase 4: Update CSV Headers and Row Mapping

Update `_csv_headers()`:
```python
def _csv_headers(self) -> List[str]:
    return [
        # ... existing 15 headers ...
        "Calc Date",
        "Calc Filename",
        "Calc Path",
    ]
```

Update `_row_to_dict()`:
```python
def _row_to_dict(self, row: ImageRow) -> Dict[str, str]:
    return {
        # ... existing 15 mappings ...
        "Calc Date": row.calc_date,
        "Calc Filename": row.calc_filename,
        "Calc Path": row.calc_path,
    }
```

### Phase 5: Test-Driven Development

Create comprehensive tests in `test_image_analyzer.py`:

#### Test Cases for _calculate_name_date()
- Same month and year: use filename_date
- Folder year < filename year: use folder_date
- Different month, same year: use filename_date
- Folder date with 00-00: edge cases
- Both dates invalid (00-00): return empty or null

#### Test Cases for _calculate_calc_date()
- EXIF date <= Name date: use EXIF date
- EXIF date > Name date: use Name date
- EXIF date empty: use Name date
- EXIF date invalid (1900-01-01 or 0000-00-00): use Name date

#### Test Cases for _get_image_dimensions()
- Image with width/height: "1920x1080"
- Image without dimensions: "0x0"
- Exif dict empty: "0x0"

#### Test Cases for _calculate_calc_filename()
- Full data available: "2023-10-15_1430_1920x1080_MyEvent_IMG_4120.jpg"
- Missing parent folder: skip in path
- Missing dimensions: "0x0" in path
- Edge cases with special characters in parent/basename

#### Test Cases for _calculate_calc_path()
- Standard case: "2020+/2023/2023-10/MyEvent/calc_filename"
- Parent with spaces/special chars: properly formatted
- Different decade calculations (2010s, 2020s, 1990s, etc.)

#### Integration Tests
- Full row calculation with real EXIF data
- CSV output includes all 18 columns with Calc columns populated

## Edge Cases and Considerations

### Date Handling
- **Empty/Missing dates**: Treat "0000-00-00", "1900-01-01", "" as invalid
- **Partial dates**: "2023-00-00" is treated as valid partial date, compare only available parts
- **Date comparison**: Compare as strings (YYYY-MM-DD sorts correctly lexicographically)

### Filename/Path Calculation
- **Special characters**: Need to handle parent folder names with spaces, punctuation, etc.
- **Unicode**: Parent folder names may contain unicode characters
- **Path separators**: Use "/" for Calc Path (OS-independent representation)
- **Lookup**: Calc Path is a *calculated* path format, NOT required to exist on filesystem

### Performance
- Date parsing/comparison is lightweight string operations
- Image dimension extraction already happens via exiftool (no added calls)
- No filesystem lookups required for Calc Path
- No performance impact expected

## Clarifications Needed

**Q1: Date Comparison Logic**
- When comparing EXIF Date to Name Date in `_calculate_calc_date()`, should we compare:
  - **Option A**: Full datetime including time component (e.g., "2023-10-15 14:30" vs "2023-10-15 00:00")?
  - **Option B**: Only date part ignoring time (e.g., just "2023-10-15")?
  - Current spec shows "date({EXIF Date}) <= date({Name Date})" suggesting date-only comparison

Answer: use Option B - I'm assuming if EXIF date is same day then the time is probably as accurate or more than the filename time.

**Q2: Parent Folder Naming**
- Should Calc Path always include the parent folder, or skip if parent is numeric (like "2023", "2023-10")?
- Example: For file in "2023-10-Events/IMG_4120.jpg", should Calc Path include "2023-10-Events" or skip it?

Answer: keep the parent folder if it has any non date text in it. so include "2023-10-Event" but if parent was just "2023-10" or "2023-10-01" then skip it.

IMPORTANT: I don't want to duplicate parent folder, height/width, etc in the filename - so need to intelligently strip these out of the "BASE NAME" of the file if they already exist.

**Q3: Width x Height Format**
- Should dimensions be padded (e.g., "1920x1080" vs "1920x 1080") or always as-is from EXIF?
- Should missing dimensions show "0x0" or be blank/omitted?

Anwer: padded is preferred.  If dimensions are missing from EXIF - can we get them from the image directly?

**Q4: Parent Folder Extraction**
- Should parent folder name be the immediate parent directory name, or processed (e.g., cleaned of dates/special chars)?
- Example: For "2023-10-vacation/IMG_4120.jpg", use "2023-10-vacation" or extract "vacation"?

Answer: see above - use "2023-10-vacation" but don't use parent if there is no non date text in the folder name.

**Q5: Timestamp in Calc Filename**
- Should HHMM be extracted from Calc Date's time component, or always "0000" if Calc Date only has date part?
- What if Calc Date comes from folder/filename with no time information?

Answer: If calc date has HHMM then use it, but otherwise use 0000

**Q6: Test Coverage**
- Should we test with real exiftool output (integration tests) or mock it (unit tests)?
- What's the target test coverage % for the new methods?

Answer: yes, use real exiftool

## Files to Modify

1. **[image_analyzer.py](src/image_analyzer.py)** (primary)
   - Add ImageRow fields (calc_date, calc_filename, calc_path)
   - Add 6 new private methods for calculations
   - Update _analyze_file() to compute and assign Calc fields
   - Update _csv_headers() to include Calc columns
   - Update _row_to_dict() to map Calc columns

2. **[test_image_analyzer.py](tests/test_image_analyzer.py)** (new tests)
   - 15+ new test functions covering calculation methods
   - Integration tests verifying CSV output

## Success Criteria

- [ ] All 18 CSV columns present in output (15 existing + 3 new Calc columns)
- [ ] Calc Date correctly implements spec logic (Name Date → Calc Date)
- [ ] Calc Filename matches format: YYYY-MM-DD_HHMM_WIDTHxHEIGHT_PARENT_BASENAME.EXT
- [ ] Calc Path matches format: <decade>/<year>/<year>-<month>/<parent>/<calc_filename>
- [ ] Test coverage >80% for image_analyzer.py
- [ ] No runtime errors with edge cases (missing dates, special characters, etc.)
- [ ] CSV output validates against schema (all rows have 18 columns, proper types)
- [ ] Audit log entries maintained (one per file)

## Estimated Effort

- **Calculation methods**: 2-3 hours (straightforward string/date logic)
- **Integration into _analyze_file()**: 0.5-1 hour
- **CSV header updates**: 0.25 hour
- **Test development**: 3-4 hours (comprehensive coverage)
- **Documentation & cleanup**: 1 hour
- **Total**: ~7-9 hours of development

## Next Steps

1. **User to clarify** Q1-Q6 above
2. **Development** following TDD approach (tests first)
3. **Integration** into existing test suite
4. **Validation** against real photo library data
5. **Documentation** update to reflect new columns
