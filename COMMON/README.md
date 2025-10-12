# COMMON Framework

Shared infrastructure framework providing consistent patterns, logging, task management, and script execution across all projects in the photo-scripts monorepo.

**📚 [Complete Documentation](docs/README.md)** - **Framework documentation hub**

## Core Components

- **ScriptLogging**: Consistent logging with dual output (console + file)
- **Task System**: Shared invoke tasks with project extensions  
- **Script Runner**: Universal script discovery and execution
- **Configuration**: Environment-based configuration management

## Quick Start

### Using COMMON in Scripts
```python
# Standard COMMON import pattern (ALWAYS use this)
common_src_path = Path(__file__).parent.parent.parent / 'COMMON' / 'src'
sys.path.insert(0, str(common_src_path))

try:
    from common.logging import ScriptLogging
    logger = ScriptLogging.get_script_logger(name="my_script", debug=True)
except ImportError:
    # Graceful fallback
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("my_script")
```

### Using Shared Tasks
```bash
# Standard task usage
inv setup              # Setup environment
inv test               # Run tests with coverage  
inv run --script name  # Run scripts
inv scripts           # List available scripts
```

## Framework Features

### Logging System
- **Dual Output**: User-friendly console + detailed file logging
- **Automatic Setup**: Creates `.log/` directories automatically
- **Timestamped Files**: Prevents conflicts with unique timestamps
- **Debug Support**: Configurable verbosity levels
- **Fallback Safety**: Works even when COMMON unavailable

### Task Management  
- **Universal Tasks**: `setup`, `test`, `clean`, `run`, `scripts`, etc.
- **Project Extension**: Easy addition of project-specific tasks
- **Script Discovery**: Automatic discovery of scripts in `scripts/` folders
- **Argument Passthrough**: Clean argument handling to target scripts

### Script Execution
Three execution methods for maximum flexibility:
1. **Invoke**: `inv run --script name --args 'arguments'`
2. **Direct**: `python ../COMMON/scripts/run.py name arguments`
3. **Local**: `python scripts/name.py arguments`

## Documentation

For complete framework documentation, see:

- **[Framework Documentation](docs/README.md)** - Complete COMMON framework guide
- **[Technical Architecture](docs/ARCHITECTURE.md)** - Detailed implementation
- **[Main Project Docs](../docs/README.md)** - Project-wide documentation