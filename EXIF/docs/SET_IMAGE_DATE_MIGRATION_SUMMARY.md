# Summary: set_empty_dates.py vs set_image_dates.py & CSV Workflows

## Overview
This document summarizes the similarities, differences, and CSV workflows for the scripts `set_empty_dates.py` and `set_image_dates.py` in the EXIF project. It also provides recommendations for reconciling their functionality into a single, standardized script using the COMMON framework and argument conventions.

---

## Script Purposes

### set_empty_dates.py
- **Purpose:** Sets `DateTimeOriginal` for images missing this field.
- **Input:**
  - Scans a target folder for images missing the date, or
  - Accepts a CSV file with a column of file paths.
- **Date Source:** Infers the date from image metadata or filename if missing.
- **EXIF Update:** Sets only `DateTimeOriginal`.

### set_image_dates.py
- **Purpose:** Updates EXIF dates in images based on a CSV input specifying the desired date for each image.
- **Input:**
  - Requires a CSV file with columns for file path and date to set.
- **Date Source:** Uses the date provided in the CSV.
- **EXIF Update:** Sets multiple fields (`DateTimeOriginal`, `ExifIFD:DateTimeOriginal`, `XMP-photoshop:DateCreated`, `FileModifyDate`).
- **Extra:** Can fix file extensions based on actual file type.

---

## CSV File Formats

### set_empty_dates.py
- **Required Columns:** Only a file path column (default: `file`, configurable via `--file-column`).
- **Date Column:** Not required; date is inferred by the script.
- **Producer:** No specific script produces CSVs for this; any CSV with a file path column suffices.

### set_image_dates.py
- **Required Columns:**
  - `Source Path` (file path to image; configurable via `--file-col`)
  - `Set Date` (date to set; configurable via `--date-col`)
- **Producer:** `analyze.py` script generates the CSV, including an empty `Set Date` column for user input.
- **Workflow:**
  1. Run `analyze.py` to generate CSV.
  2. User fills in `Set Date` for images needing updates.
  3. Run `set_image_dates.py` to apply changes.

---

## Argument Patterns & Frameworks
- Both scripts should use the standardized argument naming and parsing conventions described in the attached prompts:
  - `--input` for input file (CSV)
  - `--source` for source directory
  - `--target` for target/output directory
  - `--output` for output file
  - `--dry-run` for simulation
- Arguments should be defined in a centralized, consistent way using the COMMON `ScriptArgumentParser` framework.
- Logging and summary output should use the COMMON logging utilities.

---

## Recommendations for a Unified Script

### 1. Standardize Arguments
- Use the COMMON argument pattern for all inputs:
  - `--input` (CSV file)
  - `--source` (source directory, optional)
  - `--target` (target directory, optional)
  - `--file-col` (CSV column for file paths, default: `Source Path`)
  - `--date-col` (CSV column for dates, default: `Set Date`)
  - `--dry-run` (simulate changes)

### 2. Unified CSV Handling
- Accept a CSV file with at least a file path column.
- If a date column is present and filled, use it to set the date.
- If the date column is missing or empty, infer the date from metadata or filename (as in `set_empty_dates.py`).
- Log actions and skipped files consistently.

### 3. EXIF Update Logic
- For each image:
  - If a date is provided in the CSV, set all relevant EXIF fields.
  - If no date is provided, attempt to infer and set `DateTimeOriginal` only.
- Optionally, add file extension correction as in `set_image_dates.py`.

### 4. Leverage COMMON Frameworks
- Use `ScriptArgumentParser` for argument parsing and validation.
- Use COMMON logging for consistent audit trails.
- Encapsulate business logic in a class in `src/exif`.

### 5. Documentation & Help Output
- Ensure the script description, arguments, and options are clearly defined at the top of the file and match the `--help` output.
- Follow the template in `example_script.py` for structure and clarity.

### 6. Testing & Migration
- Update or create tests to cover both workflows (date from CSV and date inference).
- Remove legacy scripts after migration and ensure all references and tests use the new script and argument names.

---

## Example Unified Workflow
1. Run `analyze.py` to generate a CSV of images.
2. Optionally fill in the `Set Date` column for images needing specific dates.
3. Run the unified script:
   ```bash
   python set_image_dates.py --input analysis.csv --dry-run
   ```
   - The script will set dates from the CSV where provided, and infer dates for others.

---

## Conclusion
Reconciling these scripts into a single, standardized CLI tool will:
- Simplify user workflows
- Reduce code duplication
- Ensure consistent argument handling and logging
- Make future maintenance and enhancements easier

**Next Steps:**
- Refactor both scripts into a single script using the COMMON framework and argument standards.
- Update documentation and tests to reflect the new unified workflow.
