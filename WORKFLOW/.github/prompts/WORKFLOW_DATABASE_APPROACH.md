An alternate way to tackle this might be to have the cache be a database (POSTGRES or nosql - Mongo?) to ensure performance and keeping all data synced nicely.

a few important objectives I want to meet:

- I ultimately want the "golden source" of image and video metadata to be in the asset files themselves so that I could easily port these libraries to an entirely different platform if required, and so that all the metadata can be easily backed up along with the files themselves.

- I like the Immich interface for viewing, taggging and updating date/description/people/albums but I want the data to be captured in the files themselves so I'm not dependent on Immich long term

- I want a standard set of logic for naming and organizing the files based on dates (as well as event names and key metadata) but I want the ability to change those metadata fields from any of these:

    - rescan of file system dates and EXIF dates
    - sidecar file dates
    - extract from Immich API
    - bulk update of info in a .csv file that I can update in EXCEL

- I want a clean human readable file based backup of the cache that I can easily backup and restore - probably in JSON format

- I currently have 50K+ images in my library and growing.  I also have many videos that I want to view in Immich and organize the same way but I prefer to have them in a separate but parallel organized file structure following the same format

- I don't mind launching scripts that take a while to run but ideally want these scripts to be as optimized as possible so they can run relatively quickly and reliably.   I'm okay with spinning up a database just when the scripts run if it helps improve performance of those scripts.