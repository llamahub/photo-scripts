# Photo Scripts Monorepo

A Python monorepo framework for photo processing tools with shared infrastructure and consistent patterns.

## Quick Start

```bash
cd EXIF/                    # Navigate to any project
./setenv --recreate         # Create virtual environment
source activate.sh          # Activate environment
inv r -n sample -a '--help' # Run scripts with shortcut syntax
```

## Documentation Structure

- **[.vscode/ai-assistant-prompt.md](.vscode/ai-assistant-prompt.md)** - **Primary AI assistant guide** with patterns and templates
- **[DEVELOPMENT_HISTORY.md](DEVELOPMENT_HISTORY.md)** - Project context and architectural decisions
- **[COMMON/ARCHITECTURE.md](COMMON/ARCHITECTURE.md)** - Technical framework details
- **[EXIF/scripts/SAMPLE_EVOLUTION.md](EXIF/scripts/SAMPLE_EVOLUTION.md)** - Script development case study
- **[photo-scripts.code-workspace](photo-scripts.code-workspace)** - VS Code workspace configuration

## Core Framework

### Shared Infrastructure (COMMON/)
- **ScriptLogging**: `ScriptLogging.get_script_logger()` for consistent logging
- **Task System**: Shared invoke tasks with project extensions
- **Script Runner**: Universal script execution (`inv r -n script -a 'args'`)
- **Configuration**: Environment-based config management

### Standard Script Pattern
```python
# Standard import and setup pattern
from common.logging import ScriptLogging
logger = ScriptLogging.get_script_logger(name="script_name", debug=True)
```

## Current Projects

- **EXIF/**: Image metadata processing (`sample.py`, `image_data.py`)
- **COMMON/**: Shared infrastructure and framework

## Quick Reference

```bash
# Environment Management
./setenv --recreate    # Create fresh environment
source activate.sh     # Activate current environment

# Script Execution (three ways)
inv r -n sample -a '--help'                        # Shortcut
invoke run --script sample --args '--help'         # Traditional
python ../COMMON/scripts/run.py sample --help      # Direct

# Common Tasks
inv setup    # Project setup
inv test     # Run tests with coverage
inv lint     # Code quality checks
inv scripts  # List available scripts
```

For detailed information, see the linked documentation files above.