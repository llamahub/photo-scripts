# EXIF Photo Processing Tools

A comprehensive Python framework for photo organization, metadata processing, and image management with EXIF data extraction capabilities.

**📚 [Complete Documentation](docs/README.md)** - **EXIF tools documentation hub**

## Quick Start

```bash
# Setup environment
./setenv --recreate
source activate.sh

# Core operations
python scripts/organize.py /path/to/photos /path/to/organized --dry-run
python scripts/generate.py test_data.csv /path/to/output --sample 10
python scripts/select.py /path/to/photos /path/to/samples --files 50
python scripts/analyze.py /path/to/photos --output analysis.csv
python scripts/set_image_dates.py dates.csv --dry-run

# Using invoke (recommended)
inv run --script organize --args '/source /target --dry-run'
inv scripts  # List all available scripts
```

## Available Tools

| Script | Purpose | Key Features |
|--------|---------|--------------|
| **`organize.py`** | Photo organization by date/format | Dry-run mode, EXIF date extraction, format-based folders |
| **`generate.py`** | Test image generation | CSV-driven, multiple formats, EXIF metadata injection |
| **`select.py`** | Random photo sampling | Multi-stage selection, sidecar file handling |
| **`analyze.py`** | Photo metadata analysis | Comprehensive EXIF data, CSV export, "Set Date" column |
| **`set_image_dates.py`** | Batch date correction | CSV-based, automatic extension fixing, dry-run support |

## Documentation

For complete documentation, see:

- **[EXIF Documentation](docs/README.md)** - Complete tools documentation
- **[Workflow Guide](docs/guides/WORKFLOW_GUIDE.md)** - End-to-end usage workflows
- **[Testing Strategy](docs/TESTING_STRATEGY.md)** - Comprehensive testing approach
- **[Performance Guide](docs/guides/PERFORMANCE_OPTIMIZATION_GUIDE.md)** - Optimization strategies
- **[Setup Guide](../docs/setup/SETUP_GUIDE.md)** - Installation instructions

## System Requirements

### Required Dependencies
- **Python 3.8+**: Core runtime environment
- **ExifTool**: EXIF metadata extraction (critical for photo processing)

### Quick Setup
```bash
# From project root - installs all dependencies automatically
../setup-system-deps.sh
```

For detailed setup instructions, see [Setup Guide](../docs/setup/SETUP_GUIDE.md).

## Architecture

### Core Components

#### Business Logic Classes
- **ImageData**: EXIF metadata extraction and date parsing
- **PhotoOrganizer**: Date-based photo organization with decade/year/month structure
- **ImageGenerator**: Test image creation with metadata from CSV specifications
- **ImageSelector**: Random sampling with sidecar file preservation

#### CLI Scripts (Thin Wrappers)
- **organize.py**: Photo organization interface
- **generate.py**: Test image generation interface  
- **select.py**: Photo sampling interface

### Design Principles
- **Separation of Concerns**: Business logic in classes, CLI in scripts
- **Comprehensive Testing**: 118 tests covering unit and integration scenarios
- **Robust Error Handling**: Graceful fallbacks and detailed logging
- **Flexible Date Extraction**: EXIF metadata → filename patterns → fallbacks

## Usage Examples

### Photo Organization
```bash
# Dry run to preview organization
python scripts/organize.py /source/photos /target/organized --dry-run

# Live organization with debug logging
python scripts/organize.py /source/photos /target/organized --debug

# Using shared script runner
inv r -n organize -a '/source/photos /target/organized --dry-run'
```

### Test Image Generation
```bash
# Generate all images from CSV
python scripts/generate.py test_specs.csv /output/images

# Generate 10 sample images with EXIF metadata
python scripts/generate.py test_specs.csv /output/images --sample 10 --exif

# Debug mode with detailed logging
python scripts/generate.py test_specs.csv /output/images --debug
```

### Photo Sampling
```bash
# Select 20 random photos from up to 5 folders
python scripts/select.py /source/photos /samples --files 20 --folders 5

# Clean target and copy with sidecars
python scripts/select.py /source/photos /samples --files 50 --clean

# Limit depth and files per folder
python scripts/select.py /source/photos /samples --depth 3 --perfolder 3
```

## Testing

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src/ --cov-report=html

# Run specific test suite
python -m pytest tests/test_photo_organizer.py -v

# Test specific functionality
python -m pytest tests/test_image_data.py::test_getImageDate_priority_order -v
```

## Date Extraction Priority

The system uses a sophisticated fallback strategy for extracting photo dates:

1. **EXIF DateTimeOriginal** (highest priority)
2. **EXIF ExifIFD:DateTimeOriginal**
3. **XMP-photoshop:DateCreated**
4. **EXIF FileModifyDate**
5. **Filename patterns**: `YYYYMMDD_HHMMSS`, `YYYY-MM-DD`, etc.
6. **Fallback date**: `1900-01-01 00:00` (last resort)

## Project Structure

```
EXIF/
├── src/exif/                 # Business logic classes
│   ├── image_data.py         # EXIF extraction and date parsing
│   ├── photo_organizer.py    # Date-based organization
│   ├── image_generator.py    # Test image creation
│   └── image_selector.py     # Random sampling with sidecars
├── scripts/                  # CLI interfaces
│   ├── organize.py           # Photo organization script
│   ├── generate.py           # Image generation script
│   └── select.py             # Photo sampling script
├── tests/                    # Comprehensive test suite (118 tests)
├── TESTING_STRATEGY.md       # Testing documentation
└── TEST_COVERAGE.md          # Coverage reports
```

## Error Handling

The system includes robust error handling:
- **Missing ExifTool**: Graceful fallback to filename parsing
- **Corrupted Images**: Skip with detailed logging
- **Permission Issues**: Continue processing with warnings
- **Invalid Dates**: Multiple fallback strategies
- **Missing Directories**: Auto-creation with proper permissions

## Integration with COMMON Framework

This project uses the shared photo-scripts framework:
- **Logging**: `ScriptLogging.get_script_logger()` for consistent output
- **Task System**: Shared invoke tasks with project-specific extensions
- **Script Runner**: Universal execution via `inv r -n script -a 'args'`

For framework details, see [COMMON/ARCHITECTURE.md](../COMMON/ARCHITECTURE.md).