# Photo Scripts Setup Guide

Complete setup instructions for the photo-scripts framework with automatic dependency management.

## Overview

The photo-scripts framework provides three setup methods:
1. **Dev Container** (Recommended) - Automatic setup in isolated environment
2. **Automated Local Setup** - One-command dependency installation
3. **Manual Setup** - Step-by-step installation for custom environments

## Method 1: Dev Container Setup (Recommended)

### Prerequisites
- VS Code with Dev Containers extension
- Docker Desktop

### Steps
1. Open the project in VS Code
2. Click "Reopen in Container" when prompted
3. Wait for automatic dependency installation
4. Navigate to project: `cd EXIF/`
5. Setup Python environment: `./setenv --recreate && source activate.sh`
6. Test: `inv r -n organize -a '--help'`

**✅ Benefits:**
- Zero manual dependency management
- Consistent environment across all machines
- Automatic ExifTool and Python installation
- Isolated from host system

## Method 2: Automated Local Setup

### Prerequisites
- Linux (Ubuntu/Debian) or macOS
- `sudo` privileges (Linux) or Homebrew (macOS)

### Steps
1. Clone the repository
2. Run system setup: `./setup-system-deps.sh`
3. Navigate to project: `cd EXIF/`
4. Setup Python environment: `./setenv --recreate && source activate.sh`
5. Test: `inv r -n organize -a '--help'`

**✅ Benefits:**
- One-command dependency installation
- Works on local machine without containers
- Automatic OS detection and appropriate installation

## Method 3: Manual Setup

### Prerequisites
- Python 3.8+
- ExifTool

### Steps

#### Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-venv libimage-exiftool-perl
```

**macOS:**
```bash
brew install python exiftool
```

**Windows:**
- Install Python from https://www.python.org/downloads/
- Install ExifTool from https://exiftool.org/

#### Setup Project Environment
```bash
cd EXIF/                    # Navigate to project
./setenv --recreate         # Create virtual environment
source activate.sh          # Activate environment
inv r -n organize -a '--help' # Test installation
```

## Verification

After setup, verify everything works:

```bash
# Check system dependencies
python3 --version          # Should be 3.8+
exiftool -ver              # Should show version number

# Check Python environment
source activate.sh         # Should activate .venv
which python               # Should show .venv/bin/python

# Test project modules
python -c "from exif.image_data import ImageData; print('✓ Setup successful')"

# Test CLI scripts
python scripts/organize.py --help
python scripts/generate.py --help
python scripts/select.py --help
```

## Next Steps

After successful setup:

1. **Try the Quick Demo:**
   ```bash
   # Create some test images
   python scripts/generate.py test_data.csv /tmp/test_images --sample 5
   
   # Organize them by date
   python scripts/organize.py /tmp/test_images /tmp/organized --dry-run
   
   # Create random sample
   python scripts/select.py /tmp/test_images /tmp/sample --files 3
   ```

2. **Read the Documentation:**
   - [EXIF/README.md](EXIF/README.md) - Photo processing tools
   - [COMMON/ARCHITECTURE.md](COMMON/ARCHITECTURE.md) - Framework details
   - [EXIF/TESTING_STRATEGY.md](EXIF/TESTING_STRATEGY.md) - Testing approach

3. **Explore Example Use Cases:**
   - Photo organization by date and decade
   - EXIF metadata extraction and analysis
   - Test image generation for development
   - Random photo sampling with sidecar preservation

## Troubleshooting

If you encounter issues, see [SETUP_TROUBLESHOOTING.md](SETUP_TROUBLESHOOTING.md) for:
- Common error solutions
- Platform-specific notes
- Verification commands
- Getting help resources

## System Architecture

```
photo-scripts/
├── setup-system-deps.sh           # System dependency installer
├── SETUP_TROUBLESHOOTING.md       # Troubleshooting guide
├── .devcontainer/
│   └── devcontainer.json          # Dev container configuration
├── COMMON/
│   ├── setenv.py                   # Python environment setup
│   └── ARCHITECTURE.md            # Framework documentation
└── EXIF/
    ├── setenv                      # Project-specific environment
    ├── src/exif/                   # Business logic classes
    ├── scripts/                    # CLI interfaces
    └── tests/                      # Comprehensive test suite
```

The framework separates concerns:
- **System Setup**: `setup-system-deps.sh` handles OS-level dependencies
- **Python Setup**: `setenv.py` manages virtual environments and packages
- **Project Setup**: Individual project `setenv` scripts configure environments
- **Container Setup**: `.devcontainer/` provides isolated development environment

This layered approach ensures reliable setup across different environments while maintaining flexibility for local development preferences.