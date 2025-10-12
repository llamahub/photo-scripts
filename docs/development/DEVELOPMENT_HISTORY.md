# Photo Scripts Development History

This document captures the key architectural decisions, patterns, and development context for the photo-scripts monorepo framework.

## Project Overview

This is a Python monorepo containing multiple photo processing projects with shared infrastructure. The architecture emphasizes code reuse, consistent patterns, and developer experience.

### Repository Structure
```
photo-scripts/
├── COMMON/                 # Shared infrastructure and utilities
│   ├── src/common/        # Common modules (logging, config, utils)
│   ├── tests/             # Tests for common modules
│   └── pyproject.toml     # Common dependencies and config
├── EXIF/                  # EXIF processing project
│   ├── src/exif/         # Project-specific modules
│   ├── scripts/          # Standalone scripts
│   ├── tests/            # Project tests
│   └── tasks.py          # Project tasks (imports from COMMON)
└── README.md
```

## Key Architectural Decisions

### 1. Monorepo Framework (October 2025)

**Decision**: Implement a monorepo with shared COMMON infrastructure rather than separate repositories.

**Rationale**: 
- Eliminate code duplication across photo processing projects
- Centralize logging, configuration, and task management
- Enable consistent patterns across all projects
- Simplify dependency management

**Implementation**:
- `COMMON/` contains shared modules imported by all projects
- Each project has its own `src/`, `tests/`, and `tasks.py`
- Shared `pyproject.toml` in COMMON for common dependencies
- Project-specific `pyproject.toml` files for project dependencies

### 2. Centralized Logging Framework

**Decision**: Create `COMMON/src/common/logging.py` with `ScriptLogging` class for consistent logging across all scripts.

**Problem Solved**: Scripts were implementing their own logging mechanisms with inconsistent formats and capabilities.

**Solution**:
```python
# Simple usage in any script
from common.logging import ScriptLogging
logger = ScriptLogging.get_script_logger(name="script_name", debug=True)
```

**Features**:
- Dual output: console (simple format) + file (detailed format)
- Automatic log directory creation (`.log/`)
- Timestamped log files
- Debug mode support
- Fallback mechanism if COMMON is unavailable

### 3. Shared Task System

**Decision**: Consolidate duplicate `tasks.py` files into `COMMON/common_tasks.py` with project-specific extensions.

**Problem Solved**: Every project had nearly identical task definitions, creating maintenance burden.

**Implementation**:
```python
# COMMON/common_tasks.py - shared tasks
@task
def test(c): ...
@task  
def lint(c): ...

# Project-specific tasks.py
from common_tasks import *  # Import all shared tasks

@task
def sample_demo(c):  # Project-specific tasks
    ...
```

### 4. Script Runner Consolidation

**Decision**: Create universal `COMMON/scripts/run.py` that works from any project directory.

**Problem Solved**: Duplicate run.py files in each project with identical functionality.

**Features**:
- Works from any project directory
- Three execution methods:
  1. Shortcut: `inv r -n script_name -a 'args'`
  2. Traditional: `invoke run --script script_name --args 'args'`
  3. Direct: `python ../COMMON/scripts/run.py script_name args`

### 5. Virtual Environment Management

**Decision**: Each project has its own virtual environment with shared activation patterns.

**Pattern**:
- `setenv` script in each project for environment setup
- `activate.sh` for sourcing into current shell
- `--recreate` flag for clean environment rebuilds

## Development Patterns

### Script Development Pattern

1. **Import COMMON logging**:
```python
# Standard import pattern for all scripts
common_src_path = Path(__file__).parent.parent.parent / 'COMMON' / 'src'
sys.path.insert(0, str(common_src_path))

try:
    from common.logging import ScriptLogging
except ImportError:
    ScriptLogging = None  # Fallback
```

2. **Setup logging**:
```python
if ScriptLogging:
    logger = ScriptLogging.get_script_logger(name=f"script_{timestamp}", debug=debug)
else:
    # Fallback logging setup
```

3. **Use consistent argument parsing** with `--debug` flag integration

### Testing Pattern

- Comprehensive unit tests with pytest
- Coverage reporting with pytest-cov
- Shared test configuration in pyproject.toml
- Fixtures for temporary directories and mock objects

### Project Extension Pattern

To add a new project:
1. Create project directory (e.g., `RESIZE/`)
2. Copy structure from existing project
3. Create `tasks.py` that imports from `common_tasks`
4. Add project-specific dependencies to local `pyproject.toml`
5. Scripts automatically inherit COMMON logging and runner infrastructure

## Key Implementation Details

### sample.py Evolution

Original `select.sh` (bash) → `sample.py` (Python) with:
- Multi-stage sampling algorithm (subfolders → root → full tree)
- Sidecar file detection and copying
- Comprehensive logging integration
- Full test coverage (21 tests, 96%+ coverage)

### Logging Implementation

The `ScriptLogging.get_script_logger()` method provides:
```python
# Console format (simple)
'%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# File format (detailed) 
'%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s:%(lineno)d - %(message)s'
```

### Import Resolution

COMMON modules handle import path variations:
```python
try:
    from src.common.config import BaseConfig
except ImportError:
    try:
        from common.config import BaseConfig
    except ImportError:
        BaseConfig = None  # Graceful degradation
```

## Developer Experience Improvements

### Task Shortcuts
- `inv r -n sample -a '--help'` instead of `invoke run --script sample --args '--help'`
- `inv t` for tests, `inv l` for lint, `inv setup` for environment

### Consistent Error Handling
- Scripts use logger.error() for errors
- Fallback mechanisms for missing dependencies
- Clear error messages with actionable guidance

### Documentation Integration
- Comprehensive docstrings
- Example usage in help text
- README files at project and script level

## Migration Notes

### From Individual Projects to Monorepo
1. Moved shared functionality to COMMON/
2. Updated import paths to use COMMON modules
3. Consolidated task definitions
4. Standardized virtual environment management
5. Updated all scripts to use ScriptLogging

### Breaking Changes
- Scripts now require COMMON/ to be present
- Task invocation syntax changed (added shortcuts)
- Log file locations changed (now in `.log/` directories)
- Import paths changed for shared modules

## Future Considerations

### Extensibility
- New projects can easily adopt the framework
- Common patterns are established and documented
- Testing infrastructure is reusable

### Maintenance
- Single source of truth for shared functionality
- Consistent versioning and dependency management
- Centralized logging and configuration patterns

### Performance
- Lazy loading of modules where possible
- Efficient path resolution for imports
- Minimal overhead for script execution

## Context for AI Assistants

This framework was developed through iterative conversations focusing on:
1. **Code Quality**: Comprehensive testing, proper error handling, consistent patterns
2. **Developer Experience**: Simple APIs, clear documentation, helpful shortcuts
3. **Maintainability**: DRY principles, centralized shared code, clear separation of concerns
4. **Extensibility**: Easy to add new projects, scripts inherit common functionality

Key principles that guided development decisions:
- **Consistency over convenience** - patterns should be predictable
- **Graceful degradation** - fallbacks for missing dependencies
- **Developer-friendly** - minimize boilerplate, maximize clarity
- **Test-driven** - comprehensive test coverage for all functionality

The codebase reflects these principles in its structure, naming conventions, error handling, and documentation patterns.