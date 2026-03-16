#!/usr/bin/env python3
"""Tests for new_project.py."""

import sys
from pathlib import Path

import pytest

# Add COMMON src and scripts to path for imports
common_root = Path(__file__).parent.parent
sys.path.insert(0, str(common_root / "src"))
sys.path.insert(0, str(common_root / "scripts"))

import new_project
from common.argument_parser import ScriptArgumentParser


class MockLogger:
    """Simple logger double used for script tests."""

    def __init__(self):
        self.entries = []

    def info(self, message):
        self.entries.append(("info", message))

    def debug(self, message):
        self.entries.append(("debug", message))

    def warning(self, message):
        self.entries.append(("warning", message))

    def error(self, message):
        self.entries.append(("error", message))

    def audit(self, message):
        self.entries.append(("audit", message))


class RecordingScaffolder:
    """Scaffolder test double that records calls."""

    calls = []
    constructor_calls = []

    def __init__(
        self,
        monorepo_root,
        common_root,
        logger,
        model_files,
        project_subdirectories,
        common_template_mappings,
        dry_run=False,
    ):
        self.monorepo_root = monorepo_root
        self.common_root = common_root
        self.logger = logger
        self.dry_run = dry_run
        self.model_files = tuple(model_files)
        self.project_subdirectories = tuple(project_subdirectories)
        self.common_template_mappings = tuple(common_template_mappings)

        self.__class__.constructor_calls.append(
            (
                self.model_files,
                self.project_subdirectories,
                self.common_template_mappings,
                self.dry_run,
            )
        )

    def list_model_projects(self):
        return ["EXIF", "IMMICH"]

    def scaffold(self, target_project, model_project):
        self.__class__.calls.append((target_project, model_project, self.dry_run))
        return Path("/tmp") / target_project


class FailingScaffolder(RecordingScaffolder):
    """Scaffolder test double that fails on scaffold()."""

    def scaffold(self, target_project, model_project):
        raise FileExistsError(f"Already exists: {target_project}")


def _patch_common_script_methods(monkeypatch, logger):
    def fake_setup_logging(self, resolved_args, script_name=None):
        return logger

    def fake_display_configuration(self, resolved_args, config_map=None):
        return None

    def fake_print_header(self):
        return None

    monkeypatch.setattr(ScriptArgumentParser, "setup_logging", fake_setup_logging)
    monkeypatch.setattr(ScriptArgumentParser, "display_configuration", fake_display_configuration)
    monkeypatch.setattr(ScriptArgumentParser, "print_header", fake_print_header)


def test_script_info_fields():
    """SCRIPT_INFO contains required metadata fields."""
    info = new_project.SCRIPT_INFO

    assert info["name"]
    assert info["description"]
    assert isinstance(info.get("examples"), list)
    assert len(info["examples"]) > 0


def test_script_argument_structure():
    """Arguments follow source/target naming conventions for this script."""
    args = new_project.SCRIPT_ARGUMENTS

    assert args["source"]["positional"] is True
    assert args["source"]["flag"] == "--source"
    assert args["target"]["flag"] == "--target"


def test_main_uses_cli_arguments_without_prompt(monkeypatch):
    """When source and target are provided, main() does not prompt."""
    logger = MockLogger()
    _patch_common_script_methods(monkeypatch, logger)

    RecordingScaffolder.calls = []
    RecordingScaffolder.constructor_calls = []
    monkeypatch.setattr(new_project, "ProjectScaffolder", RecordingScaffolder)
    monkeypatch.setattr(sys, "argv", ["new_project.py", "EXIF", "--target", "NEWPROJECT", "--dry-run"])

    prompt_called = {"value": False}

    def fake_input(_prompt):
        prompt_called["value"] = True
        return ""

    monkeypatch.setattr("builtins.input", fake_input)

    assert new_project.main() == 0
    assert prompt_called["value"] is False
    assert RecordingScaffolder.calls == [("NEWPROJECT", "EXIF", True)]
    assert RecordingScaffolder.constructor_calls == [
        (
            tuple(new_project.MODEL_FILES_TO_COPY),
            tuple(new_project.PROJECT_FOLDERS_TO_CREATE),
            tuple(new_project.COMMON_TEMPLATE_FILES_TO_COPY),
            True,
        )
    ]


def test_main_prompts_for_missing_required_values(monkeypatch):
    """When source/target are omitted, main() prompts and uses entered values."""
    logger = MockLogger()
    _patch_common_script_methods(monkeypatch, logger)

    RecordingScaffolder.calls = []
    RecordingScaffolder.constructor_calls = []
    monkeypatch.setattr(new_project, "ProjectScaffolder", RecordingScaffolder)
    monkeypatch.setattr(sys, "argv", ["new_project.py", "--dry-run"])

    entered_values = iter(["IMMICH", "FRESHPROJECT"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(entered_values))

    assert new_project.main() == 0
    assert RecordingScaffolder.calls == [("FRESHPROJECT", "IMMICH", True)]
    assert RecordingScaffolder.constructor_calls == [
        (
            tuple(new_project.MODEL_FILES_TO_COPY),
            tuple(new_project.PROJECT_FOLDERS_TO_CREATE),
            tuple(new_project.COMMON_TEMPLATE_FILES_TO_COPY),
            True,
        )
    ]


def test_main_returns_error_when_scaffolding_fails(monkeypatch):
    """Main returns non-zero when business logic raises a scaffold error."""
    logger = MockLogger()
    _patch_common_script_methods(monkeypatch, logger)

    monkeypatch.setattr(new_project, "ProjectScaffolder", FailingScaffolder)
    monkeypatch.setattr(sys, "argv", ["new_project.py", "EXIF", "--target", "NEWPROJECT"])

    assert new_project.main() == 1
