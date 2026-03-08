
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


## New Script Structure

files_organize:         group files by <decade>/<YYYY>/<YYYY-MM>/{<event>||<YYYY-MM-DD>}
                        Not more than 50 files in a folder
                        check for duplicates

files_extract:          files --> cache (similar to analyze.py - but to cache, not csv)
                        -- target (positional / named) - path to target root folder

    cache_report:       cache --> csv (similar output to analyze.py - but from cache - not files)
    cache_select:       csv --> asset list json (output list of asset identifiers from cache based on those selected in csv)
                        -- input (positional / named)
                        -- last (use csv from last cache_report run)

files_update:           cache --> files
                        -- assets {asset list json}
                        -- last (use asset list from last cache_select run)

immich_extract:         immich --> cache
                        -- albums
                        -- people
                        -- all. (includes albums and people)
                        -- assets {asset list json}
                        -- last (use asset list from last cache_select run)

immich_update:          cache --> immich - updates immich database:
                        * removes renamed files
                        * adds/udpdate albums based on [] names in exif description
                        * adds/updates people based on exif people
                        

immich_scan:            files --> immich.  (same as rescan.py)

immich_queues:          check queues (same as check_queues.py)
                        -- wait {# seconds} (default to 10 seconds)


selected - Y, yes, YES, Yes = pull for selection
extract_status - match, error
action_file - move, rename, keep
action_exif - update

folder_path - full path of parent folder of file on disk
folder_date - date extracted from parent folder name (YYYY-MM-DD or YYYY-MM-01 or YYYY-01-01)
folder_event - event extracted from parent folder name

file_hash - caclulate at time of file_extract
filename - name of file on disk (without path)
filename_date
filename_time
filename_event
filename_width
filename_height

sidecar_path
sidecar_name
sidecar_ext
sidecar_date
sidecar_time
sidecar_offset
sidecar_timezone
sidecar_description
sidecar_tags
sidecar_albums?
sidecar_people?

exif_ext
exif_date
exif_time
exif_offset
exif_timezone
exif_description
exif_tags

immich_path
immich_name
immich_ext
immich_date
immich_time
immich_offset
immich_timezone
immich_description
immich_tags
immich_albums
immich_people

calc_date_source - filename, folder, exif, sidecar, immich
calc_time_source - filename, folder, exif, sidecar, immich
calc_name_source 
calc_album_source - exif, immich
calc_people_source - exif, immich

calc_path - calculated path to target parent folder in format: <decade>/<YYYY>/<YYYY-MM>/{<event>||<YYYY-MM-DD>}
calc_name - calculated filename in format: <YYYY-MM-DD_HHM>_<width>x<height>_<event>_<basename>.<ext>
calc_ext - calculated "true" extension

calc_date - date based on naming policy
calc_time - time based on naming policy
calc_offset - offset based on naming policy
calc_timezone - timezone calculated from calc_date + calc_offset using map
calc_description - description excluding albums, people
calc_tags - unduplicated (case sensitive) set of tags
calc_albums - list of albums the asset is associated with
calc_people - list of people (name + id) the asset is associated with
