# Photo Scripts Monorepo

A Python monorepo framework for photo processing tools with shared infrastructure and consistent patterns.

## Quick Start

### Setup Environment
```bash
# Navigate to any project
cd EXIF/
./setenv --recreate  # Creates virtual environment
source activate.sh   # Activates environment
```

### Run Scripts
```bash
# Three ways to run scripts:
inv r -n sample -a '--help'                           # Shortcut
invoke run --script sample --args '--help'            # Traditional  
python ../COMMON/scripts/run.py sample --help         # Direct
```

### Common Tasks
```bash
inv setup    # Setup project environment
inv test     # Run tests with coverage
inv lint     # Run code linting
inv clean    # Clean build artifacts
inv scripts  # List available scripts
```

## Architecture

### Shared Infrastructure (COMMON/)
- **Logging**: `ScriptLogging.get_script_logger()` for consistent logging
- **Configuration**: Base configuration classes with environment support
- **Tasks**: Shared invoke tasks for all projects
- **Scripts**: Universal script runner

### Project Structure
```
project/
├── src/project/          # Project modules
├── scripts/              # Standalone scripts  
├── tests/                # Unit tests
├── tasks.py              # Project tasks (extends COMMON)
├── pyproject.toml        # Project dependencies
├── setenv                # Environment setup
└── activate.sh           # Environment activation
```

## Script Development

### Standard Pattern
```python
#!/usr/bin/env python3
"""Script description."""

import sys
from pathlib import Path
from datetime import datetime

# Import COMMON logging
common_src_path = Path(__file__).parent.parent.parent / 'COMMON' / 'src'
sys.path.insert(0, str(common_src_path))

try:
    from common.logging import ScriptLogging
except ImportError:
    import logging
    ScriptLogging = None

def main():
    # Setup logging
    if ScriptLogging:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        logger = ScriptLogging.get_script_logger(
            name=f"script_{timestamp}",
            debug=args.debug
        )
    else:
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("script")
    
    # Use logger
    logger.info("Starting script")
    # ... script logic ...
    logger.info("Script completed")

if __name__ == '__main__':
    main()
```

## Key Features

### Logging
- **Console**: Clean format for terminal output
- **File**: Detailed format with function/line info
- **Auto-rotation**: Timestamped log files
- **Debug support**: Configurable verbosity

### Testing
- Comprehensive pytest-based testing
- Coverage reporting with pytest-cov
- Shared test configuration
- Mock-friendly patterns

### Task Management
- Shared tasks across all projects
- Project-specific extensions
- Shortcut syntax for common operations
- Cross-platform compatibility

## Current Projects

### EXIF/
Image metadata processing tools
- `sample.py`: Random image sampling with sidecar support
- `image_data.py`: EXIF data extraction and processing

### COMMON/
Shared infrastructure and utilities
- Logging framework
- Configuration management
- Task definitions
- Script runner

## Adding New Projects

1. **Create project directory**:
   ```bash
   mkdir NEW_PROJECT/
   cd NEW_PROJECT/
   ```

2. **Copy structure from existing project**:
   ```bash
   cp -r ../EXIF/{src,tests,tasks.py,pyproject.toml,setenv,activate.sh} .
   ```

3. **Update project-specific files**:
   - Modify `pyproject.toml` name and dependencies
   - Update `tasks.py` for project-specific tasks
   - Create initial modules in `src/`

4. **Setup environment**:
   ```bash
   ./setenv --recreate
   source activate.sh
   inv setup
   ```

Scripts automatically inherit:
- COMMON logging framework
- Universal script runner
- Shared task system
- Testing infrastructure

## Best Practices

### Code Organization
- Keep shared code in COMMON/
- Project-specific code in project directories
- Scripts are standalone but use COMMON infrastructure
- Tests mirror source structure

### Error Handling
- Use logger.error() for errors
- Provide fallbacks for missing dependencies
- Clear error messages with actionable guidance
- Graceful degradation patterns

### Documentation
- Comprehensive docstrings
- Usage examples in help text
- README files for context
- Type hints for clarity

## Development History

See `DEVELOPMENT_HISTORY.md` for detailed architectural decisions, migration notes, and context for future development.

## Dependencies

### Common (all projects)
- Python 3.8+
- invoke (task runner)
- pydantic (configuration)
- python-dotenv (environment management)

### Development
- pytest + pytest-cov (testing)
- black (formatting)
- flake8 (linting)
- mypy (type checking)

## License

MIT License - see individual project files for details.