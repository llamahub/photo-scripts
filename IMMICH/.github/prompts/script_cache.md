[cache] Script to extract metadata from Immich into a cache and map it to files in target folder
--------------------------------------------------------------------------------

**Script Name:** cache.py

## Purpose
- This script will be similar to EXIF/scripts/immich_extract.py but only extracts information from Immich to a cache and maps it to files in target library folder.   It will NOT actually update any files in the target library.

## Refrences:
[new_script.prompt.md](new_script.prompt.md) - please follow instructions in this file to set up this new script in alignment with project standards

[immich_extract](../../../EXIF/scripts/immich_extract.py) - use this for inspiration but want make sure new implementation is cleaner and simpler - and focused only on adding/updating metadata in the cache.  Use the same authentication mechanisms via .env file variables to connect to Immich


## Business Classes

- create a immich_cache.py file with ImmichCache class that can be used for CRUD operations to Immich cache
- Should be able to easily load/save this class from/to the immich cache file

- create a immich_connection.py file with ImmichConnnection class that can be used for connecting to and extracting data from Immich and storing it in ImmichCache

- please confirm before adding or leveraging any other business classes

- make sure to add unit test coverage for these classes

## Arguments:

**--target**: (positional/named/required) - root of library to search for files that match the filepath of each asset

**--cache**: (named/optional) path to metadata cache.  default this to ./log/cache_{target folder name without path}.json
**--clear**: (named/optional) clears cache before extracting info.  Otherwise the default is to add/update the cache with new metadata.

#### These arguments can be combined to restrict the criteria for assets extracted from Immich

**--before**: only extract assests modified before ISO date/time (e.g., 2025-06-30T00:00:00Z)
**--after**: only extract assests modified after ISO date/time (e.g., 2025-06-30T00:00:00Z)
**--album**: only extract assets with this album id


## Cache Structure

- Cache file should be a json tree structure that contains a single node for each asset extracted from Immich in the it's original format
- Each node should also include a mapping to the full filepath of a confirmed matched file (at the date of when the node was added to the cache).  If no match was found then this can be empty
- structure of the full tree should be optimized so that it nodes can easily be found by future runs of the script and by other scripts that would search for immich info related to a specific matched file by either filename, filepath, exif date, tag or album
- Would like to be able to later easily add additional scripts that update this cache with other exif info from the mapped files and/or use this cache to update assets metadata in Immich via the Immich API.




# Chat Clarifications

File Matching Strategy
The script will use a multi-stage matching approach:

Extract filename from Immich originalFileName
Search target directory for files matching that name
If multiple matches, compare EXIF dates to identify best match
Record match confidence and method used
Test Coverage Required
test_immich_cache.py
Load/save operations
Add/update assets
Index rebuilding
Search operations (by filename, path, album, tag)
Clear cache
Statistics generation
test_immich_connection.py
Mock Immich API responses
Pagination handling
Date filtering (before/after)
Album filtering
Connection validation
Error handling (network issues, auth failures)
test_cache_script.py
Argument parsing validation
Full workflow integration tests
Cache file creation
Update existing cache
Clear cache behavior
ISO date validation
Questions Requiring Confirmation
⚠️ 1. Authentication Mechanism
The existing immich_extract.py uses ImmichConfig from EXIF project. Should I:

Option A: Create a new ImmichConfig in IMMICH/src
Option B: Use environment variables directly (.env file)
Option C: Import from COMMON (if we want shared config)
Recommendation: Option A - create IMMICH-specific config for independence

⚠️ 2. File Matching Disambiguation
When multiple files have the same name in target directory:

Option A: Match by EXIF date comparison (preferred)
Option B: Use file size as tiebreaker
Option C: Store all ambiguous matches, require manual resolution
Option D: All of the above in sequence
Recommendation: Option D - try in order: EXIF date → file size → flag ambiguous

⚠️ 3. Cache Update Behavior
When updating existing cache without --clear:

Option A: Only add new assets, never modify existing ones
Option B: Update assets if Immich updatedAt is newer
Option C: Always overwrite with latest data from Immich
Recommendation: Option B - update if newer (respects Immich as source of truth)

⚠️ 4. Index Structure
Should indices be:

Option A: Built-in to main cache file (as shown above)
Option B: Separate index files for performance
Option C: Built on-the-fly when cache is loaded (not persisted)
Recommendation: Option C - rebuild on load (simpler, always consistent)

⚠️ 5. Date Validation
For --before and --after arguments:

Option A: Accept date only (YYYY-MM-DD) and full ISO 8601
Option B: Require full ISO 8601 only (consistent with immich_extract)
Option C: Accept multiple formats with parsing
Recommendation: Option B - consistent with existing script, clear expectations

⚠️ 6. Dependency on EXIF Project Code
Should this script depend on EXIF project classes like ImageAnalyzer for EXIF reading?

Option A: Yes, import from EXIF for consistency
Option B: No, create independent EXIF reading in IMMICH
Option C: Use COMMON for shared EXIF utilities
Recommendation: Option A - reuse existing battle-tested code, add EXIF to path

⚠️ 7. Logging Strategy
For AUDIT-level logging:

Option A: One AUDIT message per asset processed (status: found/not_found/ambiguous)
Option B: Only log significant events (errors, ambiguous matches)
Option C: Log summary statistics only
Recommendation: Option A - aligns with project standard for file processing

Implementation Order
✅ Create immich_connection.py with tests
✅ Create immich_cache.py with tests
✅ Create cache.py script following COMMON patterns
✅ Add integration tests
✅ Document usage in README
Please confirm the answers to the 7 questions above before I proceed with implementation. I want to ensure we make the right architectural decisions upfront.

Claude Sonnet 4.5 • 1x

1. Option A: Create a new ImmichConfig in IMMICH/src
2 Option A: Match by EXIF date comparison (preferred)
3. Option B: Update assets if Immich updatedAt is newer
4. Option C: Built on-the-fly when cache is loaded (not persisted)
5. Option B: Require full ISO 8601 only (consistent with immich_extract)
6. Option B: No, create independent EXIF reading in IMMICH
7. Option A: One AUDIT message per asset processed (status: found/not_found/ambiguous)