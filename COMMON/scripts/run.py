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
        print("\nRun scripts from the current project's scripts directory", file=sys.stderr)
        print("\nExamples:", file=sys.stderr)
        print("  run.py sample --help", file=sys.stderr)
        print("  run.py sample /path/to/photos", file=sys.stderr)
        print("  run.py sample --source /path/to/photos --target /tmp/sample", file=sys.stderr)
        return 1
    
    # Get script name and remaining args
    script_name = sys.argv[1]
    script_args = sys.argv[2:]
    
    # Get the scripts directory (in the current working directory)
    scripts_dir = Path.cwd() / "scripts"
    script_path = scripts_dir / f"{script_name}.py"
    
    # Check if the script exists
    if not script_path.exists():
        print(f"Error: Script '{script_name}.py' not found in {scripts_dir}", file=sys.stderr)
        available_scripts = [f.stem for f in scripts_dir.glob("*.py") if f.name != "run.py"]
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
