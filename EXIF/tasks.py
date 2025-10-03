"""Project-specific invoke tasks for EXIF project."""

import sys
from pathlib import Path
from invoke import task

# Add COMMON directory to path and import common tasks
common_dir = Path(__file__).parent.parent / "COMMON"
sys.path.insert(0, str(common_dir))

# Import all common functionality from common_tasks module
from common_tasks import (
    get_venv_python, get_venv_executable, ensure_venv,
    setup, clean, lint, format, test, build, run, install, 
    deps, shell, scripts, status
)

# This file inherits all tasks from COMMON/common_tasks.py
# You can add project-specific tasks below or override common tasks

@task
def sample_demo(ctx, count=5):
    """Run a demo of the sample script with test data."""
    import tempfile
    import os
    
    ensure_venv(ctx)
    
    # Create temporary test structure
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
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
        print(f"Source: {source_dir}")
        print(f"Target: {target_dir}")
        print(f"Running sample script with {count} files...")
        
        # Run the sample script
        python_path = get_venv_python()
        cmd = f"{python_path} scripts/run.py sample --source {source_dir} --target {target_dir} --files {count} --debug"
        ctx.run(cmd, pty=True)
        
        # Show results
        print(f"\nResults in {target_dir}:")
        if target_dir.exists():
            for file in target_dir.rglob("*"):
                if file.is_file():
                    rel_path = file.relative_to(target_dir)
                    print(f"  {rel_path}")
        else:
            print("  No files copied")

# Example of how to override a common task:
# @task
# def custom_run(ctx, script=None, args="", env="dev"):
#     """Override the common run task with project-specific behavior."""
#     # Custom implementation here
#     pass