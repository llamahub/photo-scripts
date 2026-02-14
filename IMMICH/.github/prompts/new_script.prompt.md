[new_script] Instructions for creating a new script
--------------------------------------------------------------------------------

## Monorepo structure:

COMMON contains shared code used by multiple projects.
{PROJECT} contains project-specific code and scripts with these subfolders:
  scripts
  src
    tests
  
## Naming Conventions
- CLI script name should ideally be a single verb (ex: "analyze.py") or a two word action (ex: "move_folders.py")
- Business logic of the script should be contained in separate modules with object model classes

## CLI Script Structure

1. Script Header - follow pattern exactly as shown in COMMON/scripts/example_script.py
  - script name should match file name
    - name/description in header should match what is passed to arg parser in SCRIPT_INFO
    - SCRIPT_INFO fields (see COMMON/scripts/example_script.py):
        - name: human-readable script name
        - description: short summary used by the CLI parser
        - examples: list of example CLI invocations
  - Do NOT duplicate the description and argument information in the header or comments - use the SCRIPT_INFO and SCRIPT_ARGUMENTS structures to define all of this information in a single place that can be easily parsed by developers and tools
  - Developer should be able to look at the header and arguments at the top of the script and understand what the script does, what arguments it takes and how to use it
  
2. When creating a new script for a specific project, follow these steps:
    - use COMMON/scripts/example_script.py as a template
  - place the new script in the {PROJECT}/scripts/ folder
  - ensure the script uses COMMON code where applicable - specifically for:
    - logging
    - argument parsing
    - configuration
    - temporary file management
    - testing framework

4. Entry point - main()
    - set up argument parser and resolve args
    - set up common logger and print standard header / configuration
    - execute main flow leveraging calls to business logic classes

6. Ensure all business logic classes have unit tests and there are tests for the CLI script as well


## Logging requirements

- All output sent to the console should use the COMMON logging framework
- Assume the common logging framework is available - do not need fallback for non-COMMON usage
- write tests for the new script in the {PROJECT}/tests/ folder
- Default log configuration should send INFO, WARN and ERROR messages to standard output
- AUDIT and DEBUG messages should be written to a log file
- AUDIT is a custom level between INFO and DEBUG and should not appear on the console
- For any scripts handling individual files (e.g. images, videos, documents), ensure an AUDIT log message is generated for each file processed, indicating success or failure and relevant info

##  Argument handling requirement

- define all arguments in SCRIPT_ARGUMENTS

**CRITICAL**: All scripts MUST follow this standardized argument naming pattern:

- Do not use argument aliases (multiple names for the same argument). Existing scripts may still have aliases, but new scripts should define a single name per argument.

main required arguments should be both positional and named where applicable. other optional arguments can be named-only, and should use the following core argument types where applicable:

### Core Argument Types:
- `--input` / `input` (positional) → Input file(s) or data source
- `--source` / `source` (positional) → Source directory or location  
- `--target` / `target` (named only) → Target/destination directory or output location
- `--output` / `output` (positional) → Output file(s) when different from target

### Standard Pattern Examples:
```python
# For scripts that process files from a directory:
'input': {
    'flag': '--input',
    'positional': True,
    'help': 'Input CSV/data file'
},
'source': {
    'flag': '--source',
    'positional': True,
    'help': 'Source directory containing files to process'
},
'target': {
    'flag': '--target',
    'help': 'Target directory for processed files'
}
}

# For scripts that generate output files:
'source': {
    'flag': '--source',
    'positional': True,
    'help': 'Source directory to analyze'
},
'output': {
    'flag': '--output',
    'positional': True,
    'help': 'Output file for results'
}
```

- Always include a --dry-run flag for scripts that modify or move files, to allow users to preview actions without making changes.

IMPORTANT: As a general rule - do NOT add fallback logic for missing information.  I would generally prefer to see meaningful errors rather than assumed logic.  If there is a question about whether a fallback would be helpful, pleae confirm it first before adding it. The goal is to keep the code as clean and simple as possible and avoid adding unnecessary complexity with multiple layers of fallback logic.  If there is a common scenario where users might forget to provide necessary information, we can consider adding validation checks that prompt the user to provide that information rather than trying to guess it in the code.