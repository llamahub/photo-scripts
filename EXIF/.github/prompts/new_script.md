[new_script] New script prompt template
--------------------------------------------------------------------------------

## Naming Conventions
- CLI script name should ideally be a single verb (ex: "analyze.py") or a two word action (ex: "move_folders.py")
- Business logic of the script should be contained in separate modules with object model classes

## CLI Script Structure

1. Script Header - follow pattern exactly as shown in example_script
    - script name should match file name
    - name/description in header should match what is passed to arg parser in SCRIPT_INFO

2. Imports
    - import common logging framework

3. Arguments
    - define all arguments in SCRIPT_ARGUMENTS
```

**CRITICAL**: All scripts MUST follow this standardized argument naming pattern:

### Core Argument Types:
- `--input` / `input` (positional) → Input file(s) or data source
- `--source` / `source` (positional) → Source directory or location  
- `--target` / `target` (named only) → Target/destination directory or output location
- `--output` / `output` (positional) → Output file(s) when different from target

### Standard Pattern Examples:
```python
# For scripts that process files from a directory:
'input': {
    'positional': True,
    'help': 'Input CSV/data file'
},
'source': {
    'positional': True,
    'help': 'Source directory containing files to process'
},
'target': {
    'flag': '--target',
    'help': 'Target directory for processed files'
}

# For scripts that generate output files:
'source': {
    'positional': True,
    'help': 'Source directory to analyze'
},
'output': {
    'positional': True,
    'help': 'Output file for results'
}
```

4. Entry point - main()
    - set up argument parser and resolve args
    - set up common logger and print standard header / configuration
    - execute main flow leveraging calls to business logic classes

5. Use COMMON framework for testing, logging and temp file manaerment

6. Ensure all business logic classes have unit tests and there are tests for the CLI script as well