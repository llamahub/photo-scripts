# WORKFLOW Cache Field Reference

This document lists cache fields written to the JSON cache file by WORKFLOW scripts and indicates where each field is populated or updated.

## Top-Level Structure

- `metadata`: Run-level information about cache lifecycle.
- `assets`: Dictionary of asset records keyed by an internal cache key.

### Assets Dictionary Key

- Key name: asset dictionary key (not a field inside each record)
- Purpose: Internal unique key for each asset record.
- Updated by: both
- Behavior:
  - `immich_to_cache`: inserts with `immich_asset_id`, or `immich_asset_id::path_key` on collision.
  - `files_to_cache`: inserts with `file_hash`.

## Metadata Fields

| Field | Purpose | Updated By |
|---|---|---|
| `metadata.created` | Timestamp when cache was first created. | both |
| `metadata.last_updated` | Timestamp of most recent save. | both |
| `metadata.total_assets` | Count of records currently in `assets`. | both |
| `metadata.source` | Legacy source marker; default initialized to `immich`. Not actively updated during merges. | neither |
| `metadata.source_path` | Source root directory used by files scan. | files_to_cache |

## Asset Record Fields

| Field | Purpose | Updated By |
|---|---|---|
| `path_key` | Canonical relative path key used for strict matching across sources. | both |
| `immich_asset_id` | Immich asset ID. | immich_to_cache |
| `immich_path` | Full path from Immich `originalPath`. | immich_to_cache |
| `immich_relative_path` | Immich path relative to configured library root. | immich_to_cache |
| `immich_name` | Original filename from Immich. | immich_to_cache |
| `immich_ext` | File extension derived from Immich filename. | immich_to_cache |
| `immich_date` | Date/time original or created timestamp from Immich metadata. | immich_to_cache |
| `immich_time` | Timezone string from Immich EXIF timezone field. | immich_to_cache |
| `immich_offset` | Offset time from Immich EXIF metadata. | immich_to_cache |
| `immich_timezone` | Timezone from Immich EXIF metadata. | immich_to_cache |
| `immich_description` | Immich description text. | immich_to_cache |
| `immich_tags` | Tag names from Immich metadata. | immich_to_cache |
| `immich_albums` | Album names (when album enrichment is enabled). | immich_to_cache |
| `immich_people` | People names (when people enrichment is enabled). | immich_to_cache |
| `raw` | Raw Immich asset payload snapshot. | immich_to_cache |
| `file_hash` | SHA-256 hash of local file content. | files_to_cache |
| `source_root` | Filesystem scan root path used for this record. | files_to_cache |
| `relative_path` | Relative path from `source_root` to file. | files_to_cache |
| `folder_path` | Full filesystem folder path for the file. | files_to_cache |
| `filename` | Local file name. | files_to_cache |
| `filename_date` | Parsed date from filename pattern. | files_to_cache |
| `filename_time` | Parsed time fragment from filename pattern. | files_to_cache |
| `folder_date` | Parsed date from folder naming pattern. | files_to_cache |
| `folder_event` | Parent folder name (event/context label). | files_to_cache |
| `exif_ext` | Lowercase extension from local file suffix. | files_to_cache |
| `last_extract_status` | Files extraction status marker (currently `match`). | files_to_cache |
| `last_extract_file_action` | Files extraction file action (currently `keep`). | files_to_cache |
| `last_extract_exif_action` | Files extraction EXIF action (currently `keep`). | files_to_cache |

## Notes

- Field updates are merge-based. If both sources touch the same `path_key`, the record is combined.
- `immich_to_cache` updates only when `path_key` exactly matches.
- `files_to_cache` updates by `path_key` first, then falls back to `file_hash` matching.
