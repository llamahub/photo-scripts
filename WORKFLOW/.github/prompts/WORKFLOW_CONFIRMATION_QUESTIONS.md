# WORKFLOW Implementation Questions

Date: 2026-03-16

This document lists the open questions that should be confirmed before implementation begins. Several of the proposed WORKFLOW scripts depend on shared decisions about cache shape, naming rules, and mutation semantics. Without those answers, implementation will either drift or require later rewrites.

## Highest-Priority Questions

### 1. What is the phase-1 script set?

The spec describes a full workflow system. Please confirm whether the first delivery should include:

- all scripts in the spec
- only the direct IMMICH ports first
- only the non-destructive cache/reporting scripts first

Recommended default:

- phase 1 = immich_scan, immich_queues, immich_to_cache, files_to_cache, cache_to_csv

ANSWER: immich_to_cache, files_to_cache, then all scripts in the order they are proposed in [WORKFLOW.md](../../../IMMICH/.github/prompts/WORKFLOW.md)

### 2. What is the authoritative cache format?

Please confirm the persistent cache storage format:

- single JSON file per run/day
- single JSON file that is incrementally updated over time
- one JSON file plus derived on-load indices
- SQLite or another structured store

Recommended default:

- one JSON cache file with indices rebuilt on load, following the earlier IMMICH cache pattern but generalized for WORKFLOW

ANSWER: 

**Use SQLite as the operational cache backend with automatic JSON export/import.**

Rationale:
- SQLite provides excellent performance for 50K-500K assets with proper indexing
- No server overhead (just a file), perfect for script-based workflows
- Built into Python, zero dependencies
- Provides ACID compliance for reliable concurrent operations
- Simple backup (copy .db file)
- Easy JSON export/import for human-readable inspection and backup

Implementation:
```
WORKFLOW/cache/
├── workflow_cache.db          # SQLite operational cache
├── workflow_cache.json         # Auto-exported for inspection
└── backups/
    └── workflow_cache_YYYYMMDD.json  # Daily snapshots
```

Scripts operate on SQLite for performance, with automatic JSON export after significant operations. JSON import available for restore/migration. This is superior to Postgres (requires server) or MongoDB (adds complexity without clear benefits) for single-user script execution.


### 3. What is the unique asset identifier?

Several scripts depend on an identifier that survives CSV export/import and links files, cache, and Immich. Please confirm whether the identifier should be based on:

- file hash only
- relative path only
- file hash plus normalized filename/path
- Immich asset id when present, otherwise file hash

Recommended default:

- file hash as the stable file-side identifier, with separate immich_asset_id when available

ANSWER: **Use composite stable identifier: `{original_path}::{file_size}::{first_seen_hash}`**

Rationale:
- File hash WILL change when EXIF is modified or metadata is updated
- Need an identifier that survives content changes while still being somewhat debuggable
- Composite approach uses path + size + original hash from first encounter
- Supports tracking file moves via separate current_path field

Database schema approach:
```sql
asset_id TEXT PRIMARY KEY,     -- Composite: original_path::size::first_hash
file_hash TEXT,                 -- Current hash (updated when content changes)
original_path TEXT,             -- Path when first discovered
current_path TEXT,              -- Current location (tracks moves/renames)
immich_asset_id TEXT            -- Linkage to Immich when synced
```

This allows:
- Stable tracking even when EXIF/metadata changes the file hash
- Detection of intentional vs accidental content changes
- CSV round-trip with stable identifiers
- Audit trail of file modifications

### 4. What sidecar formats must be supported?

The spec refers to sidecar files repeatedly, but the accepted formats are not defined. Please confirm whether support is required for:

- XMP only
- JSON sidecars
- Google Photos sidecars
- custom sidecars already present in your libraries

This affects parsing, move/rename behavior, and test fixtures.

ANSWER: want to support all sidecar files we've handled so far (including all the above)

### 5. How should separate image and video libraries be handled?

The spec says images and videos are maintained in separate libraries. Please confirm whether scripts should:

- process one target library per invocation and rely on the caller to choose image versus video root
- detect media type and split outputs automatically
- accept separate --image-target and --video-target arguments

Recommended default:

- one target library per invocation to keep CLI behavior simple and explicit

ANSWER: yes - libraries will not be mixed on a given run of CLI script.   However, when extracting from Immich - we may need to filter out by type so video doesn't get mixed with image library.

## Naming And Date Policy Questions

### 6. What is the final date precedence rule?

The spec lists folder, filename, EXIF under Date Precedence Logic, but later calculated-field sections also reference sidecar and Immich. Please confirm:

- whether sidecar date outranks EXIF or only supplements it
- whether Immich date ever drives calc_date for file-system naming
- whether rename/merge should use the same precedence as cache extraction

Recommended default:

- separate extraction precedence from final naming precedence
- file naming should be based on file-side metadata only unless explicitly overridden

ANSWER: **Bidirectional sync with provenance tracking. Immich is the editing UI, files are the persistence layer.**

Core principle:
- Edit dates/metadata in Immich UI (comfortable, visual interface)
- Changes flow back to files via cache_to_files (files remain golden source)
- Cache tracks provenance to detect and propagate Immich edits

Date precedence for calculation:
```
1. Manual CSV edit (until persisted to file via cache_to_files)
2. Immich edit detected (user changed date in Immich UI)
3. Sidecar date (once sidecar read, it gets renamed/disabled)
4. EXIF date (file-native metadata)
5. Filename date (parsed from filename pattern)
6. Folder date (parsed from folder pattern)
```

Required cache fields for provenance:
```sql
-- Raw date sources
exif_date TEXT,
sidecar_date TEXT,
filename_date TEXT,
folder_date TEXT,
immich_date TEXT,

-- Calculated authoritative date
calc_date TEXT,
calc_time TEXT,

-- Provenance tracking
date_source TEXT,  -- 'manual_csv' | 'immich_edit' | 'sidecar' | 'exif' | 'filename' | 'folder'
date_modified_at TIMESTAMP,
immich_date_last_seen TEXT,
immich_date_changed BOOLEAN
```

Workflow example (user edits date in Immich):
1. immich_to_cache detects immich_date changed → sets date_source='immich_edit', calc_date=new_value
2. cache_to_files writes calc_date → EXIF and renames file
3. After write-back succeeds → date_source changes to 'exif' (now persisted)

This enables:
- Comfortable editing in Immich
- Files remain portable and backup-friendly
- Clear audit trail of where dates came from
- Conflict resolution based on timestamps when multiple sources change 
- yes sidecar date should outrank EXIF. but once side car info is added to cache I want to disable sidecar by renaming it.

### 7. How exactly is an event folder recognized?

The spec gives examples but not a strict parser. Please confirm:

- whether any parent folder containing text counts as an event
- how to treat folders like YYYY-MM, YYYY-MM-DD, YYYY-MM-DD Name, and arbitrary text
- whether event title normalization should preserve punctuation/case

Recommended default:

- recognize explicit dated event patterns first, then free-text folders, then fall back to month-based event generation

### 8. What is the exact filename normalization rule for files_rename?

Please confirm:

- how to detect an already-compliant filename
- how to recover the original basename if the convention is partially present
- whether basename normalization should remove duplicate date/event prefixes

Recommended default:

- centralize this in naming_policy.py and treat already-compliant names as no-op unless a calculated field differs

### 9. How should timezone be derived when offset is missing?

The spec mentions calculating timezone from date plus offset using a map. Please confirm:

- whether there is an existing canonical timezone map
- whether timezone should ever be inferred from folder or event context
- what to do when offset and timezone are both unavailable

Recommended default:

- do not guess timezone silently; store null/blank and surface it for review unless a defined mapping exists

## Filesystem Mutation Questions

### 10. What exactly counts toward folder_limit?

The spec says sidecars do not count in files_organize. Please confirm that the same rule applies to files_merge.

Recommended default:

- count primary assets only, never sidecars

### 11. How should conflicts be handled during merge or rename?

Please confirm what should happen if the target path already exists:

- fail and log an error
- compare hashes and skip if identical
- auto-sequence filename
- move conflicting source to a review folder

Recommended default:

- fail clearly unless duplicate logic has already classified the asset as safe to skip

### 12. How should undo work for files_rename?

The spec says undo should read AUDIT messages from the log. Please confirm:

- whether undo is a separate command or a flag on files_rename
- whether only the most recent run must be supported or arbitrary prior logs
- whether undo must also reverse sidecar renames/moves

Recommended default:

- separate undo mode on files_rename using explicit old/new path pairs from one chosen log file

### 13. What duplicate engine should files_dedup use?

The spec says it may use dupGuru. Please confirm whether dupGuru is:

- required
- optional when installed
- only inspiration for scoring, with a native Python matcher preferred

Recommended default:

- treat dupGuru integration as optional behind an abstraction, so the workflow is still testable without GUI tooling

## Cache And CSV Questions

### 14. Which cache fields are writable by csv_to_cache?

The spec describes many extracted and calculated fields, but not all should be user-editable. Please confirm which fields CSV edits are allowed to update:

- description
- tags
- albums
- people
- calculated date/time/path/name
- source-specific raw fields

Recommended default:

- allow edits only on curated writable fields, not raw extracted source fields

### 15. What are the initial cache_to_csv views?

The spec says there will be a default view plus expandable named views. Please confirm the initial required set:

- default only
- default plus file-review view
- default plus Immich-review view
- default plus dedup-review view

Recommended default:

- start with default, file_review, and immich_review

### 16. What is the precedence between --cache defaults and “last run” behavior?

Several scripts mention daily cache defaults while others mention using the last CSV or last run from .log. Please confirm the precedence rules for:

- csv_select
- csv_to_cache
- cache_to_files

Recommended default:

- explicit path wins
- explicit --last wins over daily default
- otherwise use the current-day cache default

## Immich Sync Questions

### 17. Should WORKFLOW reuse the IMMICH auth/config approach directly?

IMMICH already has immich_config.py and immich_connection.py. Please confirm whether WORKFLOW should:

- copy/adapt those modules into WORKFLOW
- import them directly from IMMICH
- move them into COMMON first

Recommended default:

- copy/adapt into WORKFLOW initially to keep the project self-contained, then consider promotion to COMMON later if multiple projects need the same code

### 18. What exactly should cache_to_immich do about renamed files?

The spec says it updates Immich, removes renamed files, and updates albums/people. Please confirm:

- whether it should delete stale asset records in Immich
- whether it should relink renamed files or rely on rescan
- whether album/people changes are additive only or fully synchronized

Recommended default:

- separate metadata update from renamed-file reconciliation, and keep destructive deletion opt-in

### 19. How should people be represented in cache?

The spec says calc_people is a list of people name + id. Please confirm:

- whether person ids are Immich-specific only
- whether manual CSV edits may add names without ids
- whether cache_to_immich should create missing people or only link existing ones

Related decision summary:

- See [WORKFLOW/.github/prompts/WORKFLOW_PEOPLE_XMP_DECISION.md](WORKFLOW/.github/prompts/WORKFLOW_PEOPLE_XMP_DECISION.md) for the current recommendation: use Iptc4xmpExt:PersonInImageWDetails as canonical, keep Iptc4xmpExt:PersonInImage in sync for compatibility, and store Immich IDs as namespaced URI/URN values (for example, urn:immich:{instance-id}:person:{person-id}).

### 20. Should immich_scan preserve the existing rescan.py UX?

IMMICH rescan.py currently supports listing libraries and rescanning a selected library id. Please confirm whether WORKFLOW immich_scan should:

- keep the same interface
- default to one configured library
- support separate image/video library aliases

Recommended default:

- preserve the existing list-and-select model unless there is already a stable library alias convention in your environment

## Suggested Confirmation Sequence

If you want the shortest path to implementation, the key answers to confirm first are:

1. phase-1 script set
2. cache format
3. asset identifier strategy
4. sidecar formats
5. date precedence for naming
6. duplicate engine choice
7. cache_to_immich write semantics

Once those are fixed, the implementation plan can be converted into a concrete delivery sequence with much lower risk of rework.