# Temporary Directory Management Migration Guide

This guide explains how to migrate from various temporary directory patterns to the new centralized `TempManager` system.

## Overview of New System

The new centralized temporary directory management system provides:
- **Consistent naming patterns** across all projects
- **Categorized organization** (debug, cache, test, etc.)
- **Automatic cleanup options** with age-based filtering
- **Persistent vs auto-cleanup patterns** for different use cases
- **Centralized management** through invoke tasks

## Migration Patterns

### 1. Replace Legacy `get_temp_dir()` Usage

**Before (COMMON/common_tasks.py pattern):**
```python
def get_temp_dir(name_prefix="temp"):
    temp_base = Path(".tmp")
    temp_base.mkdir(exist_ok=True)
    timestamp = int(time.time())
    temp_dir = temp_base / f"{name_prefix}_{timestamp}"
    temp_dir.mkdir(exist_ok=True)
    return temp_dir

# Usage
temp_dir = get_temp_dir("demo")
```

**After (New centralized pattern):**
```python
from common.temp import TempManager

# For persistent debugging directories
temp_dir = TempManager.create_persistent_dir("demo", "debug")

# Or use convenience function
from common.temp import get_debug_temp_dir
temp_dir = get_debug_temp_dir("demo")
```

### 2. Replace Test `tempfile.TemporaryDirectory()` Usage

**Before (Test pattern):**
```python
import tempfile
from pathlib import Path

@pytest.fixture
def temp_dirs(self):
    """Create temporary source and target directories for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source = temp_path / "source"
        target = temp_path / "target"
        source.mkdir()
        target.mkdir()
        yield source, target
```

**After (New pattern):**
```python
from common.temp import pytest_temp_dirs

@pytest.fixture
def temp_dirs(self):
    """Create temporary source and target directories for testing."""
    with pytest_temp_dirs(2, ['source', 'target']) as dirs:
        yield dirs

# Or for simpler cases:
def test_something():
    with pytest_temp_dirs(2) as (source, target):
        # Test logic here
        pass
```

### 3. Replace `tmp_path` Fixture Usage

**Before (pytest tmp_path):**
```python
def test_something(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    # Test logic...
```

**After (Standardized pattern):**
```python
from common.temp import pytest_temp_dirs

def test_something():
    with pytest_temp_dirs(2, ['source', 'target']) as (source, target):
        # Test logic...
        pass
```

### 4. Replace Manual Temporary Directory Creation

**Before (Manual patterns):**
```python
# Various manual patterns found in codebase
temp_dir = Path(".tmp") / "processing"
temp_dir.mkdir(parents=True, exist_ok=True)

# Or 
with tempfile.TemporaryDirectory() as temp:
    work_dir = Path(temp) / "work"
    work_dir.mkdir()
```

**After (Categorized patterns):**
```python
from common.temp import TempManager, temp_working_dir

# For persistent work (inspection after completion)
work_dir = TempManager.create_persistent_dir("processing", "work")

# For auto-cleanup work
with temp_working_dir("processing") as work_dir:
    # Work here, automatic cleanup
    pass

# For auto-cleanup with specific naming
with TempManager.auto_cleanup_dir("processing") as work_dir:
    # Work here, automatic cleanup
    pass
```

## New Patterns by Use Case

### 1. Debugging/Inspection (Persistent)
Use when you want to inspect results after script completion:
```python
from common.temp import get_debug_temp_dir

debug_dir = get_debug_temp_dir("script_name")
# Creates: .tmp/debug/script_name_1696348800/
```

### 2. Caching (Persistent)
Use for temporary files that should persist between runs:
```python
from common.temp import get_cache_temp_dir

cache_dir = get_cache_temp_dir("thumbnails")
# Creates: .tmp/cache/thumbnails_1696348800/
```

### 3. Processing Work (Auto-cleanup)
Use for temporary work that doesn't need inspection:
```python
from common.temp import temp_working_dir

with temp_working_dir("image_processing") as work_dir:
    # Process images in work_dir
    processed_file = work_dir / "result.jpg"
    # work_dir automatically cleaned up
```

### 4. Test Fixtures (Auto-cleanup)
Use the standardized test fixture helper:
```python
from common.temp import pytest_temp_dirs

class TestMyClass:
    @pytest.fixture
    def temp_dirs(self):
        with pytest_temp_dirs(3, ['source', 'target', 'backup']) as dirs:
            yield dirs
    
    def test_method(self, temp_dirs):
        source, target, backup = temp_dirs
        # Test with clean directories
```

## Directory Structure

The new system creates organized temporary directories:

```
.tmp/                          # Base persistent temp directory
├── debug/                     # Debug/inspection directories
│   ├── script_name_timestamp/
│   └── demo_name_timestamp/
├── cache/                     # Cached data
│   ├── thumbnails_timestamp/
│   └── metadata_timestamp/
├── test/                      # Test-related temps (if persistent)
│   └── test_data_timestamp/
└── uncategorized/            # Items without category
    └── temp_timestamp/
```

Auto-cleanup directories use system temp locations and clean themselves.

## Management Commands

### Check Temporary Directory Status
```bash
inv temp-status
```
Shows all persistent temporary directories with sizes and ages.

### Clean Temporary Directories
```bash
# Clean all temporary files
inv temp-clean

# Clean files older than 24 hours
inv temp-clean --max-age-hours 24

# See what would be cleaned (dry run)
inv temp-clean --dry-run

# Enhanced clean with age filtering
inv clean --temp-age-hours 48
```

## Migration Checklist

For each project in the monorepo:

### Scripts (`scripts/*.py`)
- [ ] Replace manual temp directory creation with `TempManager.create_persistent_dir()`
- [ ] Use categories: "debug", "cache", "work", etc.
- [ ] Add cleanup logic or use auto-cleanup patterns for non-debug cases

### Tests (`tests/*.py`)
- [ ] Replace `tempfile.TemporaryDirectory` fixtures with `pytest_temp_dirs()`
- [ ] Replace manual `tmp_path` setup with standardized patterns
- [ ] Use auto-cleanup patterns for test isolation

### Task Files (`tasks.py`)
- [ ] Update `get_temp_dir()` calls to use new `TempManager`
- [ ] Add temp management tasks if not inheriting from common_tasks
- [ ] Update clean tasks to use centralized temp management

### Configuration
- [ ] Ensure `.gitignore` includes both `.tmp/` and `.temp/`
- [ ] Update any documentation that references temporary directories
- [ ] Add temp management commands to project README if needed

## Benefits of Migration

1. **Consistency**: All projects use the same temporary directory patterns
2. **Organization**: Categories keep related temporary files grouped
3. **Management**: Central commands to inspect and clean temporary files
4. **Debugging**: Persistent directories allow post-execution inspection
5. **Cleanup**: Automated cleanup with age-based filtering
6. **Testing**: Standardized test fixture patterns reduce boilerplate

## Backward Compatibility

- The old `get_temp_dir()` function still works (uses new system internally)
- Existing temporary directories will be cleaned by the enhanced `clean` task
- Migration can be done incrementally, one project at a time