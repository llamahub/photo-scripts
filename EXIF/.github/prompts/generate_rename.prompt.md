---
mode: agent
---

consider all relevant documentation linked to in the README.md file at the root level of this monorepo, including but not limited to the main documentation hub at docs/README.md, the setup guide at docs/setup/SETUP_GUIDE.md, the COMMON framework documentation at COMMON/docs/README.md, and the EXIF tools documentation at EXIF/docs/README.md.

create a script called rename.py in EXIF/scripts/ that renames photos based on their EXIF metadata. the script should use the COMMON framework for shared functionality and follow the established patterns in the EXIF tools documentation. ensure the script can handle common edge cases, such as missing metadata or duplicate filenames.  IF a duplicate filename is detected, append a suffix with this fornat to the new filename to avoid overwriting existing files:

_DUP_{current datetimestamp}

leverage the getTargetFilename of the image_data module in EXIF/ to determine the new filename based on the EXIF metadata. implement logging using the ScriptLogging class from the COMMON framework to provide detailed information about the renaming process, including successes and failures.

I also need the script to detect if the existing filename already matches the target filename format and validate if the EXIF metadata in the existing filename is incorrect or incomplete. if the existing filename is not correct, then the script should rename the file to match the correct format based on the EXIF metadata.

make sure to include a --dry-run option that allows users to see what changes would be made without actually renaming any files. also, include a --help option that provides usage information.

