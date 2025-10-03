# Photo Scripts AI Assistant Prompt

You are working on the **photo-scripts** monorepo, a Python framework for photo processing tools with shared infrastructure.

## Project Context

This is a **monorepo architecture** with:
- **COMMON/**: Shared infrastructure (logging, tasks, config, script runner)
- **EXIF/**: Image metadata processing project  
- **Future projects**: Will follow the same pattern

## Key Architectural Principles

1. **Consistency over Convenience**: Use established patterns even if custom solutions seem easier
2. **Graceful Degradation**: Always provide fallbacks (especially for COMMON imports)
3. **DRY**: Use shared COMMON infrastructure instead of duplicating code
4. **Test-Driven**: Maintain comprehensive test coverage (aim for >95%)

## Standard Patterns

### Script Development Template
```python
#!/usr/bin/env python3
"""Clear script description."""

import sys, argparse
from pathlib import Path
from datetime import datetime

# Standard COMMON import pattern - ALWAYS use this
common_src_path = Path(__file__).parent.parent.parent / 'COMMON' / 'src'
sys.path.insert(0, str(common_src_path))

try:
    from common.logging import ScriptLogging
except ImportError:
    import logging
    ScriptLogging = None

def main():
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()
    
    # Standard logging setup - ALWAYS use this pattern
    if ScriptLogging:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        logger = ScriptLogging.get_script_logger(
            name=f"script_{timestamp}",
            debug=args.debug
        )
    else:
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("script")
    
    logger.info("Starting script")
    try:
        # Script logic here
        logger.info("Script completed successfully")
    except Exception as e:
        logger.error(f"Script failed: {e}")
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
```

### Error Handling Pattern
```python
try:
    # Risky operation
except SpecificError as e:
    logger.warning(f"Handled gracefully: {e}")
    # Provide fallback
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Decide: continue or fail
```

### Testing Pattern
- Use pytest with fixtures
- Test both success and failure cases
- Mock external dependencies
- Maintain >95% coverage

## Framework Components

### ScriptLogging (REQUIRED for all scripts)
```python
from common.logging import ScriptLogging
logger = ScriptLogging.get_script_logger(name="script_name", debug=True)
```
**Features**: Console + file output, timestamped files, proper formatting

### Shared Tasks (tasks.py pattern)
```python
# Project tasks.py extends COMMON
from common_tasks import *  # Import ALL shared tasks
@task
def project_specific_task(c):  # Add project-specific tasks
    """Project-specific task."""
    pass
```

### Script Execution (Three Methods)
1. `inv r -n script -a 'args'` (preferred shortcut)
2. `invoke run --script script --args 'args'` (traditional)
3. `python ../COMMON/scripts/run.py script args` (direct)

## Code Quality Requirements

### Type Hints
- Use for ALL function parameters and return values
- Import from `typing` when needed
- Use `Path` for filesystem paths, not strings

### Logging Levels
- `DEBUG`: Detailed debugging info
- `INFO`: Progress and completion messages  
- `WARNING`: Unexpected but recoverable issues
- `ERROR`: Failures that prevent completion

### Documentation
- Docstrings for classes and public methods
- Clear parameter descriptions
- Usage examples in help text

## Common Tasks

```bash
# Environment
./setenv --recreate    # Fresh environment
source activate.sh     # Activate environment

# Development
inv setup             # Project setup
inv test              # Tests with coverage
inv lint              # Code quality
inv clean             # Clean artifacts

# Scripts
inv scripts           # List available scripts
inv r -n script -a 'args'  # Run script (shortcut)
```

## File Locations

- **Documentation**: See README.md for current structure (single source of truth)
- **Architecture**: `COMMON/ARCHITECTURE.md` for technical details
- **History**: `DEVELOPMENT_HISTORY.md` for context and decisions
- **Examples**: `EXIF/scripts/` for working examples

## Critical Patterns

### ALWAYS Use These Patterns
1. **Import COMMON**: Use the standard import pattern above
2. **ScriptLogging**: Never use print() - always use the logger
3. **Fallbacks**: Provide graceful degradation for missing COMMON
4. **Type Hints**: Full type annotations
5. **Error Handling**: Specific exceptions with logging

### NEVER Do These Things
1. Don't duplicate functionality that exists in COMMON
2. Don't use relative imports across project boundaries
3. Don't mix print() with logger calls
4. Don't catch Exception without logging
5. Don't modify system Python - use virtual environments

## Project Extension

### Adding New Scripts
1. Use standard script template above
2. Add to project's `scripts/` directory
3. Follow naming convention
4. Write comprehensive tests

### Adding New Projects  
1. Copy structure from EXIF/
2. Update `pyproject.toml` with project name/deps
3. Create `tasks.py` extending common_tasks
4. Add project modules to `src/project_name/`

## Key Files to Reference

When working on this project, regularly reference:
- `DEVELOPMENT_HISTORY.md` - Why decisions were made
- `COMMON/ARCHITECTURE.md` - How components work
- `EXIF/scripts/sample.py` - Working example
- `EXIF/scripts/example_script.py` - Simple template

Remember: This framework prioritizes **consistency** and **maintainability** over quick solutions. Follow established patterns even if custom approaches seem faster.