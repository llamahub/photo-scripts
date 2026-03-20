# WORKFLOW Script Implementation Plan

Date: 2026-03-16

## Objective

Implement the WORKFLOW project as the orchestration layer for a media-library pipeline that:

- organizes incoming files into a normalized staging structure
- identifies duplicates before merge
- renames and merges assets into target libraries
- extracts metadata from files and Immich into a shared cache
- round-trips selected metadata between cache, CSV, files, and Immich
- exposes queue and rescan operations for operational control

This plan is based on the WORKFLOW spec in IMMICH/.github/prompts/WORKFLOW.md and on existing IMMICH implementations that already solve part of the problem.

## Existing IMMICH Precedents To Reuse

### Direct or near-direct ports

- immich_scan
  - Closest precedent: IMMICH/scripts/rescan.py
  - Supporting modules: IMMICH/src/immich_config.py, IMMICH/src/immich_connection.py
  - Expected effort: low

- immich_queues
  - Closest precedent: IMMICH/scripts/check_queues.py
  - Supporting modules: IMMICH/src/queue_checker.py, IMMICH/src/immich_connection.py, IMMICH/src/immich_config.py
  - Expected effort: low

- immich_to_cache
  - Closest precedent: IMMICH/scripts/cache.py
  - Supporting modules: IMMICH/src/immich_cache.py, IMMICH/src/immich_connection.py, IMMICH/src/file_matcher.py
  - Expected effort: medium because WORKFLOW cache needs a broader schema than IMMICH cache.py currently supports

### Concepts to reuse, but not direct ports

- files_to_cache
  - Closest precedent: IMMICH analyze/update/naming-policy work, not a direct single script
  - Reusable pieces: IMMICH/src/image_analyzer.py, IMMICH/src/naming_policy.py
  - Expected effort: high because WORKFLOW wants cache output, not CSV-only analysis

- cache_to_csv and csv_to_cache
  - Closest precedent: analyze.py CSV output and update.py CSV-driven mutation flow
  - Reusable pieces: CSV column selection and selected-row semantics from IMMICH update workflows
  - Expected effort: medium

- cache_to_files
  - Closest precedent: IMMICH/scripts/update.py and IMMICH/src/image_updater.py
  - Reusable pieces: EXIF update flow, rename/move semantics, sidecar handling patterns, audit logging expectations
  - Expected effort: high because the input source becomes WORKFLOW cache instead of analyze CSV

- files_rename
  - Closest precedent: IMMICH naming-policy plus updater rename flow
  - Reusable pieces: IMMICH/src/naming_policy.py and ImageUpdater-style audit logging
  - Expected effort: medium to high

- cache_to_immich
  - Closest precedent: none as a finished script, but IMMICH connection code provides the API integration base
  - Reusable pieces: IMMICH/src/immich_connection.py
  - Expected effort: high

### Net-new workflows

- files_organize
- files_dedup
- files_merge
- csv_select

These do not appear to have direct finished equivalents in IMMICH and will require new business modules.

## Recommended Delivery Order

The current spec describes a complete workflow system. Implementing all scripts independently would duplicate parsing, naming, and cache logic. The lowest-risk order is to build the shared model first and then layer scripts on top.

### Phase 1: Shared foundations

Create the core modules that all later scripts depend on.

Recommended modules in WORKFLOW/src:

- workflow_config.py
  - configuration for Immich access, cache defaults, and path conventions

- asset_record.py
  - canonical in-memory representation of one asset across file, sidecar, EXIF, cache, and Immich data

- naming_policy.py
  - centralized filename/path/event calculation rules
  - reuse IMMICH/src/naming_policy.py patterns, but adapt to the WORKFLOW spec naming format

- date_policy.py
  - consistent precedence rules for folder, filename, EXIF, sidecar, and Immich dates/times
  - keep this separate from naming policy so organize/rename/cache flows do not each invent their own date resolution

- sidecar_handler.py
  - discover sidecars
  - parse supported sidecar metadata
  - move/rename sidecars with parent assets

- workflow_cache.py
  - storage, CRUD, indexing, serialization, and cache migration/versioning
  - broaden IMMICH/src/immich_cache.py into a generalized cache with file-derived and Immich-derived fields

- file_matcher.py
  - generalized matching between cache records, files, and Immich assets
  - can start from IMMICH/src/file_matcher.py

### Phase 2: Operational Immich parity

Implement the low-risk scripts that already exist in IMMICH and validate WORKFLOW's Immich configuration/setup.

- immich_scan
- immich_queues
- immich_to_cache

Reason for doing these first:

- they validate Immich auth/config early
- they provide an initial cache population mechanism
- they reuse the most existing code

### Phase 3: File analysis and cache reporting

Implement the scripts that make the cache inspectable and editable before any file mutations happen.

- files_to_cache
- cache_to_csv
- csv_select
- csv_to_cache

Reason for doing these before file mutations:

- they let the workflow be observed and validated with no destructive operations
- they define the stable cache schema and CSV view model that later scripts will depend on

### Phase 4: File mutation workflows

Implement the filesystem-changing scripts only after naming, cache, and sidecar logic are stable.

- files_organize
- files_rename
- files_merge
- files_dedup
- cache_to_files

Reason for this order:

- files_organize creates the staging structure
- files_rename depends on stable naming policy
- files_merge depends on stable event/folder-limit logic
- files_dedup depends on confidence and sidecar movement rules
- cache_to_files depends on the cache already being authoritative enough to drive mutations

### Phase 5: Immich write-back

Implement cache_to_immich last.

Reason:

- it depends on the cache schema being final enough to represent albums, people, descriptions, and rename/delete outcomes
- it will need the most confirmation around destructive or state-changing behavior in Immich

## Script-By-Script Plan

### 1. files_organize

Purpose:

- copy raw source files into a normalized organized staging tree while keeping original filenames
- derive organized date and event folder before rename/merge

Business modules needed:

- date_policy.py
- event_policy.py or naming_policy.py event helpers
- sidecar_handler.py
- organize_service.py

Implementation notes:

- treat folder-limit logic as a shared service because files_merge uses it too
- do not bake event-folder sequencing separately into organize and merge
- emit AUDIT per asset and per sidecar move/copy decision

Test needs:

- parent-folder event detection
- month fallback event creation
- folder limit rollover
- sidecar copy behavior
- mixed image/video handling

### 2. files_dedup

Purpose:

- identify duplicates between organized staging and target library, then move dup candidates to a dups tree

Business modules needed:

- duplicate_finder.py
- sidecar_handler.py
- dedup_service.py

Implementation notes:

- keep duplicate-identification engine abstracted so dupGuru can be swapped or mocked
- do not hard-wire UI-driven dupGuru output parsing into the CLI script itself

Test needs:

- confidence threshold filtering
- sidecar co-movement
- destination tree preservation
- no-op behavior when no duplicates exist

### 3. files_rename

Purpose:

- rename files in place to the target filename convention
- support undo using AUDIT log output

Business modules needed:

- naming_policy.py
- rename_service.py
- audit_log_reader.py

Implementation notes:

- reuse the naming-policy centralization idea already established in IMMICH
- design undo around explicit old_path/new_path audit entries rather than trying to infer history from filenames later

Test needs:

- convention-compliant names do not get doubled
- undo restores original names
- sidecars rename consistently with parent asset

### 4. files_merge

Purpose:

- move organized assets into the canonical library tree while honoring folder limits and sidecars

Business modules needed:

- naming_policy.py
- folder_allocator.py
- merge_service.py
- sidecar_handler.py

Implementation notes:

- folder-allocation logic should be shared with files_organize where possible
- merge must decide whether target folder reuse versus sequence rollover is based on assets only, not sidecars

Test needs:

- merge into existing folder below limit
- create new seq folder above limit
- preserve relative structure for sidecars

### 5. files_to_cache

Purpose:

- extract filesystem-derived, sidecar-derived, and EXIF-derived metadata into WORKFLOW cache

Business modules needed:

- workflow_cache.py
- file_inventory.py
- exif_reader.py or adaptation of existing image analyzer logic
- sidecar_handler.py
- naming_policy.py
- date_policy.py

Implementation notes:

- this should become the main file-side cache population path
- unlike IMMICH analyze.py, output should be structured cache first and CSV secondarily through cache_to_csv

Test needs:

- field population for folder, filename, EXIF, sidecar, and calculated fields
- stable asset identifier generation
- repeated runs update/merge cache correctly

### 6. cache_to_csv

Purpose:

- render cache records to CSV using configurable views

Business modules needed:

- workflow_cache.py
- csv_views.py
- cache_reporter.py

Implementation notes:

- implement view definitions in code as a mapping, not spread across scripts
- include identifier column first and Select column early for manual review workflows

Test needs:

- default view
- custom view lookup
- missing view handling
- output path defaulting

### 7. csv_select

Purpose:

- extract selected asset identifiers from CSV and emit a filtered JSON payload

Business modules needed:

- csv_selection.py
- workflow_cache.py or a lightweight selector service

Implementation notes:

- normalize supported truthy values once in a shared helper used by csv_select and csv_to_cache

Test needs:

- selected-row filtering
- default input behavior
- output JSON structure

### 8. csv_to_cache

Purpose:

- apply human-reviewed CSV edits back into the cache

Business modules needed:

- workflow_cache.py
- csv_importer.py

Implementation notes:

- define which CSV columns are writable versus read-only before implementation begins
- preserve provenance so cache-to-files and cache-to-Immich know which values came from manual edits

Test needs:

- select-only update behavior
- --all override
- field normalization rules

### 9. cache_to_files

Purpose:

- apply cache-derived metadata and path/name decisions back onto library files

Business modules needed:

- workflow_cache.py
- file_update_service.py
- exif_writer.py
- sidecar_handler.py

Implementation notes:

- this is the WORKFLOW equivalent of IMMICH update flow, but the source of truth is cache rather than an analyze CSV
- albums-in-description formatting should live in one helper to keep file and Immich writes consistent

Test needs:

- EXIF updates
- rename/move execution
- album-prefix formatting
- cache selection logic when using --last or explicit cache

### 10. immich_to_cache

Purpose:

- populate or refresh cache fields from Immich

Business modules needed:

- workflow_cache.py
- immich_connection.py
- immich_import_service.py

Implementation notes:

- start by reusing the structure of IMMICH/scripts/cache.py, but do not keep the schema Immich-specific
- this should enrich existing asset records rather than build a separate parallel cache

Test needs:

- before/after validation
- album/people toggles
- daily cache default behavior
- merge semantics when cache already contains file-derived data

### 11. cache_to_immich

Purpose:

- push approved cache metadata back into Immich

Business modules needed:

- immich_connection.py
- immich_update_service.py
- workflow_cache.py

Implementation notes:

- treat renamed/deleted file reconciliation separately from metadata updates
- keep destructive behavior opt-in and audit-logged

Test needs:

- album updates
- people updates
- renamed-file reconciliation
- partial-failure handling

### 12. immich_scan

Purpose:

- trigger Immich rescan

Plan:

- port IMMICH/scripts/rescan.py nearly directly
- reuse config and connection modules
- confirm whether WORKFLOW should preserve library listing mode

### 13. immich_queues

Purpose:

- report and optionally wait for queue idle state

Plan:

- port IMMICH/scripts/check_queues.py and IMMICH/src/queue_checker.py nearly directly
- preserve return code semantics for idle versus active state

## Recommended Initial Module Set In WORKFLOW/src

Keep the first implementation pass focused. A practical initial set is:

- workflow_config.py
- workflow_cache.py
- immich_connection.py
- queue_checker.py
- naming_policy.py
- date_policy.py
- sidecar_handler.py
- file_matcher.py
- organize_service.py
- merge_service.py
- rename_service.py
- file_update_service.py
- csv_views.py

Additional modules like duplicate_finder.py or immich_update_service.py can be introduced once the corresponding scripts are ready.

## Test Strategy

Mirror IMMICH's split between business-class tests and script-level tests.

Recommended WORKFLOW tests:

- test_workflow_cache.py
- test_naming_policy.py
- test_date_policy.py
- test_sidecar_handler.py
- test_file_matcher.py
- test_queue_checker.py
- test_immich_connection.py
- test_organize_service.py
- test_merge_service.py
- test_rename_service.py
- test_file_update_service.py
- test_csv_views.py
- test_files_to_cache_script.py
- test_cache_to_csv_script.py
- test_csv_select_script.py
- test_csv_to_cache_script.py
- test_cache_to_files_script.py
- test_immich_to_cache_script.py
- test_immich_scan_script.py
- test_immich_queues_script.py

Integration fixtures should include:

- image files with and without EXIF
- matching sidecar files
- duplicate candidates
- event-folder examples with and without dates
- cache snapshots
- mocked Immich API payloads for albums and people

## Spec Gaps That Affect The Plan

The current spec is directionally strong, but it is not yet implementation-complete. These gaps are large enough that coding all scripts immediately would create rework:

- cache storage format is not explicitly fixed even though many scripts depend on it
- unique asset identifier is required by several scripts but not defined
- sidecar formats are referenced but not enumerated
- duplicate-identification engine and exact confidence semantics are not fixed
- date precedence mentions folder, filename, EXIF, but later calculated fields also include sidecar and Immich
- image and video libraries are described as separate on disk, but CLI argument strategy for that split is not defined
- cache_to_immich behavior is underspecified compared with the other scripts
- immich_scan says "same as rescan.py" but the exact library-selection behavior still needs confirmation

## Recommendation Before Coding

Do not start by writing all thirteen scripts. Start with:

1. Finalize the shared cache schema and identifier strategy.
2. Finalize naming/date/event rules in reusable policy modules.
3. Port the low-risk Immich operational scripts.
4. Implement files_to_cache and cache_to_csv as the first non-destructive WORKFLOW-native scripts.
5. Only then implement rename/merge/file update flows.

This keeps the early iterations observable and reduces the chance of mutating files based on unstable policy logic.