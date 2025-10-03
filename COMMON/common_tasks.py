"""Invoke tasks for project management - all tools run from local .venv."""

import os
import sys
import time
from pathlib import Path
from invoke import task, Context

# Import logging for gtest task
try:
    from common.logging import ScriptLogging
except ImportError:
    ScriptLogging = None


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


def get_temp_dir(name_prefix="temp"):
    """Create a temporary directory that persists and is visible for debugging.
    
    Args:
        name_prefix: Prefix for the temporary directory name
        
    Returns:
        Path object for the created temporary directory
    """
    temp_base = Path(".tmp")
    temp_base.mkdir(exist_ok=True)
    
    # Create a unique directory name with timestamp
    timestamp = int(time.time())
    temp_dir = temp_base / f"{name_prefix}_{timestamp}"
    temp_dir.mkdir(exist_ok=True)
    
    return temp_dir


@task
def setup(ctx):
    """Setup the project environment."""
    print("Setting up project environment...")
    ctx.run("python setenv.py", pty=True)


@task
def clean(ctx):
    """Clean build artifacts and temporary directories."""
    ensure_venv(ctx)
    print("Cleaning build artifacts and temporary directories...")
    
    # Remove common build directories
    dirs_to_clean = [
        ".pytest_cache",
        "__pycache__",
        "*.egg-info",
        "build",
        "dist",
        ".coverage",
        ".mypy_cache",
        ".tmp"
    ]
    
    python_path = get_venv_python()
    
    # Clean temporary directories first (with informative output)
    tmp_dir = Path(".tmp")
    if tmp_dir.exists():
        print(f"Removing temporary directory: {tmp_dir.absolute()}")
        if os.name == "nt":  # Windows
            ctx.run(f'rd /s /q "{tmp_dir}"', warn=True)
        else:  # Unix-like
            ctx.run(f"rm -rf '{tmp_dir}'", warn=True)
        print(f"  ✓ Removed {tmp_dir}")
    else:
        print(f"No temporary directory found: {tmp_dir}")
    
    # Clean other build artifacts with explicit reporting
    for pattern in dirs_to_clean:
        if pattern == ".tmp":
            continue  # Already handled above
        
        print(f"\nCleaning pattern: {pattern}")
        
        if os.name == "nt":  # Windows
            # Find and report directories before removing
            result = ctx.run(f'for /d /r . %d in ({pattern}) do @echo Found: %d', warn=True, hide=True)
            if result and result.stdout.strip():
                print(result.stdout.strip())
            ctx.run(f'for /d /r . %d in ({pattern}) do @if exist "%d" rd /s /q "%d"', warn=True)
            ctx.run(f'del /s /q {pattern} 2>nul', warn=True)
        else:  # Unix-like
            # Find and report what will be removed
            result = ctx.run(f"find . -name '{pattern}' 2>/dev/null", warn=True, hide=True)
            if result and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        print(f"  Found: {line}")
            # Now remove them
            ctx.run(f"find . -name '{pattern}' -exec rm -rf {{}} + 2>/dev/null || true")
            
        # Verify removal
        if os.name != "nt":
            verify_result = ctx.run(f"find . -name '{pattern}' 2>/dev/null", warn=True, hide=True)
            if verify_result and not verify_result.stdout.strip():
                print(f"  ✓ Cleaned all {pattern} entries")
            else:
                remaining = verify_result.stdout.strip().split('\n') if verify_result.stdout.strip() else []
                if remaining:
                    print(f"  ⚠ Some {pattern} entries may remain: {len(remaining)} found")
        
    print("\n✓ Cleanup completed!")


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


@task
def gtest(ctx, safe_only=False):
    """Run global tests across all projects - comprehensive testing framework.
    
    This task runs tests across all projects in the workspace:
    1. Runs unit tests in each project with a 'tests' folder
    2. Runs safe invoke tasks in each project  
    3. Runs scripts with --help to validate they work
    
    Args:
        safe_only: If True, only run non-destructive tasks (default: False)
    """
    import os
    from pathlib import Path
    
    # Setup logging
    logger = ScriptLogging.get_script_logger(debug=True)
    
    # Find all projects (directories with tasks.py or pyproject.toml)
    workspace_root = Path.cwd()
    if workspace_root.name != "photo-scripts":
        # Try to find workspace root
        while workspace_root.name != "photo-scripts" and workspace_root != workspace_root.parent:
            workspace_root = workspace_root.parent
        if workspace_root.name != "photo-scripts":
            workspace_root = Path("/workspaces/photo-scripts")
    
    projects = []
    for item in workspace_root.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            if (item / "tasks.py").exists() or (item / "pyproject.toml").exists():
                projects.append(item)
    
    logger.info("=" * 80)
    logger.info(f" GLOBAL TEST RUNNER - {'SAFE MODE' if safe_only else 'FULL MODE'}")
    logger.info("=" * 80)
    logger.info(f"Workspace root: {workspace_root}")
    logger.info(f"Found projects: {[p.name for p in projects]}")
    
    # Define task categories
    safe_tasks = ["test", "lint", "status", "scripts", "format"]
    destructive_tasks = ["setup", "install", "build", "deps"]
    
    # Always run clean first if available, then other tasks
    clean_task = ["clean"]
    tasks_to_run = safe_tasks
    if not safe_only:
        tasks_to_run.extend(destructive_tasks)
        logger.warning("Running in FULL mode - includes potentially destructive tasks!")
        logger.warning("Tasks that may modify system: clean, " + ", ".join(destructive_tasks))
    
    total_passed = 0
    total_failed = 0
    results = []
    
    for project in projects:
        logger.info("=" * 60)
        logger.info(f"TESTING PROJECT: {project.name}")
        logger.info("=" * 60)
        
        os.chdir(project)
        project_passed = 0
        project_failed = 0
        
        # 1. Run unit tests if tests directory exists
        if (project / "tests").exists():
            logger.info(f"🧪 Running unit tests in {project.name}")
            try:
                result = ctx.run("inv test", hide=True, warn=True)
                if result.return_code == 0:
                    logger.info(f"✅ Unit tests PASSED in {project.name}")
                    project_passed += 1
                else:
                    logger.error(f"❌ Unit tests FAILED in {project.name}")
                    project_failed += 1
                results.append(f"{project.name}/tests: {'PASS' if result.return_code == 0 else 'FAIL'}")
            except Exception as e:
                logger.error(f"❌ Unit tests ERROR in {project.name}: {e}")
                project_failed += 1
                results.append(f"{project.name}/tests: ERROR")
        
        # 2. Run invoke tasks (clean first, then others)
        logger.info(f"⚙️  Running invoke tasks in {project.name}")
        
        # Get list of available tasks once
        try:
            task_check = ctx.run("inv --list", hide=True, warn=True)
            available_tasks = task_check.stdout
        except:
            available_tasks = ""
        
        # Run clean task first if available
        if "clean" in available_tasks:
            logger.info(f"   Running task: clean (cleanup first)")
            try:
                result = ctx.run("inv clean", hide=True, warn=True)
                if result.return_code == 0:
                    logger.info(f"   ✅ Task clean PASSED")
                    project_passed += 1
                else:
                    logger.error(f"   ❌ Task clean FAILED")
                    project_failed += 1
                results.append(f"{project.name}/clean: {'PASS' if result.return_code == 0 else 'FAIL'}")
            except Exception as e:
                logger.error(f"   ❌ Task clean ERROR: {e}")
                project_failed += 1
                results.append(f"{project.name}/clean: ERROR")
        
        # Run other tasks
        for task_name in tasks_to_run:
            try:
                if task_name in available_tasks:
                    logger.info(f"   Running task: {task_name}")
                    result = ctx.run(f"inv {task_name}", hide=True, warn=True)
                    if result.return_code == 0:
                        logger.info(f"   ✅ Task {task_name} PASSED")
                        project_passed += 1
                    else:
                        logger.error(f"   ❌ Task {task_name} FAILED")
                        project_failed += 1
                    results.append(f"{project.name}/{task_name}: {'PASS' if result.return_code == 0 else 'FAIL'}")
                else:
                    logger.info(f"   ⏭️  Task {task_name} not available")
            except Exception as e:
                logger.error(f"   ❌ Task {task_name} ERROR: {e}")
                project_failed += 1
                results.append(f"{project.name}/{task_name}: ERROR")
        
        # 3. Test scripts with --help
        scripts_dir = project / "scripts"
        if scripts_dir.exists():
            logger.info(f"📜 Testing scripts in {project.name}")
            script_files = [f for f in scripts_dir.glob("*.py") if f.name != "run.py"]
            
            for script_file in script_files:
                script_name = script_file.stem
                try:
                    logger.info(f"   Testing script: {script_name}")
                    # Test with --help to ensure script loads and parses args correctly
                    result = ctx.run(f"inv run --script {script_name} --args '--help'", hide=True, warn=True)
                    if result.return_code == 0:
                        logger.info(f"   ✅ Script {script_name} PASSED")
                        project_passed += 1
                    else:
                        logger.error(f"   ❌ Script {script_name} FAILED")
                        project_failed += 1
                    results.append(f"{project.name}/{script_name}: {'PASS' if result.return_code == 0 else 'FAIL'}")
                except Exception as e:
                    logger.error(f"   ❌ Script {script_name} ERROR: {e}")
                    project_failed += 1
                    results.append(f"{project.name}/{script_name}: ERROR")
        
        total_passed += project_passed
        total_failed += project_failed
        
        logger.info(f"Project {project.name} summary: {project_passed} passed, {project_failed} failed")
    
    # Final summary
    os.chdir(workspace_root)
    logger.info("=" * 80)
    logger.info(" GLOBAL TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total: {total_passed} passed, {total_failed} failed")
    logger.info("")
    logger.info("Detailed Results:")
    for result in results:
        status = "✅" if "PASS" in result else "❌"
        logger.info(f"  {status} {result}")
    
    if total_failed > 0:
        logger.error(f"❌ GLOBAL TESTS FAILED: {total_failed} failures")
        return 1
    else:
        logger.info(f"✅ ALL GLOBAL TESTS PASSED: {total_passed} tests")
        return 0