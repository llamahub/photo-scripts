# Common Tasks System

This directory contains shared invoke tasks for all projects in the monorepo.

## Files

- `common_tasks.py` - Contains all the common task implementations
- `tasks.py` - Simple wrapper that imports all common tasks (for projects that don't need customization)

## Usage

### For projects that don't need custom tasks:
Copy `tasks.py` to your project directory. It will automatically import all common tasks.

### For projects that need custom tasks:
Create a custom `tasks.py` in your project directory like this:

```python
"""Project-specific invoke tasks."""

import sys
from pathlib import Path
from invoke import task

# Add COMMON directory to path and import common tasks
common_dir = Path(__file__).parent.parent / "COMMON"
sys.path.insert(0, str(common_dir))

# Import all common functionality from common_tasks module
from common_tasks import (
    get_venv_python, get_venv_executable, ensure_venv,
    setup, clean, lint, format, test, build, run, install, 
    deps, shell, scripts, status
)

# Add your project-specific tasks here
@task
def my_custom_task(ctx):
    """A custom task for this project."""
    print("This is a custom task!")

# Override common tasks if needed
@task
def run(ctx, script=None, args="", env="dev"):
    """Override the common run task with project-specific behavior."""
    # Your custom implementation here
    pass
```

## Available Tasks

All projects get these standard tasks:

- `setup` - Setup the project environment
- `clean` - Clean build artifacts  
- `lint` - Run linting tools (black, flake8, mypy)
- `format` - Format code with black
- `test` - Run tests with pytest
- `build` - Build the project (clean, lint, test)
- `run` - Run scripts or main project
- `scripts` - List available scripts
- `install` - Install the project
- `deps` - Update dependencies
- `shell` - Start shell with virtual environment
- `status` - Show project and environment status

## Common Functions

These utility functions are available for custom tasks:

- `get_venv_python()` - Get path to virtual environment Python
- `get_venv_executable(tool_name)` - Get path to tool in virtual environment  
- `ensure_venv(ctx)` - Ensure virtual environment exists