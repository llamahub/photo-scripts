# COMMON Framework Documentation

The shared infrastructure framework that provides consistent patterns, logging, task management, and script execution across all projects in the photo-scripts monorepo.

## 📋 Quick Navigation

| Document | Purpose | Audience |
|----------|---------|----------|
| **[Architecture](ARCHITECTURE.md)** | Technical framework details | Developers |
| **[Main Project README](../README.md)** | Framework overview and usage | All Users |

## 🏗️ Framework Components

### Core Infrastructure
- **ScriptLogging**: Consistent logging with dual output (console + file)
- **Task System**: Shared invoke tasks across all projects
- **Script Runner**: Universal script discovery and execution
- **Configuration**: Environment-based configuration management

### Development Tools
- **Virtual Environment Management**: Consistent environment setup
- **Import Path Management**: Standardized module importing
- **Error Handling**: Graceful degradation patterns
- **Testing Framework**: Shared test configuration and patterns

## 🚀 Quick Start for Developers

### Using COMMON in Your Scripts
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

### Using COMMON Tasks
```bash
# Standard task usage
inv setup              # Setup environment
inv test               # Run tests with coverage
inv run --script name  # Run scripts
inv scripts           # List available scripts
```

## 📚 Technical Documentation

### **[Architecture](ARCHITECTURE.md)**
Comprehensive technical documentation covering:

- **Logging System**: ScriptLogging class features and usage patterns
- **Task System**: Shared tasks and extension patterns  
- **Script Runner**: Universal script discovery and execution
- **Configuration**: BaseConfig and environment management
- **Testing Framework**: Shared test configuration and patterns
- **Virtual Environment**: Environment setup and activation
- **Import Management**: Consistent import strategies
- **Error Handling**: Graceful degradation patterns
- **Extension Points**: Adding new projects and functionality

## 🔧 Framework Features

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
1. **Shortcut**: `inv run --script name --args 'arguments'`
2. **Traditional**: `invoke run --script name --args 'arguments'`  
3. **Direct**: `python ../COMMON/scripts/run.py name arguments`

### Configuration Management
- **Environment-based**: Supports dev/test/prod environments
- **Pydantic Integration**: Type-safe configuration with validation
- **Dotenv Support**: Loads from `.env` files automatically
- **Project Extension**: Extensible for project-specific needs

## 🧪 Testing Integration

### Shared Test Configuration
All projects inherit consistent pytest configuration:
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

## 🔗 Integration with Projects

### Project Structure
Each project that uses COMMON follows this pattern:
```
PROJECT_NAME/
├── src/project_name/     # Project-specific source code
├── scripts/              # Executable scripts (auto-discovered)
├── tests/                # Project tests (inherit COMMON config)
├── tasks.py              # Extends COMMON tasks
├── pyproject.toml        # Project configuration
├── setenv                # Virtual environment setup
├── activate.sh           # Environment activation
└── README.md            # Project documentation
```

### Standard Integration Pattern
```python
# In project tasks.py
import sys
from pathlib import Path

# Import shared tasks
sys.path.insert(0, str(Path(__file__).parent.parent / 'COMMON'))
from common_tasks import *

# Add project-specific tasks
@task
def project_specific_task(c):
    """A custom task for this project."""
    pass
```

## 🛠️ Development Guidelines

### Adding New Framework Features
1. **Add to COMMON modules**: Place in appropriate `src/common/` module
2. **Update import patterns**: Ensure graceful fallback handling
3. **Add tests**: Comprehensive test coverage in `COMMON/tests/`
4. **Document**: Update this documentation and architecture docs
5. **Validate**: Test integration across all projects

### Framework Extension Points
- **New Projects**: Copy structure, extend tasks, add to monorepo
- **New Scripts**: Follow standard template, use ScriptLogging
- **New Modules**: Add to `src/common/`, update import patterns
- **New Tasks**: Extend common_tasks.py or add project-specific tasks

## 🔍 Troubleshooting

### Common Issues
- **Import Errors**: Verify COMMON path resolution in scripts
- **Task Not Found**: Check tasks.py extends common_tasks properly  
- **Virtual Environment**: Ensure `./setenv && source activate.sh` completed
- **Script Discovery**: Verify scripts are in `scripts/` directory

### Debug Mode
Enable debug logging to troubleshoot framework issues:
```python
logger = ScriptLogging.get_script_logger(name="script", debug=True)
```

## 📈 Performance Considerations

### Framework Optimizations
- **Lazy Loading**: Modules imported only when needed
- **Path Efficiency**: Minimal path resolution overhead
- **Memory Usage**: Shared modules loaded once per process
- **Fast Startup**: Quick initialization for simple operations

### Best Practices
- Use the standard import pattern for consistency
- Leverage shared tasks instead of duplicating functionality
- Follow established error handling patterns
- Maintain comprehensive test coverage

---

*For detailed technical implementation, see [ARCHITECTURE.md](ARCHITECTURE.md). For project-wide context, see the [main documentation](../../docs/README.md).*