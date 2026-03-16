#!/usr/bin/env python3
"""
================================================================================
=== [New Project Script] - Create a new monorepo project scaffold
================================================================================

Creates a new project folder in the monorepo using:
- Core project files from a model project (pyproject.toml, tasks.py, setenv, run)
- COMMON templates (scripts/example_script.py and tests/test_example_script.py)
- Standard project folders (scripts, src, tests)

If source/target values are not provided on the CLI, the script prompts for them.
"""

import sys
import os
from pathlib import Path

# Add src to path for COMMON modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from common.argument_parser import (
    ScriptArgumentParser,
    create_standard_arguments,
    merge_arguments,
)
from common.project_scaffolder import ProjectScaffolder


SCRIPT_INFO = {
    "name": "New Project Script",
    "description": "Create a new monorepo project scaffold from an existing project",
    "examples": [
        "EXIF --target NEW_PROJECT",
        "--source IMMICH --target NEW_PROJECT",
        "--dry-run",
    ],
}


SCRIPT_ARGUMENTS = {
    "source": {
        "flag": "--source",
        "positional": True,
        "help": "Source/model project to copy base files from (e.g. EXIF)",
    },
    "target": {
        "flag": "--target",
        "help": "Target project folder name to create",
    },
}


ARGUMENTS = merge_arguments(create_standard_arguments(), SCRIPT_ARGUMENTS)


MODEL_FILES_TO_COPY = ("pyproject.toml", "tasks.py", "setenv", "run")
PROJECT_FOLDERS_TO_CREATE = ("scripts", "src", "tests")
COMMON_TEMPLATE_FILES_TO_COPY = (
    ("scripts/example_script.py", "scripts/example_script.py"),
    ("tests/test_example_script.py", "tests/test_example_script.py"),
)


def _prompt_required_value(label: str, logger) -> str:
    logger.info(label)
    try:
        value = input("→ ").strip()
    except EOFError:
        value = ""

    if not value:
        raise ValueError(f"{label} cannot be empty")

    return value


def main() -> int:
    """Main entry point with standardized argument parsing and logging."""
    parser = ScriptArgumentParser(SCRIPT_INFO, ARGUMENTS)
    parser.print_header()

    args = parser.parse_args()
    resolved_args = vars(args).copy()

    logger = parser.setup_logging(resolved_args, "new_project")

    common_root = Path(__file__).resolve().parent.parent
    monorepo_root = common_root.parent

    scaffolder = ProjectScaffolder(
        monorepo_root=monorepo_root,
        common_root=common_root,
        logger=logger,
        model_files=MODEL_FILES_TO_COPY,
        project_subdirectories=PROJECT_FOLDERS_TO_CREATE,
        common_template_mappings=COMMON_TEMPLATE_FILES_TO_COPY,
        dry_run=resolved_args.get("dry_run", False),
    )

    available_models = scaffolder.list_model_projects()
    if available_models:
        logger.info(f"Available model projects: {', '.join(available_models)}")

    source_project = getattr(args, "source_file", None) or getattr(args, "source", None)
    target_project = getattr(args, "target", None)

    if not source_project:
        source_project = _prompt_required_value("Enter source/model project name:", logger)

    try:
        scaffolder.validate_model_project(source_project)
    except Exception as exc:
        logger.error(f"Invalid model project selection: {exc}")
        return 1

    if not target_project:
        target_project = _prompt_required_value("Enter target/new project folder name:", logger)

    resolved_args["source_project"] = source_project
    resolved_args["target_project"] = target_project

    config_map = {
        "source_project": "Source project",
        "target_project": "Target project",
    }
    parser.display_configuration(resolved_args, config_map)

    try:
        target_path = scaffolder.scaffold(
            target_project=target_project,
            model_project=source_project,
        )

        if resolved_args.get("dry_run"):
            logger.info(f"Dry run complete for target project: {target_path}")
        else:
            logger.info(f"New project created successfully: {target_path}")

        return 0

    except Exception as exc:
        logger.error(f"Failed to create project scaffold: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
