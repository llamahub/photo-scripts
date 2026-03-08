# Naming Policy Plan

Date: 2026-02-15

## Goal
Centralize the filename and folder naming rules used by analyze/update/cache so the same normalized convention is applied everywhere.

## Current Naming Convention (Baseline)
- Filename: YYYY-MM-DD_HHMM_WIDTHxHEIGHT_PARENT_BASENAME.ext
- Path: root/<decade+>/<year>/<year-month>/<parent_desc>/

## Plan
1. Create shared naming policy module
   - Introduce naming_policy.py with pure functions for:
     - calc filename
     - calc path
     - calc status (MATCH/RENAME/MOVE)
     - parent_desc and basename normalization
     - filename normalization tweaks (date prefix, double underscore cleanup)

2. Refactor analyzer to use naming policy
   - Replace internal filename/path/status builders with NamingPolicy calls.
   - Keep analyzer outputs unchanged (behavior parity).

3. Refactor updater to use naming policy
   - Replace calc filename normalization with NamingPolicy.normalize_calc_filename.

4. Extend cache schema to store normalized fields
   - Store calc_date, calc_time, calc_filename, calc_path, calc_status, parent_desc, basename.
   - Use these fields as the golden source for both filesystem and Immich updates.

5. Add tests for naming policy
   - Cover: date parsing, placeholder handling, basename cleanup, parent_desc handling, and move/rename status.
   - Verify consistency with existing analyze/update expectations.

## Notes
- No fallback logic added. Errors should surface when inputs are missing or ambiguous.
- Any changes to naming rules should be applied only in naming_policy.py to avoid drift.
