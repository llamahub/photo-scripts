# Photo Scripts Monorepo

A Python monorepo framework for photo processing tools with shared infrastructure and consistent patterns.

## Quick Start

### Option 1: Dev Container (Recommended)
```bash
# Open in VS Code with dev containers extension
# Dependencies install automatically via setup-system-deps.sh

cd EXIF/                    # Navigate to any project
./setenv --recreate         # Create virtual environment
source activate.sh          # Activate environment
inv r -n organize -a '--help' # Run scripts with shortcut syntax
```

### Option 2: Local Development
```bash
# Install system dependencies first
./setup-system-deps.sh      # Installs Python, ExifTool, etc.

cd EXIF/                    # Navigate to any project
./setenv --recreate         # Create virtual environment
source activate.sh          # Activate environment
inv r -n organize -a '--help' # Run scripts with shortcut syntax
```

## Documentation Structure

- **[.vscode/ai-assistant-prompt.md](.vscode/ai-assistant-prompt.md)** - **Primary AI assistant guide** with patterns and templates
- **[SETUP_TROUBLESHOOTING.md](SETUP_TROUBLESHOOTING.md)** - **System setup and dependency troubleshooting**
- **[DEVELOPMENT_HISTORY.md](DEVELOPMENT_HISTORY.md)** - Project context and architectural decisions
- **[COMMON/ARCHITECTURE.md](COMMON/ARCHITECTURE.md)** - Technical framework details
- **[EXIF/scripts/SAMPLE_EVOLUTION.md](EXIF/scripts/SAMPLE_EVOLUTION.md)** - Script development case study
- **[photo-scripts.code-workspace](photo-scripts.code-workspace)** - VS Code workspace configuration

## System Requirements

### Required Dependencies
- **Python 3.8+**: Core runtime environment
- **ExifTool**: EXIF metadata extraction (critical for photo organization)

### Automated Installation
Use the provided setup script to install all system dependencies:

```bash
./setup-system-deps.sh          # Auto-detects OS and installs dependencies
./setup-system-deps.sh --help   # Show installation options
```

**Supported Platforms:**
- **Linux (Ubuntu/Debian)**: Installs via `apt` (requires `sudo`)
- **macOS**: Installs via Homebrew (requires `brew` to be installed)
- **Windows**: Provides manual installation instructions

**Dev Container Users**: Dependencies install automatically - no manual setup needed!

**Having Issues?** See [SETUP_TROUBLESHOOTING.md](SETUP_TROUBLESHOOTING.md) for common solutions.

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