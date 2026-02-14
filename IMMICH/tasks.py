"""Project-specific invoke tasks for EXIF project."""

import sys
from pathlib import Path
from invoke import task
import subprocess

# Add COMMON directory to path and import common tasks
common_dir = Path(__file__).parent.parent / "COMMON"
sys.path.insert(0, str(common_dir))

# Import all common functionality from common_tasks module
from common_tasks import (
    get_venv_python, get_venv_executable, ensure_venv, task_header,
    setup, clean, lint, format, test, build, run, install,
    deps, shell, scripts, status, gtest, temp_status, temp_clean,
    log_archive
)  # This file inherits all tasks from COMMON/common_tasks.py
# You can add project-specific tasks below or override common tasks

@task
def sample_demo(ctx, count=5):
    """Run a demo of the sample script with test data."""
    task_header("sample-demo", "Run a demo of the sample script with test data", ctx, count=count)
    import os
    
    ensure_venv(ctx)
    
    # Create temporary test structure using centralized temp management
    try:
        from common.temp import get_debug_temp_dir
        temp_path = get_debug_temp_dir("demo")
    except ImportError:
        # Fallback if temp system not available
        from pathlib import Path
        import time
        temp_base = Path(".tmp")
        temp_base.mkdir(exist_ok=True)
        timestamp = int(time.time())
        temp_path = temp_base / f"demo_{timestamp}"
        temp_path.mkdir(exist_ok=True)
    
    try:
        source_dir = temp_path / "demo_photos"
        target_dir = temp_path / "sampled_photos"
        
        # Create test directory structure
        folders = [source_dir, source_dir / "folder1", source_dir / "folder2"]
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)
        
        # Create test image files
        test_images = [
            source_dir / "root_image1.jpg",
            source_dir / "root_image2.png", 
            source_dir / "folder1" / "photo1.jpg",
            source_dir / "folder1" / "photo2.tiff",
            source_dir / "folder2" / "image1.jpeg",
            source_dir / "folder2" / "image2.bmp"
        ]
        
        for img in test_images:
            img.touch()
            
        print(f"Created demo structure with {len(test_images)} test images")
        print(f"Temp directory: {temp_path}")
        print(f"Source: {source_dir}")
        print(f"Target: {target_dir}")
        print(f"Running sample script with {count} files...")
        
        # Run the sample script using the common run task
        args = f"--source {source_dir} --target {target_dir} --files {count} --debug"
        run(ctx, script="sample", args=args)
        
        # Show results
        print(f"\nResults in {target_dir}:")
        if target_dir.exists():
            for file in target_dir.rglob("*"):
                if file.is_file():
                    rel_path = file.relative_to(target_dir)
                    print(f"  {rel_path}")
        else:
            print("  No files copied")
            
    except Exception as e:
        print(f"Error during demo: {e}")
        print(f"Temporary files available for inspection in: {temp_path}")
        raise
    finally:
        print(f"Demo completed. Temporary files in: {temp_path}")
        print("Note: Temporary directory will persist for debugging")

# Shortcut alias for the run task (commonly used pattern)
@task(name="r")  
def r_shortcut(ctx, n=None, a=""):
    """Shortcut for run task - 'inv r -n script -a args'."""
    run(ctx, script=n, args=a)

# Example of how to override a common task:
# @task
# def custom_run(ctx, script=None, args="", env="dev"):
#     """Override the common run task with project-specific behavior."""
#     # Custom implementation here
#     pass

@task
def test(ctx, integration=False, unit=False, coverage=False, all=False):
    """Run tests. Use --integration for integration tests, --unit for unit tests, --all for all tests."""
    task_header("test", "Run tests with coverage" if coverage else "Run tests", ctx, integration=integration, unit=unit, all=all)
    ensure_venv(ctx)
    pytest_args = []
    if coverage:
        pytest_args.append("--cov")
    if all:
        pass  # No marker filter, run all tests
    elif integration:
        pytest_args.extend(["-m", "'integration'"])
    else:
        pytest_args.extend(["-m", "'not integration'"])
    ctx.run(f".venv/bin/pytest {' '.join(pytest_args)}", pty=True)