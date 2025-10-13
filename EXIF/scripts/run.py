#!/usr/bin/env python3
"""
Enhanced script runner for EXIF project.

This script allows running scripts from both EXIF/scripts and COMMON/scripts directories,
with EXIF scripts taking precedence over COMMON scripts when names clash.
"""

import sys
import subprocess
from pathlib import Path


def main():
    """Main entry point for the script runner."""
    # Check if we have at least one argument (the script name)
    if len(sys.argv) < 2:
        print("Usage: run.py <script_name> [script_args...]", file=sys.stderr)
        print("\nRun scripts from EXIF/scripts or COMMON/scripts directories", file=sys.stderr)
        print("EXIF scripts take precedence over COMMON scripts", file=sys.stderr)
        
        # Show available scripts
        local_scripts_dir = Path.cwd() / "scripts"
        common_scripts_dir = Path.cwd().parent / "COMMON" / "scripts"
        
        local_scripts = []
        common_scripts = []
        
        if local_scripts_dir.exists():
            local_scripts = [f.stem for f in local_scripts_dir.glob("*.py") if f.name != "run.py"]
        
        if common_scripts_dir.exists():
            common_scripts = [f.stem for f in common_scripts_dir.glob("*.py") if f.name != "run.py"]
        
        all_scripts = sorted(set(local_scripts + common_scripts))
        
        if all_scripts:
            print(f"\nAvailable scripts:", file=sys.stderr)
            for script in all_scripts:
                if script in local_scripts and script in common_scripts:
                    print(f"  {script} (EXIF - takes precedence)", file=sys.stderr)
                elif script in local_scripts:
                    print(f"  {script} (EXIF)", file=sys.stderr)
                else:
                    print(f"  {script} (COMMON)", file=sys.stderr)
        
        print("\nExamples:", file=sys.stderr)
        print("  run.py organize --help", file=sys.stderr)
        print("  run.py clean /path --dry-run", file=sys.stderr)
        print("  run.py sample /path/to/photos", file=sys.stderr)
        return 1
    
    # Get script name and remaining args
    script_name = sys.argv[1]
    script_args = sys.argv[2:]
    
    # Get the scripts directories (local EXIF first, then COMMON as fallback)
    local_scripts_dir = Path.cwd() / "scripts"
    common_scripts_dir = Path.cwd().parent / "COMMON" / "scripts"
    
    # Check for script in EXIF/scripts first (precedence)
    local_script_path = local_scripts_dir / f"{script_name}.py"
    common_script_path = common_scripts_dir / f"{script_name}.py"
    
    script_path = None
    source = None
    
    if local_script_path.exists():
        script_path = local_script_path
        source = "EXIF"
    elif common_script_path.exists():
        script_path = common_script_path
        source = "COMMON"
    
    # If script not found in either location
    if script_path is None:
        print(f"Error: Script '{script_name}.py' not found in EXIF or COMMON scripts", file=sys.stderr)
        
        # Show available scripts from both directories
        local_scripts = []
        common_scripts = []
        
        if local_scripts_dir.exists():
            local_scripts = [f.stem for f in local_scripts_dir.glob("*.py") if f.name != "run.py"]
        
        if common_scripts_dir.exists():
            common_scripts = [f.stem for f in common_scripts_dir.glob("*.py") if f.name != "run.py"]
        
        all_scripts = sorted(set(local_scripts + common_scripts))
        
        if all_scripts:
            print(f"Available scripts:", file=sys.stderr)
            for script in all_scripts:
                if script in local_scripts and script in common_scripts:
                    print(f"  {script} (EXIF - takes precedence)", file=sys.stderr)
                elif script in local_scripts:
                    print(f"  {script} (EXIF)", file=sys.stderr)
                else:
                    print(f"  {script} (COMMON)", file=sys.stderr)
        else:
            print("No scripts found in either EXIF or COMMON directories", file=sys.stderr)
        return 1
    
    # Show which script we're running
    print(f"Running {source} script '{script_name}' with args: {' '.join(script_args)}")
    
    # Run the script with the provided arguments
    try:
        cmd = [sys.executable, str(script_path)] + script_args
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error running script: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())