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

**files_extract:**
- extract info from files (filename + EXIF) to cache
- similar to [analyze.py](../../scripts/analyze.py) but to cache, not csv
- cache should include some unique identifier of each asset
- Arguments:
    - --source: (positional/named) *{files_library}* root folder
      --cache: (optional) path to cache default to .cache/cache_{YYYY-MM-DD} use a new cache for each day

**cache_report:**
- ouput contents of cache to .csv file
- script should have a map of views to field names that can be expanded as required.  default view will be named "default"
- csv should include identifier field that can be used to easily find assets from cache
- default view should inlude empty "Select" column follwed by unique identifier, folder_path, filename, ... others TBD
- Arguments:
    - --cache: (optional) path to cache default to.cache/cache_{YYYY-MM-DD} use a new cache for each day
    - --output: (optional) path to output file.  default to .log/cache_report_{timestamp}.csv
    - --view: (optional) view name that determines which fields to include. (default to "default")
    
**cache_select:**
- extract subset of cache JSON baed on list of asset identifiers marked as selected in input .csv file
- Arguments:
    - --input: (positional/named/optional) path to .csv file (default to last run cache_report in .log)
    - --cache: (optional) path to cache default to.cache/cache_{YYYY-MM-DD} use a new cache for each day
    - --output: (optional) path to output file.  default to .log/cache_select_{timestamp}.json


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

## Cache fields to iclude for each asset

last_extract_status - match, error
last_extract_file_action - move, rename, keep
last_extract_exif_action - update

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
