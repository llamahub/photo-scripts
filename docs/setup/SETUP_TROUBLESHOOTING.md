# System Setup Troubleshooting

This guide helps resolve common issues when setting up the photo-scripts framework.

## Quick Reference

```bash
# Install system dependencies
./setup-system-deps.sh

# Setup Python environment
cd EXIF/  # or any project directory
./setenv --recreate
source activate.sh

# Verify setup
python -c "from exif.image_data import ImageData; print('✓ Setup successful')"
```

## Common Issues

### 1. ExifTool Not Found

**Symptoms:**
- Warning: "ExifTool not found" during setup
- Photos organized by filename instead of EXIF dates
- `exiftool: command not found` errors

**Solutions:**

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install libimage-exiftool-perl
```

**macOS:**
```bash
# Install Homebrew first if needed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install ExifTool
brew install exiftool
```

**Windows:**
1. Download ExifTool from https://exiftool.org/
2. Extract `exiftool(-k).exe` and rename to `exiftool.exe` 
3. Either:
   - Add the directory to your PATH, or
   - Copy `exiftool.exe` to your project directory

**Verification:**
```bash
exiftool -ver  # Should show version number
```

### 2. Python Version Issues

**Symptoms:**
- "Python 3.8+ required" error
- Import errors or compatibility issues

**Solutions:**

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**macOS:**
```bash
brew install python
```

**Windows:**
- Download Python 3.8+ from https://www.python.org/downloads/
- Check "Add Python to PATH" during installation

**Verification:**
```bash
python3 --version  # Should show 3.8 or higher
```

### 3. Permission Issues

**Symptoms:**
- "Permission denied" errors during setup
- Cannot create virtual environment

**Solutions:**

**Linux/macOS:**
```bash
# Make setup script executable
chmod +x setup-system-deps.sh

# Run with proper permissions
sudo ./setup-system-deps.sh  # For system package installation
```

**Virtual Environment Issues:**
```bash
# Clean up and recreate
rm -rf .venv
./setenv --recreate
```

### 4. Import Errors

**Symptoms:**
- `ModuleNotFoundError` when running scripts
- "No module named 'exif'" errors

**Solutions:**

**Check virtual environment activation:**
```bash
source activate.sh  # or source .venv/bin/activate
which python        # Should show .venv/bin/python
```

**Reinstall dependencies:**
```bash
./setenv --recreate
source activate.sh
```

**Verify installation:**
```bash
python -c "import exif; print('✓ Module imported successfully')"
```

### 5. Dev Container Issues

**Symptoms:**
- Dependencies not installing in dev container
- Container setup fails

**Solutions:**

**Rebuild container:**
1. VS Code: `Ctrl+Shift+P` → "Dev Containers: Rebuild Container"
2. Or delete container and reopen

**Manual dependency installation:**
```bash
# Inside dev container
sudo apt update
sudo apt install libimage-exiftool-perl
```

**Check setup script:**
```bash
./setup-system-deps.sh --help
./setup-system-deps.sh
```

## Platform-Specific Notes

### Ubuntu/Debian
- Requires `sudo` for system package installation
- All dependencies available via `apt`
- Script handles everything automatically

### macOS
- Requires Homebrew to be installed first
- Python might conflict with system version
- Use `python3` and `pip3` explicitly

### Windows
- Manual installation required for most dependencies
- Path configuration often needed
- Consider using Windows Subsystem for Linux (WSL)

## Verification Commands

After setup, verify everything works:

```bash
# System dependencies
python3 --version
exiftool -ver

# Python environment
source activate.sh
python -c "import sys; print(f'Python: {sys.executable}')"

# Project modules
python -c "from exif.image_data import ImageData; print('✓ EXIF module OK')"
python -c "from exif.photo_organizer import PhotoOrganizer; print('✓ Organizer module OK')"

# Full workflow test
python scripts/organize.py --help
```

## Getting Help

If issues persist:

1. **Check logs**: Look for detailed error messages in terminal output
2. **Verify versions**: Ensure Python 3.8+ and recent ExifTool
3. **Clean install**: Remove `.venv` and run `./setenv --recreate`
4. **Platform docs**: Check platform-specific installation guides
5. **Issue tracker**: Report persistent issues with full error details

## Environment Information

To help with troubleshooting, collect this information:

```bash
# System info
uname -a
python3 --version
exiftool -ver 2>/dev/null || echo "ExifTool not found"

# Environment info
echo "PATH: $PATH"
echo "PYTHONPATH: $PYTHONPATH"
which python3
ls -la .venv/bin/ 2>/dev/null || echo "No .venv found"
```