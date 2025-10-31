**IMPORTANT**: Follow ALL guidelines in [new_script.md](new_script.md)

* **Script Name**: set_empty_dates.py
* **Bus Logic Classes**: EmptyDateManager, ImageData
* **Description**: Sets the original date for all images in a target folder where this date is currently not set.

## Arguments ##
--target (positional and named, required) = root folder to scan and update images in
--dry-run log updates but do not action

## Business Logic ##
For each image file in --target (and it sub-folders), use EXIF tool to check if DateTimeOriginal is populated.

If not, then please use the following to calculate the date to set for this field in this priority order:

    src/ImageData.getImageDate()
    src/ImageData.getFilenameDate()

