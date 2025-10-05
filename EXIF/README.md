# EXIF Photo Processing Tools

A comprehensive Python framework for photo organization, metadata processing, and image management with EXIF data extraction capabilities.

## Quick Start

```bash
# Setup environment
./setenv --recreate
source activate.sh

# Run photo organization
python scripts/organize.py /path/to/photos /path/to/organized --dry-run

# Generate test images
python scripts/generate.py test_data.csv /path/to/output

# Select random samples
python scripts/select.py /path/to/photos /path/to/samples --files 10
```

## System Requirements

### Required Dependencies
- **Python 3.8+**: Core runtime
- **ExifTool**: EXIF metadata extraction (critical for photo date detection)

### Automated Setup
Use the project's system setup script to install all dependencies:

```bash
# From the project root directory
../setup-system-deps.sh     # Auto-detects OS and installs dependencies
```

**Manual Installation (if needed):**
```bash
# Ubuntu/Debian
sudo apt install python3-venv libimage-exiftool-perl

# macOS (requires Homebrew)
brew install python exiftool

# Windows
# Download Python from: https://www.python.org/downloads/
# Download ExifTool from: https://exiftool.org/
```

### Python Dependencies
Automatically installed via `./setenv`:
- PIL/Pillow: Image processing
- pytest: Testing framework
- invoke: Task runner

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