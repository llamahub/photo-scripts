#!/usr/bin/env python3
"""
Universal script runner for monorepo projects.

This script allows running other scripts in the scripts directory with arguments.
It can be used by any project in the monorepo.
"""

import sys
import subprocess
from pathlib import Path


def main():
    """Main entry point for the script runner."""
    # Check if we have at least one argument (the script name)
    if len(sys.argv) < 2:
        print("Usage: run.py <script_name> [script_args...]", file=sys.stderr)
        print("\nRun scripts from the current project's scripts directory or COMMON/scripts", file=sys.stderr)
        print("\nExamples:", file=sys.stderr)
        print("  run.py sample --help", file=sys.stderr)
        print("  run.py sample /path/to/photos", file=sys.stderr)
        print("  run.py sample --source /path/to/photos --target /tmp/sample", file=sys.stderr)
        return 1
    
    # Get script name and remaining args
    script_name = sys.argv[1]
    script_args = sys.argv[2:]
    
    # Get the scripts directories (local and COMMON)
    local_scripts_dir = Path.cwd() / "scripts"
    common_scripts_dir = Path(__file__).parent
    
    # Look for the script in local directory first, then COMMON
    script_path = None
    if (local_scripts_dir / f"{script_name}.py").exists():
        script_path = local_scripts_dir / f"{script_name}.py"
    elif (common_scripts_dir / f"{script_name}.py").exists():
        script_path = common_scripts_dir / f"{script_name}.py"
    
    # Check if the script exists
    if script_path is None or not script_path.exists():
        print(f"Error: Script '{script_name}.py' not found in scripts or COMMON/scripts", file=sys.stderr)
        
        # Show available scripts from both directories
        available_scripts = set()
        if local_scripts_dir.exists():
            available_scripts.update([f.stem for f in local_scripts_dir.glob("*.py") if f.name != "run.py"])
        if common_scripts_dir.exists():
            available_scripts.update([f.stem for f in common_scripts_dir.glob("*.py") if f.name != "run.py"])
        
        if available_scripts:
            print(f"Available scripts: {', '.join(sorted(available_scripts))}", file=sys.stderr)
        return 1
    
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
