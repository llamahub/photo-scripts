#!/bin/bash
set -e

echo "========================================="
echo "Photo Scripts System Dependencies Setup"
echo "========================================="

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
else
    OS="unknown"
fi

echo "Detected OS: $OS"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install dependencies on Linux (Ubuntu/Debian)
install_linux() {
    echo "Installing system dependencies for Linux (Ubuntu/Debian)..."
    
    # Update package lists
    echo "Updating package lists..."
    sudo apt update
    
    # Install Python virtual environment support
    if ! command_exists python3; then
        echo "Installing Python 3..."
        sudo apt install -y python3 python3-pip
    else
        echo "✓ Python 3 already installed"
    fi
    
    if ! dpkg -l | grep -q python3-venv; then
        echo "Installing Python 3 virtual environment support..."
        sudo apt install -y python3-venv
    else
        echo "✓ Python 3 venv already installed"
    fi
    
    # Install ExifTool
    if ! command_exists exiftool; then
        echo "Installing ExifTool for EXIF metadata processing..."
        sudo apt install -y libimage-exiftool-perl
    else
        echo "✓ ExifTool already installed"
    fi
    
    echo "✓ Linux dependencies installation complete"
}

# Function to install dependencies on macOS
install_macos() {
    echo "Installing system dependencies for macOS..."
    
    # Check if Homebrew is installed
    if ! command_exists brew; then
        echo "Homebrew not found. Please install Homebrew first:"
        echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    
    # Install Python if needed
    if ! command_exists python3; then
        echo "Installing Python 3..."
        brew install python
    else
        echo "✓ Python 3 already installed"
    fi
    
    # Install ExifTool
    if ! command_exists exiftool; then
        echo "Installing ExifTool for EXIF metadata processing..."
        brew install exiftool
    else
        echo "✓ ExifTool already installed"
    fi
    
    echo "✓ macOS dependencies installation complete"
}

# Function to show Windows instructions
install_windows() {
    echo "Windows system dependencies setup:"
    echo ""
    echo "1. Python 3.8+:"
    echo "   Download and install from: https://www.python.org/downloads/"
    echo "   Make sure to check 'Add Python to PATH' during installation"
    echo ""
    echo "2. ExifTool:"
    echo "   Download from: https://exiftool.org/"
    echo "   Extract and add to your PATH, or place exiftool.exe in your project directory"
    echo ""
    echo "After installing these dependencies manually, you can run:"
    echo "  ./setenv --recreate"
    echo ""
    echo "Note: This script cannot automatically install dependencies on Windows."
    echo "Please install them manually and re-run this script to verify."
}

# Function to verify installations
verify_dependencies() {
    echo ""
    echo "Verifying installed dependencies..."
    
    # Check Python
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version)
        echo "✓ $PYTHON_VERSION"
    else
        echo "✗ Python 3 not found"
        return 1
    fi
    
    # Check ExifTool
    if command_exists exiftool; then
        EXIFTOOL_VERSION=$(exiftool -ver 2>/dev/null || echo "unknown")
        echo "✓ ExifTool version $EXIFTOOL_VERSION"
    else
        echo "⚠️  ExifTool not found - photo organization will use filename parsing fallback"
    fi
    
    echo ""
}

# Main installation logic
main() {
    case $OS in
        "linux")
            install_linux
            ;;
        "macOS")
            install_macos
            ;;
        "windows")
            install_windows
            ;;
        *)
            echo "Unsupported operating system: $OSTYPE"
            echo "Please install dependencies manually:"
            echo "- Python 3.8+"
            echo "- ExifTool (libimage-exiftool-perl)"
            exit 1
            ;;
    esac
    
    verify_dependencies
    
    echo "========================================="
    echo "System dependencies setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Navigate to a project directory (e.g., cd EXIF/)"
    echo "2. Run: ./setenv --recreate"
    echo "3. Run: source activate.sh"
    echo "4. Start using the photo scripts!"
    echo "========================================="
}

# Handle command line arguments
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    echo "Photo Scripts System Dependencies Setup"
    echo ""
    echo "This script installs required system dependencies:"
    echo "- Python 3.8+"
    echo "- Python virtual environment support"
    echo "- ExifTool (for EXIF metadata processing)"
    echo ""
    echo "Usage:"
    echo "  $0          # Install dependencies for current OS"
    echo "  $0 --help   # Show this help message"
    echo ""
    echo "Supported platforms:"
    echo "- Linux (Ubuntu/Debian): Installs via apt"
    echo "- macOS: Installs via Homebrew"
    echo "- Windows: Shows manual installation instructions"
    exit 0
fi

# Run main installation
main