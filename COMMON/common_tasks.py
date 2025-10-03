"""Invoke tasks for project management - all tools run from local .venv."""

import os
import sys
from pathlib import Path
from invoke import task, Context


def get_venv_python():
    """Get the path to the virtual environment's python executable."""
    venv_path = Path(".venv")
    if os.name == "nt":  # Windows
        return venv_path / "Scripts" / "python.exe"
    else:  # Unix-like
        return venv_path / "bin" / "python"


def get_venv_executable(tool_name):
    """Get the path to a tool in the virtual environment."""
    venv_path = Path(".venv")
    if os.name == "nt":  # Windows
        return venv_path / "Scripts" / tool_name
    else:  # Unix-like
        return venv_path / "bin" / tool_name


def ensure_venv(ctx):
    """Ensure virtual environment exists before running tasks."""
    venv_path = Path(".venv")
    if not venv_path.exists():
        print("Virtual environment not found. Run 'python setenv.py' first.")
        sys.exit(1)


@task
def setup(ctx):
    """Setup the project environment."""
    print("Setting up project environment...")
    ctx.run("python setenv.py", pty=True)


@task
def clean(ctx):
    """Clean build artifacts."""
    ensure_venv(ctx)
    print("Cleaning build artifacts...")
    
    # Remove common build directories
    dirs_to_clean = [
        ".pytest_cache",
        "__pycache__",
        "*.egg-info",
        "build",
        "dist",
        ".coverage",
        ".mypy_cache"
    ]
    
    python_path = get_venv_python()
    for pattern in dirs_to_clean:
        if os.name == "nt":  # Windows
            ctx.run(f'for /d /r . %d in ({pattern}) do @if exist "%d" rd /s /q "%d"', warn=True)
            ctx.run(f'del /s /q {pattern} 2>nul', warn=True)
        else:  # Unix-like
            ctx.run(f"find . -name '{pattern}' -exec rm -rf {{}} + 2>/dev/null || true")


@task
def lint(ctx):
    """Run linting tools."""
    ensure_venv(ctx)
    print("Running linting...")
    
    python_path = get_venv_python()
    
    # Run black
    print("Running black...")
    ctx.run(f"{python_path} -m black --check src/ tests/", warn=True)
    
    # Run flake8
    print("Running flake8...")
    ctx.run(f"{python_path} -m flake8 src/ tests/", warn=True)
    
    # Run mypy
    print("Running mypy...")
    ctx.run(f"{python_path} -m mypy src/", warn=True)


@task
def format(ctx):
    """Format code with black."""
    ensure_venv(ctx)
    print("Formatting code...")
    python_path = get_venv_python()
    ctx.run(f"{python_path} -m black src/ tests/")


@task
def test(ctx, coverage=True, verbose=False):
    """Run tests."""
    ensure_venv(ctx)
    print("Running tests...")
    
    python_path = get_venv_python()
    cmd = f"{python_path} -m pytest"
    if coverage:
        cmd += " --cov=src --cov-report=html --cov-report=term"
    if verbose:
        cmd += " -v"
    
    ctx.run(cmd, pty=True)


@task
def build(ctx):
    """Build the project."""
    ensure_venv(ctx)
    print("Building project...")
    
    python_path = get_venv_python()
    
    # Clean first
    clean(ctx)
    
    # Run linting
    lint(ctx)
    
    # Run tests
    test(ctx)
    
    # Build package
    #ctx.run(f"{python_path} -m build", warn=True)


@task
def run(ctx, script=None, args="", env="dev"):
    """Run a script from the scripts directory or the main project.
    
    Args:
        script: Name of the script to run (without .py extension)
        args: Arguments to pass to the script (as a single string)
        env: Environment to run in (default: dev)
    
    Examples:
        invoke run --script sample --args "/path/to/photos"
        invoke run --script sample --args "--source /path/to/photos --target /tmp/sample --files 50"
        invoke run  # Run main project without script
    """
    ensure_venv(ctx)
    
    python_path = get_venv_python()
    
    # Set environment
    os.environ["ENVIRONMENT"] = env
    
    if script:
        # Check if local scripts/run.py exists, otherwise use common one
        local_run_script = Path("scripts/run.py")
        common_run_script = Path(__file__).parent / "scripts" / "run.py"
        
        if local_run_script.exists():
            run_script_path = local_run_script
        elif common_run_script.exists():
            run_script_path = common_run_script
            # Copy common run.py to local scripts directory if it doesn't exist
            scripts_dir = Path("scripts")
            scripts_dir.mkdir(exist_ok=True)
        else:
            # Fallback: try to run script directly
            script_path = Path("scripts") / f"{script}.py"
            if script_path.exists():
                print(f"Running script '{script}' directly with args: {args}")
                cmd = f"{python_path} {script_path}"
                if args:
                    cmd += f" {args}"
                ctx.run(cmd, pty=True)
                return
            else:
                print(f"Error: Script '{script}.py' not found in scripts/ directory")
                return
        
        # Run specific script through run.py
        print(f"Running script '{script}' with args: {args}")
        cmd = f"{python_path} {run_script_path} {script}"
        if args:
            cmd += f" {args}"
        ctx.run(cmd, pty=True)
    else:
        # Run main project
        print(f"Running project in {env} environment...")
        main_script = Path("src") / Path.cwd().name / "main.py"
        if main_script.exists():
            ctx.run(f"{python_path} {main_script}", pty=True)
        elif Path("scripts/run.py").exists():
            ctx.run(f"{python_path} scripts/run.py", pty=True)
        else:
            # If no main script, show available scripts
            print("No main script found. Available scripts:")
            scripts_dir = Path("scripts")
            if scripts_dir.exists():
                available_scripts = [f.stem for f in scripts_dir.glob("*.py") if f.name != "run.py"]
                if available_scripts:
                    print(f"  {', '.join(sorted(available_scripts))}")
                    print(f"\nUse: invoke run --script <script_name> --args '<arguments>'")
                else:
                    print("  No scripts found in scripts/ directory")
            else:
                print("  No scripts/ directory found")


@task
def install(ctx, dev=False):
    """Install the project."""
    ensure_venv(ctx)
    print("Installing project...")
    
    python_path = get_venv_python()
    pip_path = get_venv_python().parent / ("pip.exe" if os.name == "nt" else "pip")
    
    if dev:
        ctx.run(f"{pip_path} install -e .", pty=True)
    else:
        ctx.run(f"{pip_path} install .", pty=True)


@task
def deps(ctx):
    """Update dependencies."""
    ensure_venv(ctx)
    print("Updating dependencies...")
    
    pip_path = get_venv_python().parent / ("pip.exe" if os.name == "nt" else "pip")
    
    # Check if pyproject.toml exists
    if Path("pyproject.toml").exists():
        ctx.run(f"{pip_path} install -e .[dev]", pty=True)
    elif Path("requirements.txt").exists():
        ctx.run(f"{pip_path} install -r requirements.txt", pty=True)


@task
def shell(ctx):
    """Start a shell with the virtual environment activated."""
    ensure_venv(ctx)
    venv_path = Path(".venv")
    
    if os.name == "nt":  # Windows
        activate_script = venv_path / "Scripts" / "activate.bat"
        print(f"Starting shell with virtual environment...")
        print(f"Virtual environment: {venv_path.absolute()}")
        ctx.run(f'cmd /k "{activate_script}"')
    else:  # Unix-like
        activate_script = venv_path / "bin" / "activate"
        shell = os.environ.get("SHELL", "/bin/bash")
        print(f"Starting shell with virtual environment...")
        print(f"Virtual environment: {venv_path.absolute()}")
        ctx.run(f'bash --rcfile <(echo "source {activate_script}; echo \'Virtual environment activated: {venv_path.absolute()}\'") -i')


@task
def scripts(ctx):
    """List available scripts."""
    scripts_dir = Path("scripts")
    print("=== Available Scripts ===")
    
    if scripts_dir.exists():
        available_scripts = [f.stem for f in scripts_dir.glob("*.py") if f.name != "run.py"]
        if available_scripts:
            for script in sorted(available_scripts):
                script_path = scripts_dir / f"{script}.py"
                # Try to get the docstring
                try:
                    with open(script_path, 'r') as f:
                        lines = f.readlines()
                        docstring = ""
                        in_docstring = False
                        for line in lines[1:10]:  # Check first few lines after shebang
                            if '"""' in line and not in_docstring:
                                in_docstring = True
                                docstring = line.split('"""')[1].strip()
                                if '"""' in docstring:  # Single line docstring
                                    docstring = docstring.split('"""')[0].strip()
                                    break
                            elif in_docstring and '"""' in line:
                                break
                            elif in_docstring:
                                docstring += " " + line.strip()
                        
                        if docstring:
                            print(f"  {script:<15} - {docstring}")
                        else:
                            print(f"  {script}")
                except:
                    print(f"  {script}")
            
            print(f"\nUsage: invoke run --script <script_name> --args '<arguments>'")
            # Check where run.py is located
            if Path("scripts/run.py").exists():
                print(f"   or: python scripts/run.py <script_name> [arguments...]")
            else:
                common_run = Path(__file__).parent / "scripts" / "run.py"
                if common_run.exists():
                    print(f"   or: python {common_run} <script_name> [arguments...]")
        else:
            print("  No scripts found")
    else:
        print("  No scripts directory found")


@task
def status(ctx):
    """Show project status and virtual environment info."""
    venv_path = Path(".venv")
    python_path = get_venv_python()
    
    print("=== Project Status ===")
    print(f"Project directory: {Path.cwd()}")
    print(f"Virtual environment: {venv_path.absolute()}")
    print(f"Virtual environment exists: {venv_path.exists()}")
    
    if venv_path.exists():
        print(f"Python executable: {python_path}")
        # Show installed packages
        pip_path = python_path.parent / ("pip.exe" if os.name == "nt" else "pip")
        print("\n=== Installed Packages ===")
        ctx.run(f"{pip_path} list", pty=True)
    else:
        print("Run 'python setenv.py' or 'invoke setup' to create virtual environment.")