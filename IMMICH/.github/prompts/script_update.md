
## Script Details:

script name:  update.py
description:  updates files selected from output csv file from analyze script

args: --input (positional/named/optional) - path to csv file (created by analyze script)
      --last (named/optional) - use latest analyze output csv file from .log 

log file: ./.log/update_{timestamp}.log

business class(es):
 src/image_analyzer.py = ImageAnalyzer (if required)
 src/image_updater.py = ImageUpdater for making changes to files

scan the input csv file for "Selected" or "Select" column and process any rows marked "Y" or "YES" (any capitalization) or TRUE

update all relevant Exif Data to use:
    Calc Date
    Calc Offset (prefer Calc Offset; otherwise derive from Calc Timezone and Calc Date)
    Calc Description
    Calc Tags

If Calc Status = "RENAME" then rename the file to match {Calc Filename}
If Calc Status = "MOVE" then move/rename the file to match {Calc Path}/{Calc Filename}

