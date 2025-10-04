"""
Centralized temporary file and directory management for the photo-scripts framework.

This module provides consistent patterns for creating, managing, and cleaning up
temporary directories and files across all projects.
"""

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional, Union, Generator
from contextlib import contextmanager


class TempManager:
    """Centralized temporary file and directory management."""

    # Standard temporary directory patterns
    PERSISTENT_BASE = ".tmp"  # For debugging/inspection (manual cleanup)
    AUTO_CLEANUP_BASE = ".temp"  # For automatic cleanup

    @classmethod
    def get_project_temp_base(cls) -> Path:
        """Get the base temporary directory for the current project.

        Returns:
            Path to the .tmp directory in current working directory
        """
        temp_base = Path(cls.PERSISTENT_BASE)
        temp_base.mkdir(exist_ok=True)
        return temp_base

    @classmethod
    def create_persistent_dir(
        cls, name_prefix: str = "temp", category: Optional[str] = None
    ) -> Path:
        """Create a persistent temporary directory for debugging/inspection.

        Directory will persist until manually cleaned (via 'inv clean' or manual removal).
        Use this for directories you might want to inspect after script completion.

        Args:
            name_prefix: Descriptive prefix for the directory
            category: Optional category for organizing temp dirs (e.g., 'test', 'demo', 'cache')

        Returns:
            Path to the created directory

        Example:
            temp_dir = TempManager.create_persistent_dir("sample_demo", "demo")
            # Creates: .tmp/demo/sample_demo_1696348800/
        """
        temp_base = cls.get_project_temp_base()

        # Add category subdirectory if specified
        if category:
            temp_base = temp_base / category
            temp_base.mkdir(exist_ok=True)

        # Create unique directory with timestamp
        timestamp = int(time.time())
        temp_dir = temp_base / f"{name_prefix}_{timestamp}"
        temp_dir.mkdir(exist_ok=True)

        return temp_dir

    @classmethod
    @contextmanager
    def auto_cleanup_dir(cls, name_prefix: str = "temp") -> Generator[Path, None, None]:
        """Create a temporary directory that automatically cleans up.

        Use this for temporary work that doesn't need inspection after completion.

        Args:
            name_prefix: Descriptive prefix for the directory

        Yields:
            Path to the temporary directory

        Example:
            with TempManager.auto_cleanup_dir("processing") as temp_dir:
                # Use temp_dir for work
                pass  # Directory automatically deleted here
        """
        with tempfile.TemporaryDirectory(prefix=f"{name_prefix}_") as temp_path:
            yield Path(temp_path)

    @classmethod
    def create_persistent_file(
        cls,
        name_prefix: str = "temp",
        suffix: str = ".tmp",
        category: Optional[str] = None,
    ) -> Path:
        """Create a persistent temporary file.

        Args:
            name_prefix: Descriptive prefix for the file
            suffix: File extension (include the dot)
            category: Optional category for organizing temp files

        Returns:
            Path to the created file

        Example:
            temp_file = TempManager.create_persistent_file("config", ".json", "cache")
            # Creates: .tmp/cache/config_1696348800.json
        """
        temp_dir = cls.create_persistent_dir(name_prefix, category)
        timestamp = int(time.time())
        temp_file = temp_dir / f"{name_prefix}_{timestamp}{suffix}"
        temp_file.touch()
        return temp_file

    @classmethod
    @contextmanager
    def auto_cleanup_file(
        cls, name_prefix: str = "temp", suffix: str = ".tmp"
    ) -> Generator[Path, None, None]:
        """Create a temporary file that automatically cleans up.

        Args:
            name_prefix: Descriptive prefix for the file
            suffix: File extension (include the dot)

        Yields:
            Path to the temporary file

        Example:
            with TempManager.auto_cleanup_file("data", ".json") as temp_file:
                # Use temp_file
                pass  # File automatically deleted here
        """
        import tempfile

        fd, temp_path = tempfile.mkstemp(prefix=f"{name_prefix}_", suffix=suffix)
        os.close(fd)  # Close the file descriptor
        try:
            yield Path(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @classmethod
    def clean_persistent_temps(cls, max_age_hours: Optional[int] = None) -> int:
        """Clean up persistent temporary directories and files.

        Args:
            max_age_hours: Only clean items older than this many hours.
                          If None, clean all persistent temps.

        Returns:
            Number of items cleaned up
        """
        cleaned_count = 0
        temp_base = Path(cls.PERSISTENT_BASE)

        if not temp_base.exists():
            return 0

        current_time = time.time()

        for item in temp_base.rglob("*"):
            # Skip the base directory itself
            if item == temp_base:
                continue

            try:
                # Check age if max_age_hours is specified
                if max_age_hours is not None:
                    item_age = current_time - item.stat().st_mtime
                    max_age_seconds = max_age_hours * 3600
                    if item_age < max_age_seconds:
                        continue

                if item.is_file():
                    item.unlink()
                    cleaned_count += 1
                elif item.is_dir() and not any(item.iterdir()):  # Empty directory
                    item.rmdir()
                    cleaned_count += 1

            except (OSError, PermissionError):
                # Skip items we can't clean
                continue

        # Try to remove empty category directories and base if empty
        try:
            for item in temp_base.rglob("*"):
                if item.is_dir() and not any(item.iterdir()):
                    item.rmdir()
            if temp_base.exists() and not any(temp_base.iterdir()):
                temp_base.rmdir()
        except (OSError, PermissionError):
            pass

        return cleaned_count

    @classmethod
    def list_persistent_temps(cls) -> list[Path]:
        """List all persistent temporary directories and files.

        Returns:
            List of paths to temporary items
        """
        temp_base = Path(cls.PERSISTENT_BASE)
        if not temp_base.exists():
            return []

        return [item for item in temp_base.rglob("*") if item != temp_base]


# Convenience functions for common use cases
def get_debug_temp_dir(name_prefix: str = "debug", category: str = "debug") -> Path:
    """Create a persistent temp directory for debugging/inspection."""
    return TempManager.create_persistent_dir(name_prefix, category)


def get_cache_temp_dir(name_prefix: str = "cache", category: str = "cache") -> Path:
    """Create a persistent temp directory for caching."""
    return TempManager.create_persistent_dir(name_prefix, category)


@contextmanager
def temp_working_dir(name_prefix: str = "work") -> Generator[Path, None, None]:
    """Create a temporary working directory with auto cleanup."""
    with TempManager.auto_cleanup_dir(name_prefix) as temp_dir:
        yield temp_dir


# Pytest fixture helper
@contextmanager
def pytest_temp_dirs(
    num_dirs: int = 2, names: Optional[list[str]] = None
) -> Generator[list[Path], None, None]:
    """Create multiple temporary directories for pytest tests.

    Creates directories under the project's .tmp/test/ structure for better organization
    and easier debugging of test artifacts.

    Args:
        num_dirs: Number of directories to create
        names: Optional list of directory names (default: ['source', 'target', ...])

    Yields:
        List of temporary directory paths

    Example:
        def test_something():
            with pytest_temp_dirs(2, ['source', 'target']) as (source, target):
                # Use source and target directories
                pass
    """
    if names is None:
        names = ["source", "target", "working", "output", "backup"][:num_dirs]

    # Create a test-specific temporary base directory under .tmp/test/
    test_base = TempManager.create_persistent_dir("pytest", "test")

    try:
        temp_dirs = []
        for i in range(num_dirs):
            name = names[i] if i < len(names) else f"temp_{i}"
            temp_dir = test_base / name
            temp_dir.mkdir(exist_ok=True)
            temp_dirs.append(temp_dir)

        yield temp_dirs

    finally:
        # Clean up the test directory after use (unless requested to keep)
        if os.environ.get('PYTEST_KEEP_TEMPS') != '1':
            try:
                shutil.rmtree(test_base, ignore_errors=True)
            except OSError:
                pass  # Don't fail tests due to cleanup issues
        else:
            print(f"🔍 Keeping test temp directory for debugging: {test_base}")
