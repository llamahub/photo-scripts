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


def task_header(task_name: str, description: str, ctx: Context = None, **kwargs):
    """Print a standard header for invoke tasks.
    
    Args:
        task_name: Name of the task
        description: Brief description of what the task does
        ctx: Invoke context (optional, used to get actual args)
        **kwargs: Task arguments to display
    """
    print("=" * 80)
    print(f"=== [{task_name}] {description}")
    print("=" * 80)
    
    # Build the command line that was used
    cmd_parts = ["> invoke", task_name]
    
    # Add arguments if provided
    if kwargs:
        for key, value in kwargs.items():
            if value is True:
                cmd_parts.append(f"--{key.replace('_', '-')}")
            elif value is not False and value is not None:
                cmd_parts.append(f"--{key.replace('_', '-')} {value}")
    
    print(" ".join(cmd_parts))
    print()


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
    task_header("setup", "Setup the project environment", ctx)
    ctx.run("python setenv.py", pty=True)


@task
def clean(ctx, temp_age_hours=None):
    """Clean build artifacts and temporary directories.
    
    Args:
        temp_age_hours: Only clean temporary files older than this many hours.
                       If not specified, clean all temporary files.
    """
    task_header("clean", "Clean build artifacts and temporary directories", ctx, 
                temp_age_hours=temp_age_hours)
    ensure_venv(ctx)
    
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
    
    # Use centralized temp management for cleaning
    try:
        from common.temp import TempManager
        print("Using centralized temp management...")
        
        # List what will be cleaned
        temp_items = TempManager.list_persistent_temps()
        if temp_items:
            print(f"Found {len(temp_items)} temporary items:")
            for item in temp_items[:10]:  # Show first 10
                print(f"  - {item}")
            if len(temp_items) > 10:
                print(f"  ... and {len(temp_items) - 10} more")
        
        # Clean temporary files
        age_hours = int(temp_age_hours) if temp_age_hours else None
        cleaned_count = TempManager.clean_persistent_temps(max_age_hours=age_hours)
        
        if cleaned_count > 0:
            age_msg = f" (older than {age_hours}h)" if age_hours else ""
            print(f"  ✓ Cleaned {cleaned_count} temporary items{age_msg}")
        else:
            print("  ℹ No temporary items to clean")
            
    except ImportError:
        # Fallback to old method
        print("Fallback: Using legacy temp cleanup...")
        tmp_dir = Path(".tmp")
        if tmp_dir.exists():
            print(f"Removing temporary directory: {tmp_dir.absolute()}")
            if os.name == "nt":  # Windows
                ctx.run(f'rd /s /q "{tmp_dir}"', warn=True)
            else:  # Unix-like
                ctx.run(f"rm -rf '{tmp_dir}'", warn=True)
            print(f"  ✓ Removed {tmp_dir}")
        
        # Also clean .temp directory if it exists
        temp_dir = Path(".temp")
        if temp_dir.exists():
            print(f"Removing auto-cleanup temp directory: {temp_dir.absolute()}")
            if os.name == "nt":  # Windows
                ctx.run(f'rd /s /q "{temp_dir}"', warn=True)
            else:  # Unix-like
                ctx.run(f"rm -rf '{temp_dir}'", warn=True)
            print(f"  ✓ Removed {temp_dir}")
    
    # Clean other build artifacts with explicit reporting
    for pattern in dirs_to_clean:
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
    task_header("lint", "Run linting tools (black, flake8, mypy)", ctx)
    ensure_venv(ctx)
    
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
    task_header("format", "Format code with black", ctx)
    ensure_venv(ctx)
    python_path = get_venv_python()
    ctx.run(f"{python_path} -m black src/ tests/")


@task
def test(ctx, coverage=True, verbose=False, test_path="", keep_temps=False, sample_count=None):
    """Run tests.
    
    Args:
        coverage: Generate coverage reports (default: True, disabled for specific tests)
        verbose: Run with verbose output
        test_path: Specific test file, class, or method to run
                  (e.g. 'tests/test_file.py::TestClass::test_method')
        keep_temps: Keep temporary files after test completion for debugging
        sample_count: Number of sample images to generate in test_generate_sample_images (default: 10)
    
    Examples:
        inv test                                    # Run all tests with coverage
        inv test --test-path="tests/test_file.py"  # Run specific test file
        inv test -t "tests/test_file.py" --keep-temps  # Keep temp files for inspection
        inv test -t "tests/test_generate_images.py::TestImageGenerator::test_generate_sample_images" --sample-count=25
        inv test -t "tests/test_file.py::TestClass" --no-coverage  # Run test class without coverage
    """
    # Adjust task description based on whether running specific tests
    if test_path:
        task_header("test", f"Run specific test: {test_path}", ctx, 
                   coverage=coverage, verbose=verbose, test_path=test_path, keep_temps=keep_temps, sample_count=sample_count)
        # Disable coverage by default for specific tests (can be overridden)
        coverage = coverage if 'coverage' in ctx.config.run.env else False
    else:
        task_header("test", "Run tests with coverage", ctx, 
                   coverage=coverage, verbose=verbose, keep_temps=keep_temps, sample_count=sample_count)
    
    ensure_venv(ctx)
    
    # Set environment variables for test behavior
    env = {}
    if keep_temps:
        env['PYTEST_KEEP_TEMPS'] = '1'
        print("🔍 Keeping temporary files for debugging (use 'inv temp-clean' to clean up later)")
    if sample_count is not None:
        env['TEST_SAMPLE_COUNT'] = str(sample_count)
        print(f"📊 Using custom sample count: {sample_count}")
    
    python_path = get_venv_python()
    cmd = f"{python_path} -m pytest"
    
    # Add test path if specified
    if test_path:
        cmd += f" {test_path}"
    
    # Add coverage only if enabled (and usually not for specific tests)
    if coverage:
        cmd += " --cov=src --cov-report=html --cov-report=term"
    
    # Add verbose flag
    if verbose:
        cmd += " -v"
        
    # For specific tests, also add -s to see print output
    if test_path:
        cmd += " -s"
    
    ctx.run(cmd, pty=True, env=env)


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
    task_header("scripts", "List available scripts", ctx)
    scripts_dir = Path("scripts")
    
    if not scripts_dir.exists():
        print("No scripts directory found")
        return
    
    available_scripts = [f.stem for f in scripts_dir.glob("*.py") if f.name != "run.py"]
    if not available_scripts:
        print("No scripts found")
        return
    
    print("Available Scripts:")
    for script in sorted(available_scripts):
        script_path = scripts_dir / f"{script}.py"
        
        # Get a brief description from the file
        description = _get_script_description(script_path)
        
        if description:
            print(f"  {script:<15} {description}")
        else:
            print(f"  {script}")
    
    print(f"\nUsage:")
    print(f"  inv r -n <script> -a '<args>'")
    print(f"  inv run --script <script> --args '<args>'")


def _get_script_description(script_path):
    """Extract a brief description from a script file."""
    try:
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Look for common patterns for brief descriptions
        import re
        
        # Pattern 1: Look for "Brief:" or "Description:" lines in comments
        brief_match = re.search(r'#.*(?:Brief|Description):\s*(.+)', content, re.IGNORECASE)
        if brief_match:
            return brief_match.group(1).strip()
        
        # Pattern 2: Look for argparse description
        desc_match = re.search(r'description\s*=\s*[\'"]([^\'"\n]+)[\'"]', content)
        if desc_match:
            desc = desc_match.group(1).strip()
            # Keep it short - just the first sentence
            first_sentence = desc.split('.')[0]
            if len(first_sentence) < 80:
                return first_sentence
        
        # Pattern 3: Get first line of module docstring if it's short
        docstring_match = re.search(r'"""([^"]+)"""', content)
        if docstring_match:
            first_line = docstring_match.group(1).strip().split('\n')[0]
            if len(first_line) < 80 and not first_line.startswith('#!'):
                return first_line
        
        return None
    except:
        return None


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


@task
def temp_status(ctx):
    """Show status of temporary directories and files."""
    task_header("temp-status", "Show status of temporary directories and files", ctx)
    try:
        from common.temp import TempManager
        
        # List all persistent temporary items
        temp_items = TempManager.list_persistent_temps()
        
        if not temp_items:
            print("No persistent temporary items found.")
            return
        
        # Group by category/type
        categories = {}
        for item in temp_items:
            if item.is_dir():
                # Try to determine category from path
                parts = item.parts
                if len(parts) >= 2 and parts[-2] != ".tmp":
                    category = parts[-2]  # Category directory
                else:
                    category = "uncategorized"
            else:
                category = "files"
            
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        # Display by category
        total_size = 0
        for category, items in sorted(categories.items()):
            print(f"\n{category.upper()}:")
            for item in items:
                size = 0
                if item.is_file():
                    size = item.stat().st_size
                elif item.is_dir():
                    # Calculate directory size
                    for child in item.rglob('*'):
                        if child.is_file():
                            try:
                                size += child.stat().st_size
                            except (OSError, PermissionError):
                                pass
                
                total_size += size
                size_mb = size / (1024 * 1024) if size > 0 else 0
                
                # Show age
                import time
                age_hours = (time.time() - item.stat().st_mtime) / 3600
                
                print(f"  {item.name}: {size_mb:.1f} MB, {age_hours:.1f}h old")
        
        print(f"\nTotal: {len(temp_items)} items, {total_size / (1024 * 1024):.1f} MB")
        print("\nUse 'inv temp-clean' to clean up temporary files.")
        print("Use 'inv temp-clean --max-age-hours 24' to clean files older than 24 hours.")
        
    except ImportError:
        print("Centralized temp management not available.")
        print("Checking for legacy temporary directories...")
        
        # Check legacy paths
        legacy_paths = [Path(".tmp"), Path(".temp")]
        found_any = False
        
        for path in legacy_paths:
            if path.exists():
                print(f"\nFound legacy temp directory: {path}")
                items = list(path.rglob('*'))
                print(f"  Contains {len(items)} items")
                found_any = True
        
        if not found_any:
            print("No temporary directories found.")


@task
def temp_clean(ctx, max_age_hours=None, dry_run=False):
    """Clean temporary directories and files.
    
    Args:
        max_age_hours: Only clean items older than this many hours
        dry_run: Show what would be cleaned without actually cleaning
    """
    task_header("temp-clean", "Clean temporary directories and files", ctx,
                max_age_hours=max_age_hours, dry_run=dry_run)
    try:
        from common.temp import TempManager
        
        # List current items
        temp_items = TempManager.list_persistent_temps()
        
        if not temp_items:
            print("No temporary items to clean.")
            return
        
        print(f"Found {len(temp_items)} temporary items")
        
        if max_age_hours:
            print(f"Cleaning items older than {max_age_hours} hours...")
        else:
            print("Cleaning all temporary items...")
        
        if dry_run:
            # Just list what would be cleaned
            import time
            current_time = time.time()
            would_clean = []
            
            for item in temp_items:
                if max_age_hours:
                    age_hours = (current_time - item.stat().st_mtime) / 3600
                    if age_hours < float(max_age_hours):
                        continue
                would_clean.append(item)
            
            if would_clean:
                print(f"\nWould clean {len(would_clean)} items:")
                for item in would_clean:
                    print(f"  - {item}")
            else:
                print("\nNo items match the cleaning criteria.")
        else:
            # Actually clean
            age_hours = int(max_age_hours) if max_age_hours else None
            cleaned_count = TempManager.clean_persistent_temps(max_age_hours=age_hours)
            
            if cleaned_count > 0:
                age_msg = f" (older than {age_hours}h)" if age_hours else ""
                print(f"✓ Cleaned {cleaned_count} items{age_msg}")
            else:
                print("No items were cleaned.")
        
    except ImportError:
        print("Centralized temp management not available.")
        print("Use 'inv clean' for legacy temporary directory cleanup.")
        return 0