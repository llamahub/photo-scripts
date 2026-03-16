#!/usr/bin/env python3
"""Unit tests for the ProjectScaffolder business logic."""

import sys
from pathlib import Path

import pytest

# Add COMMON src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from common.project_scaffolder import ProjectScaffolder


MODEL_FILES_TO_COPY = ("pyproject.toml", "tasks.py", "setenv", "run")
PROJECT_FOLDERS_TO_CREATE = ("scripts", "src", "tests")
COMMON_TEMPLATE_FILES_TO_COPY = (
    ("scripts/example_script.py", "scripts/example_script.py"),
    ("tests/test_example_script.py", "tests/test_example_script.py"),
)


class MockLogger:
    """Simple logger double that supports audit logging."""

    def __init__(self):
        self.messages = []

    def info(self, message):
        self.messages.append(("info", message))

    def debug(self, message):
        self.messages.append(("debug", message))

    def warning(self, message):
        self.messages.append(("warning", message))

    def error(self, message):
        self.messages.append(("error", message))

    def audit(self, message):
        self.messages.append(("audit", message))


def _create_common_templates(common_root: Path) -> None:
    scripts_dir = common_root / "scripts"
    tests_dir = common_root / "tests"
    scripts_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)

    (scripts_dir / "example_script.py").write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import sys",
                "import os",
                "sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (tests_dir / "test_example_script.py").write_text(
        "\n".join(
            [
                "import sys",
                "from pathlib import Path",
                "",
                "# Add COMMON src and scripts to path for imports",
                "common_root = Path(__file__).parent.parent",
                "sys.path.insert(0, str(common_root / \"src\"))",
                "sys.path.insert(0, str(common_root / \"scripts\"))",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _create_model_project(project_root: Path, project_name: str = "EXIF") -> Path:
    model_project = project_root / project_name
    model_project.mkdir(parents=True)

    (model_project / "pyproject.toml").write_text("name = 'model'\n", encoding="utf-8")
    (model_project / "tasks.py").write_text("# tasks\n", encoding="utf-8")
    (model_project / "setenv").write_text("source ../COMMON/setenv\n", encoding="utf-8")
    (model_project / "run").write_text("source ../COMMON/run\n", encoding="utf-8")

    return model_project


def _build_scaffolder(scaffold_fixture, dry_run: bool = False) -> ProjectScaffolder:
    return ProjectScaffolder(
        monorepo_root=scaffold_fixture["monorepo_root"],
        common_root=scaffold_fixture["common_root"],
        logger=scaffold_fixture["logger"],
        model_files=MODEL_FILES_TO_COPY,
        project_subdirectories=PROJECT_FOLDERS_TO_CREATE,
        common_template_mappings=COMMON_TEMPLATE_FILES_TO_COPY,
        dry_run=dry_run,
    )


@pytest.fixture
def scaffold_fixture(tmp_path: Path):
    monorepo_root = tmp_path
    common_root = monorepo_root / "COMMON"
    common_root.mkdir()

    _create_common_templates(common_root)
    _create_model_project(monorepo_root, "EXIF")

    logger = MockLogger()

    return {
        "monorepo_root": monorepo_root,
        "common_root": common_root,
        "logger": logger,
    }


def test_list_model_projects_only_returns_valid_projects(scaffold_fixture):
    """Projects are discoverable only when required scaffold files exist."""
    monorepo_root = scaffold_fixture["monorepo_root"]
    _create_model_project(monorepo_root, "IMMICH")

    invalid_project = monorepo_root / "BROKEN"
    invalid_project.mkdir()
    (invalid_project / "pyproject.toml").write_text("name = 'broken'\n", encoding="utf-8")

    scaffolder = _build_scaffolder(scaffold_fixture)

    assert scaffolder.list_model_projects() == ["EXIF", "IMMICH"]


def test_scaffold_creates_new_project_and_copies_required_files(scaffold_fixture):
    """A new project scaffold includes model files and adjusted template imports."""
    scaffolder = _build_scaffolder(scaffold_fixture)

    target_path = scaffolder.scaffold(target_project="NEWPROJECT", model_project="EXIF")

    assert target_path.exists()
    assert (target_path / "scripts").exists()
    assert (target_path / "src").exists()
    assert (target_path / "tests").exists()

    assert (target_path / "pyproject.toml").exists()
    assert (target_path / "tasks.py").exists()
    assert (target_path / "setenv").exists()
    assert (target_path / "run").exists()
    assert (target_path / "scripts" / "example_script.py").exists()
    assert (target_path / "tests" / "test_example_script.py").exists()

    copied_script = (target_path / "scripts" / "example_script.py").read_text(
        encoding="utf-8"
    )
    assert "..', '..', 'COMMON', 'src'" in copied_script

    copied_test = (target_path / "tests" / "test_example_script.py").read_text(
        encoding="utf-8"
    )
    assert "repo_root / \"COMMON\" / \"src\"" in copied_test


def test_scaffold_dry_run_does_not_create_files(scaffold_fixture):
    """Dry run reports work without creating directories or files."""
    scaffolder = _build_scaffolder(scaffold_fixture, dry_run=True)

    target_path = scaffolder.scaffold(target_project="NEWPROJECT", model_project="EXIF")
    assert target_path == scaffold_fixture["monorepo_root"] / "NEWPROJECT"
    assert not target_path.exists()


def test_scaffold_fails_when_target_exists(scaffold_fixture):
    """Scaffolding fails clearly when target project already exists."""
    target_path = scaffold_fixture["monorepo_root"] / "NEWPROJECT"
    target_path.mkdir()

    scaffolder = _build_scaffolder(scaffold_fixture)

    with pytest.raises(FileExistsError):
        scaffolder.scaffold(target_project="NEWPROJECT", model_project="EXIF")


def test_scaffold_fails_when_model_project_missing_required_files(scaffold_fixture):
    """Scaffolding fails clearly when the selected model project is incomplete."""
    model_project = scaffold_fixture["monorepo_root"] / "EXIF"
    (model_project / "tasks.py").unlink()

    scaffolder = _build_scaffolder(scaffold_fixture)

    with pytest.raises(FileNotFoundError):
        scaffolder.scaffold(target_project="NEWPROJECT", model_project="EXIF")
