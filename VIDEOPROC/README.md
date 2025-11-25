# VIDEOPROC Module

VideoProc Vlogger project file repair and maintenance utilities.

## Overview

This module provides tools for working with VideoProc Vlogger project files (.vpd/.dvp format). The primary focus is on repairing broken project file references when media files have been moved, renamed, or converted to different formats.

## Available Scripts

### repair.py - VPD Project File Repair

Automatically repairs VideoProc Vlogger project files by finding and fixing missing media file references.

**Key Features:**
- 🔍 Automatically searches for missing files in project directory tree
- 🔄 Handles format conversions (HEIC → JPG, etc.)
- 💾 Creates backups before modifying files
- 🎯 Supports dry-run mode to preview changes
- 📝 Comprehensive logging of all operations
- 🎨 Supports images, video, and audio files

**Quick Start:**
```bash
# Repair a project file (with backup)
. run repair project.vpd --backup

# Preview changes without modifying
. run repair project.vpd --dry-run

# Specify search directory
. run repair project.vpd --search-root /path/to/media --backup
```

**Documentation:** [REPAIR_SCRIPT.md](docs/REPAIR_SCRIPT.md)

### example_script.py - Script Template

Template demonstrating the consistent structure and argument parsing pattern that all VIDEOPROC scripts should follow.

**Purpose:**
- Provides standardized CLI interface using COMMON framework
- Shows integration with ScriptArgumentParser
- Demonstrates proper logging setup
- Template for future script development

## Usage

### Using the Run Wrapper

The VIDEOPROC module uses the COMMON run wrapper for consistent script execution:

```bash
# Activate environment and run script
. run repair project.vpd --backup

# Get help for any script
. run repair --help

# Run with verbose logging
. run repair project.vpd --verbose
```

### Direct Python Execution

You can also run scripts directly:

```bash
cd /workspaces/photo-scripts/VIDEOPROC
python3 scripts/repair.py project.vpd --backup
```

## Project Structure

```
VIDEOPROC/
├── README.md              # This file
├── run                    # Run wrapper (links to COMMON/run)
├── setenv                 # Environment setup
├── tasks.py              # Invoke task definitions
├── pyproject.toml        # Python project configuration
│
├── scripts/              # Executable scripts
│   ├── repair.py         # VPD file repair tool
│   └── example_script.py # Script template
│
├── src/                  # Source code modules
│   └── videoproc/        # Core functionality
│
├── docs/                 # Documentation
│   ├── REPAIR_SCRIPT.md  # Repair script guide
│   └── ...
│
├── samples/              # Sample files and test data
│   ├── test_project/     # Test VPD files
│   └── test_media/       # Test media files
│
└── VPD_File_Structure_Analysis.md  # Technical file format documentation
```

## Common Workflows

### Workflow 1: Repair Moved Files

Files have been reorganized but VPD still references old paths:

```bash
# Step 1: Preview what will be fixed
. run repair project.vpd --dry-run --verbose

# Step 2: Create backup and repair
. run repair project.vpd --backup

# Step 3: Verify repair succeeded
. run repair project.vpd
```

### Workflow 2: Handle Format Conversions

iPhone photos converted from HEIC to JPG:

```bash
# Repair automatically handles extension changes
. run repair project.vpd --backup
```

### Workflow 3: Project Relocation

Project moved to new computer with different paths:

```bash
# Specify where media files are now located
. run repair project.vpd --search-root /Users/newuser/Movies --backup
```

## File Format

VideoProc Vlogger uses JSON-based project files (.vpd/.dvp) that contain:

- **Timeline**: Track and block definitions with editing attributes
- **Project Info**: Metadata, resolution, frame rate
- **Resource Lists**: References to image, video, and audio files
- **Scapegoat**: Actual file path definitions and metadata

**Detailed Analysis:** [VPD_File_Structure_Analysis.md](VPD_File_Structure_Analysis.md)

## Dependencies

### Required
- Python 3.8+
- COMMON framework (shared utilities)

### Optional
- None (uses Python standard library only)

## Installation

The VIDEOPROC module is part of the photo-scripts monorepo:

```bash
# Navigate to VIDEOPROC directory
cd /workspaces/photo-scripts/VIDEOPROC

# Setup environment (if needed)
./setenv

# Run scripts using wrapper
. run repair --help
```

## Development

### Creating New Scripts

1. Copy `scripts/example_script.py` as template
2. Follow the established patterns:
   - Use ScriptArgumentParser for CLI
   - Integrate with ScriptLogging
   - Support standard arguments (--verbose, --quiet, --dry-run)
   - Provide comprehensive help text

3. Add documentation in `docs/`

### Testing

Test scripts are in `tests/` directory:

```bash
# Run all tests
python3 -m pytest

# Run specific test
python3 -m pytest tests/test_repair.py

# Run with coverage
python3 -m pytest --cov=src --cov-report=html
```

## Best Practices

### Working with VPD Files

✅ **DO:**
- Always create backups before modifying
- Test with --dry-run first
- Close VideoProc Vlogger before running scripts
- Keep media files organized in project subdirectories
- Use verbose mode when troubleshooting

❌ **DON'T:**
- Edit VPD files while VideoProc Vlogger is open
- Skip backups on important projects
- Delete backup files immediately
- Move files after repair without re-running script

### Script Development

✅ **DO:**
- Follow example_script.py template
- Use COMMON framework utilities
- Provide comprehensive help text
- Log important operations at INFO level
- Support dry-run mode for destructive operations

❌ **DON'T:**
- Hardcode paths or configurations
- Skip input validation
- Modify files without user confirmation
- Ignore errors silently

## Troubleshooting

### Common Issues

**"No files could be repaired"**
- Files not in search path
- Use `--search-root` to specify correct directory
- Check that file basenames match

**"Invalid JSON in VPD file"**
- VPD file corrupted
- Restore from backup
- Validate with `python3 -m json.tool project.vpd`

**"Multiple matches found"**
- Multiple files with same name
- Script uses first match
- Organize files to avoid duplicates

### Log Files

All operations are logged to `.log/` directory:

```bash
# View recent logs
ls -lt .log/repair_*.log | head

# Check specific operation
cat .log/repair_20251122_143022.log
```

## Future Enhancements

Planned features:
- [ ] Relocate script - Update all paths when moving project
- [ ] Organize script - Consolidate scattered media files
- [ ] Validate script - Check project integrity
- [ ] Extract script - Export media file list
- [ ] Deduplicate script - Find and remove duplicate resources

## Documentation

- [REPAIR_SCRIPT.md](docs/REPAIR_SCRIPT.md) - Detailed repair script guide
- [VPD_File_Structure_Analysis.md](VPD_File_Structure_Analysis.md) - Technical file format details
- [example_script.py](scripts/example_script.py) - Script development template

## Support

For issues or questions:
1. Check log files in `.log/` directory
2. Run with `--verbose` for detailed output
3. Review documentation in `docs/`
4. Check related COMMON framework documentation

## License

Part of the photo-scripts monorepo project.

## See Also

- [COMMON Framework](../COMMON/docs/README.md) - Shared utilities
- [EXIF Module](../EXIF/README.md) - Photo organization by EXIF date
- [Project Documentation](../docs/README.md) - Overall project documentation
