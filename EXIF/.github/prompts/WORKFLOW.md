
[WORKFLOW.md] Document Photo Scripts Worflows
================================================================================

## Workflow Steps

**organize:** Move images from source into target folder with standard folder structure:

* uses prioritized date extracted from EXIF/filesystem/filename
* decade = 2000+, 2010+, 2020+, etc
* structure = {decade}/{YYYY}/{YYYY-MM}/{Parent Folder}/{Filename}.{ext}

```jsonc
. run organize mnt/server_drive2/images-originals/{source} /mnt/photo_drive/images-originals/{target}
```

**find_dups:** Compare against target library and highlight filename dups

```jsonc
. run find_dups /mnt/photo_drive/images-originals/{source} /mnt/photo_drive/santee-images
```

**delete_dups:** Delete duplicate files based on CSV ouptut from find_dups
```jsonc
. run delete_dups {input.csv} --status-col match_type --status-val "Exact match" --dry-run
```

**rename** Rename image files to match standard pattern:

* filename = {year}-{month}-{day}_{hour}{minute}{labelPart}_{width}x{height}{parentPart}_{baseName}.{trueExt}

```jsonc
. run rename {source}
```

## Austin & McKenna Video


```bash
# organize
. run organize mnt/server_drive2/images-originals/Austin_and_McKenna /mnt/photo_drive/images-originals/Austin_and_McKenna

# find_dups
. run find_dups /mnt/photo_drive/images-originals/Austin_and_McKenna /mnt/photo_drive/santee-images --output /mnt/photo_drive/AandM_dups.csv

# delete_dups
. run delete_dups /mnt/photo_drive/AandM_dups.csv --status-col match_type --status-val "Exact match" --dry-run


```

## TBD ##
[ ] video vs pics


## Other Workflows

organize
find_dups (by name)
delete_dups

rename 
analyze
set_image_dates

dupguru
dupgremove

immich_extract


ORGANIZE: {originals} --> {interim}
- break down into folder structure
- split folders > threshold # of images

REMOVE DUPS: {interim} vs {lbrary} --> {dups}
- find dups by filename relative to library
- USER REVIEW - update CSV
- remove dups per user input in CSV

- find dups via dupguru
- USER REVIEW - in dupguru CSV
- remove dups per user input in CSV

STANDARDIZE NAMES & DATES: {interim}
- analyze EXIF, File Dates, Filename
- USER REVIEW - update CSV
- rename and set EXIF dates pre user input in CSV

MERGE: {interim} --> {library}

IMMICH: User update descriptions, labels and/or dates

SYNC:
- extract dates, labels and descriptions from immich and sync in EXIF
