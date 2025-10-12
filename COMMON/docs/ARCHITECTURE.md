# COMMON Framework Architecture

This document provides technical details about the shared infrastructure framework.

## Logging System

### ScriptLogging Class

Located in `COMMON/src/common/logging.py`, provides consistent logging for all scripts.

#### Key Features
- **Dual Output**: Console (user-friendly) + File (detailed debugging)
- **Automatic Setup**: Creates `.log/` directories automatically
- **Timestamped Files**: Prevents log file conflicts
- **Debug Support**: Configurable verbosity levels
- **Fallback Safety**: Graceful degradation if COMMON unavailable

#### Usage Pattern
```python
# Standard import pattern
common_src_path = Path(__file__).parent.parent.parent / 'COMMON' / 'src'
sys.path.insert(0, str(common_src_path))

try:
    from common.logging import ScriptLogging
    logger = ScriptLogging.get_script_logger(name="script_name", debug=True)
except ImportError:
    # Fallback logging
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("script_name")
```

#### Output Formats
```python
# Console format (clean for users)
'%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# Example: 2025-10-03 18:22:31 - sample_20251003_182231 - INFO - Starting process

# File format (detailed for debugging)  
'%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s:%(lineno)d - %(message)s'
# Example: 2025-10-03 18:22:31 - sample_20251003_182231 - INFO - sample - run:259 - Starting process
```

### Import Resolution Strategy

The logging module handles different import contexts:
```python
try:
    from src.common.config import BaseConfig  # From COMMON project
except ImportError:
    try:
        from common.config import BaseConfig   # From other projects
    except ImportError:
        BaseConfig = None                      # Graceful degradation
```

## Task System

### Shared Tasks (COMMON/common_tasks.py)

Eliminates duplication by providing common tasks that all projects inherit.

#### Core Tasks
- `setup`: Environment and dependency setup
- `clean`: Remove build artifacts and caches
- `test`: Run pytest with coverage reporting
- `lint`: Code quality checks with flake8
- `build`: Build project distributions
- `run`: Universal script runner
- `scripts`: List available scripts

#### Extension Pattern
```python
# Project-specific tasks.py
import sys
from pathlib import Path

# Import shared tasks
sys.path.insert(0, str(Path(__file__).parent.parent / 'COMMON'))
from common_tasks import *

# Add project-specific tasks
@task
def sample_demo(c):
    """Run sample script with demo data."""
    # Project-specific task implementation
```

### Script Runner System

#### Universal Runner (COMMON/scripts/run.py)
- Works from any project directory
- Automatic script discovery in `scripts/` folders
- Argument passthrough to target scripts
- Error handling and user feedback

#### Three Execution Methods
1. **Shortcut**: `inv r -n script -a 'args'`
2. **Traditional**: `invoke run --script script --args 'args'`  
3. **Direct**: `python ../COMMON/scripts/run.py script args`

#### Implementation Details
```python
def run_script(script_name, script_args=None):
    """Run a script from the current project's scripts directory."""
    scripts_dir = Path.cwd() / 'scripts'
    script_path = scripts_dir / f'{script_name}.py'
    
    if not script_path.exists():
        # Fallback search in other common locations
        for search_dir in [Path.cwd(), scripts_dir.parent]:
            # ... search logic
    
    # Execute with proper argument handling
    cmd = [sys.executable, str(script_path)] + (script_args or [])
    subprocess.run(cmd, check=True)
```

## Configuration System

### BaseConfig Class (COMMON/src/common/config.py)

Provides consistent configuration management across projects.

#### Features
- **Environment-based**: Supports dev/test/prod environments
- **Pydantic Validation**: Type-safe configuration with validation
- **Dotenv Integration**: Loads from `.env` files
- **Extensible**: Projects can extend for specific needs

#### Usage Pattern
```python
from common.config import BaseConfig, load_config

# Load configuration
config = load_config(project_path=Path.cwd(), env="dev")

# Use in logging setup
logger = LoggingConfig.setup_logging(config, project_name="my_project")
```

## Testing Framework

### Shared Configuration
`pyproject.toml` provides consistent test configuration:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
pythonpath = ["src", "common/src"]
```

### Testing Patterns
- **Fixture-based**: Reusable test fixtures for common scenarios
- **Mock-friendly**: Designed for easy mocking and isolation
- **Coverage Integration**: Automatic coverage reporting
- **Cross-platform**: Works on Windows, macOS, Linux

## Virtual Environment Management

### Environment Setup Pattern
Each project has consistent environment management:
- `setenv`: Creates/recreates virtual environment
- `activate.sh`: Activates environment in current shell
- `pyproject.toml`: Defines dependencies

### Activation Flow
```bash
./setenv --recreate    # Create fresh environment
source activate.sh     # Activate in current shell
inv setup             # Install dependencies and setup
```

## Import Path Management

### Consistent Import Strategy
All scripts use the same pattern to import COMMON modules:
```python
# Standard pattern for all scripts
common_src_path = Path(__file__).parent.parent.parent / 'COMMON' / 'src'
sys.path.insert(0, str(common_src_path))
```

### Path Resolution
- Relative paths from script location
- Fallback mechanisms for different project structures
- Error handling for missing COMMON directory

## Error Handling Patterns

### Graceful Degradation
Framework components provide fallbacks:
```python
try:
    from common.logging import ScriptLogging
    # Use full functionality
except ImportError:
    # Provide basic functionality
    import logging
    ScriptLogging = None
```

### User-Friendly Errors
- Clear error messages with actionable guidance
- Helpful suggestions for common issues
- Consistent error logging patterns

## Extension Points

### Adding New Projects
1. Copy structure from existing project
2. Update `pyproject.toml` with project-specific info
3. Extend `tasks.py` with project-specific tasks
4. Scripts automatically inherit framework

### Adding New Scripts
1. Follow standard script template
2. Import ScriptLogging for consistent logging
3. Add to project's `scripts/` directory
4. Automatically available via script runner

### Adding New Shared Functionality
1. Add to appropriate COMMON module
2. Update import patterns if needed
3. Add tests to COMMON test suite
4. Document in architecture docs

## Performance Considerations

### Lazy Loading
- Modules are imported only when needed
- Heavy dependencies are optional
- Fast startup times for simple scripts

### Path Efficiency
- Minimal path resolution overhead
- Cached import paths where possible
- Efficient script discovery

### Memory Usage
- Shared modules loaded once per process
- Minimal memory footprint for simple operations
- Efficient logging buffer management

## Security Considerations

### Path Safety
- Validates script paths before execution
- Prevents directory traversal attacks
- Safe handling of user-provided arguments

### Environment Isolation
- Virtual environments prevent system contamination
- Clear dependency boundaries
- Reproducible environments across machines

## Monitoring and Debugging

### Logging Integration
- All framework operations are logged
- Debug modes available for troubleshooting
- Structured logging for analysis

### Error Tracking
- Comprehensive error context
- Stack traces preserved
- User-friendly error summaries

This architecture provides a solid foundation for scaling photo processing tools while maintaining consistency and developer experience.