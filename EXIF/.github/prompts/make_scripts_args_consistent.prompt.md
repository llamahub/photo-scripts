

I want each of my EXIF and COMMON scripts to use a consistent style and structure for defining and parsing command-line arguments.

I want to be able to open the CLI script file and immediately see near the top of the file with the exact same description of the scripts purpose, its arguments, and options as I would see if I ran the script with a --help argument.

I don't want to have to maintain two separate places where the arguments and options are described.

I like this format of script name and description to show both at the top of the file and on the command line when the script runs:

================================================================================
=== [{Script Name}] - {Brief Description of Script Purpose}
================================================================================

I want the arguments and options to be defined in a consistent way using argparse with similar names, structure, ordering, and formatting across all scripts.

All required arguments should be both positional and named arguments.

Consistent names should include:

--input for input file (e.g., CSV file)
--output for output file (e.g., modified CSV file)
--source for input source directory
--target for output target directory
--dry-run for simulating actions without making changes
--help for displaying help information

CLI scripts should have a consistent structure:

-- arguments define near the top of the file after the description (per above)
-- main() function to encapsulate script logic
-- business logic encapsulated in a separate class in src/exif or src/common modules
-- if __name__ == "__main__": main() at the bottom to invoke main function

I should be able to scroll quickly through any CLI script and immediately understand its purpose, arguments, and options and basic flow of execution just by looking at the top of the file and the main() function.

Logging setup and summary output should be consistent across all scripts leveraging common logging utilities where possible so that code in CLI script is very minimal and focused on argument parsing and invoking the main processing class.

the example_script.py file in COMMON and in EXIF should be set up to be used as the template for all other scripts to follow to ensure these standards are met.

