
[WORKFLOW.md] Document Photo Scripts Worflows
================================================================================

## Workflow Steps

```bash
# link_photo_drive: Mount and link /mnt/photo_drive to remote or local storage
 ./run link_photo_drive --remote

# analyze: Gathers info on all files in image library and outputs to a CSV file:
./run analyze --source /mnt/photo_drive/santee-samples

# update: updates files selected from output csv file from analyze script
./run update --last --force --all --dry-run 

# cache: Extract metadata from Immich and cache with file mappings
./run cache /mnt/photo_drive/santee-samples --after 2026-02-15T00:00:00Z

# delete_unmatched: Delete unmatched assets from Immich library
 ./run delete_unmatched .log/cache_santee-samples.json --force --dry-run

# fix_deleted: Clear Immich deletion history to allow re-import of renamed files
 ./run fix_deleted --dry-run
```