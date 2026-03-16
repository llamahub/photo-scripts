## Objectives
- Image files in a *{files_library}* to be maintained in a standardized chronological folder structure with standardized naming convention that signals critical metadata about the image asset.  (date,time,height,width,event, original filename)
- All critical metadata captured into the files themselves (via EXIF) so that the file becomes the golden source with EXIF data matching the data that is in the filename.
- Scripts can be run to organize, de-dup and merge incoming bactches of images into the *{files_librarty}* ensuring that existing files are not overwritten or duplicated in the library but new files are updated to fit the structure, naming convention and EXIF info standard patterns.
- An Immich instance with an external library pointed at *{files_librarty}* can be used to view the images and update tags, description, date, albums and people.
- Changes made in Immich can be extracted into a *{cache}* that can act as a central place for scripts to compare,  match and update files vs to match Immich.
- If files are changed/renamed then updates to Immich database can be made and re-scan of library triggered.
- Video files can be handled by all the same scripts but stored in a separate *{files_library}* with the same structure and naming conventions.   These files can also be seen and modified in Immich (and even combined in albums) but mantained separately on disk.

## Component Architecture

```
files_source --> files_organized --> files_library (images)
                                 --> files_library (video)
             --> files_dups

files_library <--> cache <--> Immich    
```

- *{files_source}*: Root folder of incoming image and/or video files: eg., from google photos, or directly from a camera.  (can contain sub-folders in any structure)

- *{files_organized}*: copy of *{files_source}* organized by *{files_library}* [folder structure](#library-folder-structure)

- *{files_dups}*: files removed from *{files_organized}* that are confirmed as duplicates already existing in ** {files_library}*

- *{files_library}*: target library of assets and sidecar files stored in standardized folder structure with standardized naming convention.   Goal is ultimately to have all relavant metadata (date, time, tz, tags, descriptionm albums, people, etc.) stored within the EXIF tags of the asset files themelves.  Note: plan to have a separate libraries for videos vs images.

- *{cache}*: cache of all relevant metadata extracted/derived from *{files_library}* and *{Immich}*:

- *{Immich}*: Immich instance running with an external library pointed to each *{files_library}*


## Library Folder Structure

The target library folder structure is: ```{decade}/{year}/{month}/{event}```

- *{decade}*: Format = YYYYMM+ (starting with beginning year of decade - e.g., "1990+", "2000+", "2010+")

- *{year}*: Format = YYYY

- *{month}*: Format = YYYY-MM (if month is unknown, it can be 00)

- *{event}*: Should follow this format: *{event start date}* *{source label}* *{event title}{seq number}*

    - *{event start date}*: format of YYYY-MM or YYYY-MM-DD

    - *{source label}*: optional label that can be provided when importing assets from a new source

    - *{event title}*: optional free text name of the event

    - *{seq number}*: optional suffix with "_" + two digit seq number ("_02", "_03", etc) used to break up event folders so that no more than a target # of assets are in one folder

## Library Filename Convention

The target filename convention is: ```{date}_{time}_{width}x{height}_{event}_{basename}.{ext}```

- *{date}*: format = YYYY-MM-DD, calculatd based on [date precedence logic](#date-precedence-logic)
- *{time}*: format = HHMM, calculated ased on [date precedence logic](#date-precedence-logic)
- *{width}*: width of image per EXIF
- *{heigh}*: height of image per EXIF
- *{event}*: event name determined by parent folder name
- *{basename}*: original filename witout extension
- *{ext}*: EXIF "true" extension

## Date Precedence Logic
- folder
- filename
- EXIF

## New Script Structure

**files_organize:**
- copy files from *{files_source}* to *{files_organized}* following *{files_library}* [folder structure](#library-folder-structure)
- Not more than the limit of assets in a folder
- keep original filenames
- also copy any related sidecar files (sidecar files don't count against folder limit)
- calculate *{organized_date}* based on *{files_source}* folder name, filename and exif dates following standard [date precedence logic](#date-precedence-logic)
- derive *{event}* from one of the following:
    - If immediate parent folder of the asset looks like an event name (other than a pure date) then use it.  Examples:
        - YYYY-MM-DD or YYYY-MM followed by text description
        - A text name that does not have a date
    - Otherwise use the month of the cacluated *{organized_date}* (and label if provided) to determine the *{event}*.
        - If more than the limit of assets exist for the month (+ label)- then break down month into multple events with *{seq number}*
        - Keep assets in chronological order by cacluated *{organized_date}*
        - Don't create extra events if not necessary
- Arguments:
    - --source: (positional/named) *{files_source}* root folder
    - --target: (positional/named) *{files_organized}* root folder
    - --label: (optional)  *{source label}* to use in event names
    - --folder_limit: (optional) limit # of assets per folder (default this to 50)

**files_dedup:**
- move files from *{files_organized}* to *{files_dups}* which are identified as potential duplicates of assets in *{files_library}*
- make sure to also move related sidecar files along with the assets
- keep the same folder structure under *{files_dups}* matching that in *{files_organized}*
- potentially use [dupGuru](https://dupeguru.voltaicideas.net/) to identify duplicates
- Arguments:
    - --source: (positional/named) *{files_organized}* root folder
    - --target: (positional/named) *{files_library}* root folder
    - --dups: (optional) *{files_dups}* root folder (default to: "*{files_organized}*_dups")
    - --confidence: (optional) target confidence threshold for duplicate identification (default to 100%)

**files_rename:**
- rename files in a source folder structure to match *{files_library}* [naming convention](#library-filename-convention)
- capture [AUDIT] messages in log for each file renamed
- be able to undo a given run by reading [AUDIT] messages from the log
- make sure that rename doesn't recurively embed original filenames that already match the convention:
    - need smart logic to extract
- Arguments:
    - --source: (positional/named) root folder
    - --label: (optional) label to include in event names

**files_merge:**
- merge files from *{files_organized}* to *{files_library}*
- locates the logical target folder in target library where each file should be placed based on folder structure](#library-folder-structure)
- if existing target folder does not exist, create it and any required parent folders
- if existing target folder exists and this will push # of assets in the folder above limit - then create new target folder with new seq # to keep # of assets under limit
- moves the file from *{files_organized}* to target subfolder.
- make sure to include any related sidecar files along with the assets
- Arguments:
    - --source: (positional/named) *{files_organized}* root folder
    - --target: (positional/named) *{files_library}* root folder
    - --folder_limit: (optional) limit # of assets per folder (default this to 50)

**files_to_cache:**
- extract info from *{files_library}* (folder name, filename and EXIF data) to *{cache}*
- similar to [analyze.py](../../scripts/analyze.py) but to cache, not csv
- cache should include some unique identifier of each asset
- Arguments:
    - --source: (positional/named) *{files_library}* root folder
    - --cache: (optional) path to cache - default to .cache/cache_{YYYY-MM-DD} use a new cache for each day

**cache_to_csv:**
- ouput contents of *{cache}* to .csv file
- script should have a map of views to field names that can be expanded as required.  default view will be named "default"
- csv should include identifier field that can be used to easily find assets from cache
- default view should inlude empty "Select" column follwed by unique identifier, folder_path, filename, ... others TBD
- Arguments:
    - --cache: (optional) path to cache - default to .cache/cache_{YYYY-MM-DD} use a new cache for each day
    - --output: (optional) path to output file.  default to .log/cash_to_csv_{timestamp}.csv
    - --view: (optional) view name that determines which fields to include. (default to "default")
    
**csv_select:**
- extract subset of cache JSON baed on list of asset identifiers marked as selected in input .csv file
- Arguments:
    - --input: (positional/named/optional) path to .csv file (default to last run cache_report in .log)
    - --cache: (optional) path to cache default to.cache/cache_{YYYY-MM-DD} use a new cache for each day
    - --output: (optional) path to output file.  default to .log/cache_select_{timestamp}.json -->

**csv_to_cache:**
- extract info from .csv file to update *{cache}*
- by default only update cache for records marked in .csv file as selected (Select column = "Y", "Yes", "YES" or TRUE)
- Arguments:
    - --input: (positional/named/optional) path to .csv file (default to last run cash_to_csv in .log)
    - --cache: (optional) path to cache default to.cache/cache_{YYYY-MM-DD} use a new cache for each day
    - --all: (optional) ignore Select field and extract info for all assets in the .csv file

**cache_to_files:**
- update files in *{files_library}* from data in *{cache}*
- adds/updates albums by adding bracketed list of albums as prefix to EXIF description: (e.g., [{album name1}], [{album name2}] {description})
- Arguments:
    - --target: (positional/named) *{files_library}* root folder
    - --cache: (optional) path to cache - default to .cache/cache_{YYYY-MM-DD} use a new cache for each day (or --last)
    - --last: (optional flag) if specified - use last csv_to_cache run in .log folder as the cache

**immich_to_cache:**
- extract info from *{Immich}*: to *{cache}*:
- similar to [cache.py](../../scripts/cache.py) 
- Arguments:
    - --cache: (optional) path to cache default to.cache/cache_{YYYY-MM-DD} use a new cache for each day
    - --album-name: (optional) Only extract assets for specific album name
    - --before: (optional) Only extract assets modified before ISO date/time (e.g., 2025-06-30T00:00:00Z)
    - --after: (optional) Only extract assets modified after ISO date/time (e.g., 2025-06-30T00:00:00Z)
    - --albums (optional flag) if specified - extract all album names for each asset
    - --people (optional flag) if specifide - extract all people for each asset
    - --all (optional flag) if specified - extra all album names and people for each asset

**cache_to_immich:**
- updates *{Immich}* database from *{cache}*
- removes any renamed files
- adds/updates albums
- adds/updates people
                        
**immich_scan:**
- same as [rescan.py](../../scripts/rescan.py)

**immich_queues:**
- same as [check_queues.py](../../scripts/check_queues.py)

## Cache fields to iclude for each asset

- *last_extract_status* - match, error
- *last_extract_file_action* - move, rename, keep
- *last_extract_exif_action* - update

### Folder derived fields:

- *folder_path* - full path of parent folder of file on disk
- *folder_date* - date extracted from parent folder name (YYYY-MM-DD or YYYY-MM-01 or YYYY-01-01)
- *folder_event* - event extracted from parent folder name

### Filename derived fields:

- *file_hash* - calculate at time of file_extract
- *filename* - name of file on disk (without path)
- *filename_date* - date extracted from filename
- *filename_time* - time extracted from filename
- *filename_event* - event extracted from filename
- *filename_width* - width extracted from filename
- *filename_height* - height extracted from filename

## Sidercar derived fields:

- *sidecar_path* - full path of sidecar file
- *sidecar_name* - name of sidecar file (without path)
- *sidecar_ext* - extension of sidecar file
- *sidecar_date* - date extracted from sidecar file
- *sidecar_time* - time extracted from sidecar file
- *sidecar_offset* - offset extracted from sidecar file
- *sidecar_timezone* - timezone extracted from sidecar file
- *sidecar_description* - description extracted from sidecar file
- *sidecar_tags* - tags extracted from sidecar file
- *sidecar_albums* - albums extracted from sidecar file
- *sidecar_people* - people extracted from sidecar file

## EXIF derived fields:

- *exif_ext* - extension extracted from EXIF data
- *exif_date* - date extracted from EXIF data
- *exif_time* - time extracted from EXIF data
- *exif_offset* - offset extracted from EXIF data
- *exif_timezone* - timezone extracted from EXIF data
- *exif_description* - description extracted from EXIF data
- *exif_tags* - tags extracted from EXIF data

## Immich derived fields:

- *immich_path* - full path of Immich file
- *immich_name* - name of Immich file (without path)
- *immich_ext* - extension of Immich file
- *immich_date* - date extracted from Immich data
- *immich_time* - time extracted from Immich data
- *immich_offset* - offset extracted from Immich data
- *immich_timezone* - timezone extracted from Immich data
- *immich_description* - description extracted from Immich data
- *immich_tags* - tags extracted from Immich data
- *immich_albums* - albums extracted from Immich data
- *immich_people* - people extracted from Immich data

## Calculated fields (based on last extracted data and naming policy logic):

- *calc_date_source* - filename, folder, exif, sidecar, immich
- *calc_time_source* - filename, folder, exif, sidecar, immich
- *calc_name_source* - filename, folder, exif, sidecar, immich
- *calc_album_source* - exif, immich
- *calc_people_source* - exif, immich

- *calc_path* - calculated path to target parent folder in format: <decade>/<YYYY>/<YYYY-MM>/{<event>||<YYYY-MM-DD>}
- *calc_name* - calculated filename in format: <YYYY-MM-DD_HHM>_<width>x<height>_<event>_<basename>.<ext>
- *calc_ext* - calculated "true" extension

- *calc_date* - date based on naming policy
- *calc_time* - time based on naming policy
- *calc_offset* - offset based on naming policy
- *calc_timezone* - timezone calculated from calc_date + calc_offset using map
- *calc_description* - description excluding albums, people
- *calc_tags* - unduplicated (case sensitive) set of tags
- *calc_albums* - list of albums the asset is associated with
- *calc_people* - list of people (name + id) the asset is associated with
