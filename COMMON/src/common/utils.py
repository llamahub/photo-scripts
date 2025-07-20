"""Common utility functions."""

import os
import sys
from pathlib import Path
from typing import Optional, List, Union


def add_to_path(paths: Union[str, Path, List[Union[str, Path]]]) -> None:
    """Add paths to sys.path for module imports.

    Args:
        paths: Single path or list of paths to add
    """
    if isinstance(paths, (str, Path)):
        paths = [paths]

    for path in paths:
        path_str = str(Path(path).resolve())
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


def find_project_root(start_path: Optional[Path] = None) -> Path:
    """Find the project root directory.

    Args:
        start_path: Starting path for search

    Returns:
        Path to project root
    """
    if start_path is None:
        start_path = Path.cwd()

    current = Path(start_path).resolve()

    # Look for common project root indicators
    indicators = ["pyproject.toml", ".git", "requirements.txt"]

    while current != current.parent:
        for indicator in indicators:
            if (current / indicator).exists():
                return current
        current = current.parent

    return Path.cwd()


def setup_project_paths(project_name: str) -> None:
    """Setup paths for a project to access common libraries.

    Args:
        project_name: Name of the current project
    """
    project_root = find_project_root()

    # Add common library to path
    common_src = project_root / "common" / "src"
    if common_src.exists():
        add_to_path(common_src)

    # Add current project to path
    current_project_src = project_root / project_name / "src"
    if current_project_src.exists():
        add_to_path(current_project_src)

    # Add other projects if needed (optional)
    for project_dir in project_root.iterdir():
        if (
            project_dir.is_dir()
            and project_dir.name not in ["common", project_name, ".git", "__pycache__"]
            and not project_dir.name.startswith(".")
        ):
            other_project_src = project_dir / "src"
            if other_project_src.exists():
                add_to_path(other_project_src)


def get_environment() -> str:
    """Get the current environment from environment variables.

    Returns:
        Current environment (dev, test, prod)
    """
    return os.getenv("ENVIRONMENT", "dev")
