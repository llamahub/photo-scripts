#!/usr/bin/env python3
"""Environment setup script for project."""

import os
import sys
import subprocess
import venv
from pathlib import Path


def check_python_version():
    """Check if Python version is sufficient."""
    if sys.version_info < (3, 8):
        print(f"Python 3.8+ required, but you have {sys.version}")
        sys.exit(1)
    print(f"Using Python {sys.version}")


def create_venv(venv_path: Path) -> None:
    """Create virtual environment."""
    print(f"Creating virtual environment at {venv_path}")
    venv.create(venv_path, with_pip=True)


def get_pip_path(venv_path: Path) -> Path:
    """Get the pip executable path in the virtual environment."""
    if os.name == "nt":  # Windows
        return venv_path / "Scripts" / "pip.exe"
    else:  # Unix-like
        return venv_path / "bin" / "pip"


def get_python_path(venv_path: Path) -> Path:
    """Get the python executable path in the virtual environment."""
    if os.name == "nt":  # Windows
        return venv_path / "Scripts" / "python.exe"
    else:  # Unix-like
        return venv_path / "bin" / "python"


def install_dependencies(venv_path: Path, project_path: Path) -> None:
    """Install dependencies from pyproject.toml."""
    pip_path = get_pip_path(venv_path)
    pyproject_file = project_path / "pyproject.toml"
    requirements_file = project_path / "requirements.txt"  # Legacy support
    
    # Prefer pyproject.toml if it exists
    if pyproject_file.exists():
        print(f"Installing dependencies from {pyproject_file}")
        # Install in editable mode with dev dependencies
        subprocess.run([str(pip_path), "install", "-e", f"{project_path}[dev]"], check=True)
        
        # Also install invoke specifically to ensure it's available
        subprocess.run([str(pip_path), "install", "invoke"], check=True)
        
    elif requirements_file.exists():
        print(f"Installing requirements from {requirements_file} (legacy)")
        subprocess.run([str(pip_path), "install", "-r", str(requirements_file)], check=True)
        subprocess.run([str(pip_path), "install", "invoke"], check=True)
        
    else:
        print("No dependency file found, installing minimal dependencies...")
        minimal_deps = ["invoke", "pydantic", "python-dotenv", "pytest"]
        subprocess.run([str(pip_path), "install"] + minimal_deps, check=True)


def setup_environment(project_path: Path = None) -> None:
    """Setup virtual environment for project."""
    check_python_version()
    
    if project_path is None:
        project_path = Path.cwd()
    
    venv_path = project_path / ".venv"
    requirements_file = project_path / "requirements.txt"
    
    # Create virtual environment if it doesn't exist
    if not venv_path.exists():
        create_venv(venv_path)
    else:
        print(f"Virtual environment already exists at {venv_path}")
    
    # Install dependencies
    install_dependencies(venv_path, project_path)
    
    # Install common library in development mode if this is a project
    project_root = project_path.parent if project_path.name != "common" else project_path.parent
    common_path = project_root / "common"
    
    if common_path.exists() and project_path != common_path:
        pip_path = get_pip_path(venv_path)
        print(f"Installing common library from {common_path}")
        subprocess.run([str(pip_path), "install", "-e", str(common_path)], check=True)
    
    # Create activation helper scripts
    create_activation_helpers(venv_path, project_path)
    
    print("\n" + "="*50)
    print("Environment setup complete!")
    print("="*50)
    
    if os.name == "nt":  # Windows
        print(f"To activate: {venv_path}\\Scripts\\activate.bat")
        print("Or use: .\\activate.bat")
    else:  # Unix-like
        print(f"To activate: source {venv_path}/bin/activate")
        print("Or use: source ./setenv")
    
    print("\nAfter activation, you can use:")
    print("  invoke test    # Run tests")
    print("  invoke build   # Build project")
    print("  invoke run     # Run project")


def create_activation_helpers(venv_path: Path, project_path: Path):
    """Create helper scripts for easy activation."""
    
    if os.name == "nt":  # Windows
        activate_script = project_path / "activate.bat"
        with open(activate_script, "w") as f:
            f.write(f'@echo off\n')
            f.write(f'call "{venv_path}\\Scripts\\activate.bat"\n')
        print(f"Created activation helper: {activate_script}")
    else:  # Unix-like
        activate_script = project_path / "activate.sh"
        with open(activate_script, "w") as f:
            f.write(f'#!/bin/bash\n')
            f.write(f'source "{venv_path}/bin/activate"\n')
        
        # Make it executable
        activate_script.chmod(0o755)
        print(f"Created activation helper: {activate_script}")


if __name__ == "__main__":
    setup_environment()