"""Business logic for creating a new project scaffold in the monorepo."""

from pathlib import Path
from typing import List, Sequence, Tuple
import shutil


class ProjectScaffolderError(RuntimeError):
    """Raised when scaffold file transformations cannot be completed safely."""


class ProjectScaffolder:
    """Create a new project folder from COMMON templates and a model project."""

    def __init__(
        self,
        monorepo_root: Path,
        common_root: Path,
        logger,
        model_files: Sequence[str],
        project_subdirectories: Sequence[str],
        common_template_mappings: Sequence[Tuple[str, str]],
        dry_run: bool = False,
    ):
        self.monorepo_root = Path(monorepo_root).resolve()
        self.common_root = Path(common_root).resolve()
        self.logger = logger
        self.model_files = tuple(model_files)
        self.project_subdirectories = tuple(project_subdirectories)
        self.common_template_mappings = tuple(common_template_mappings)
        self.dry_run = dry_run

        if not self.model_files:
            raise ValueError("model_files is required")

        if not self.project_subdirectories:
            raise ValueError("project_subdirectories is required")

        if not self.common_template_mappings:
            raise ValueError("common_template_mappings is required")

    def list_model_projects(self) -> List[str]:
        """List projects that can be used as a model for new project scaffolds."""
        projects: List[str] = []

        if not self.monorepo_root.exists():
            return projects

        for candidate in sorted(self.monorepo_root.iterdir(), key=lambda item: item.name.lower()):
            if not candidate.is_dir() or candidate.name.startswith("."):
                continue

            if candidate.name == self.common_root.name:
                continue

            if self._is_valid_model_project(candidate):
                projects.append(candidate.name)

        return projects

    def scaffold(self, target_project: str, model_project: str) -> Path:
        """Create a new project scaffold from a model project and COMMON templates."""
        target_name = self._validate_project_name(target_project, "target project")
        model_name = self._validate_project_name(model_project, "model project")

        model_path = self.monorepo_root / model_name
        target_path = self.monorepo_root / target_name

        if not model_path.exists() or not model_path.is_dir():
            raise FileNotFoundError(f"Model project does not exist: {model_path}")

        self._validate_model_files(model_path)

        if target_path.exists():
            raise FileExistsError(f"Target project already exists: {target_path}")

        self.logger.info(f"Creating project scaffold: {target_name}")
        self.logger.info(f"Model project: {model_name}")

        self._create_project_directories(target_path)
        self._copy_model_files(model_path, target_path)
        self._copy_common_templates(target_path)

        if self.dry_run:
            self.logger.info(f"Dry run complete. No files were created for {target_path}")
        else:
            self.logger.info(f"Project scaffold created successfully: {target_path}")

        return target_path

    def _is_valid_model_project(self, project_path: Path) -> bool:
        return all((project_path / filename).exists() for filename in self.model_files)

    def _validate_model_files(self, model_path: Path) -> None:
        missing = [filename for filename in self.model_files if not (model_path / filename).exists()]
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise FileNotFoundError(
                f"Model project is missing required files: {missing_list} (project: {model_path})"
            )

    def _validate_project_name(self, raw_name: str, label: str) -> str:
        name = (raw_name or "").strip()
        if not name:
            raise ValueError(f"{label.capitalize()} is required")

        path_candidate = Path(name)
        if path_candidate.name != name:
            raise ValueError(f"{label.capitalize()} must be a single folder name: {name}")

        if name in {".", ".."}:
            raise ValueError(f"{label.capitalize()} must be a valid folder name: {name}")

        return name

    def _create_project_directories(self, target_path: Path) -> None:
        self._create_directory(target_path)
        for subdirectory in self.project_subdirectories:
            self._create_directory(target_path / subdirectory)

    def _copy_model_files(self, model_path: Path, target_path: Path) -> None:
        for filename in self.model_files:
            self._copy_file(model_path / filename, target_path / filename)

    def _copy_common_templates(self, target_path: Path) -> None:
        copied_targets = {}

        for source_relative, target_relative in self.common_template_mappings:
            source_path = self.common_root / source_relative
            target_file = target_path / target_relative
            self._copy_file(source_path, target_file)
            copied_targets[Path(target_relative).as_posix()] = target_file

        if not self.dry_run:
            example_script_key = Path("scripts/example_script.py").as_posix()
            example_test_key = Path("tests/test_example_script.py").as_posix()

            if example_script_key in copied_targets:
                self._adjust_example_script_for_project(copied_targets[example_script_key])

            if example_test_key in copied_targets:
                self._adjust_example_test_for_project(copied_targets[example_test_key])

    def _create_directory(self, directory_path: Path) -> None:
        if self.dry_run:
            self.logger.info(f"DRY RUN: Would create directory: {directory_path}")
            return

        directory_path.mkdir(parents=True, exist_ok=False)
        self._audit(f"CREATE_DIR success path={directory_path}")

    def _copy_file(self, source_path: Path, destination_path: Path) -> None:
        if not source_path.exists():
            self._audit(f"COPY_FILE failed source_missing={source_path} destination={destination_path}")
            raise FileNotFoundError(f"Required source file not found: {source_path}")

        if self.dry_run:
            self.logger.info(f"DRY RUN: Would copy {source_path} -> {destination_path}")
            self._audit(f"COPY_FILE dry_run source={source_path} destination={destination_path}")
            return

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
        self._audit(f"COPY_FILE success source={source_path} destination={destination_path}")

    def _adjust_example_script_for_project(self, script_path: Path) -> None:
        content = script_path.read_text(encoding="utf-8")
        old_text = "sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))"
        new_text = (
            "sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'COMMON', 'src'))"
        )

        if old_text not in content:
            raise ProjectScaffolderError(
                f"Could not find expected COMMON import pattern in {script_path}"
            )

        updated = content.replace(old_text, new_text, 1)
        script_path.write_text(updated, encoding="utf-8")
        self._audit(f"UPDATE_FILE success path={script_path} change=common_import_path")

    def _adjust_example_test_for_project(self, test_path: Path) -> None:
        content = test_path.read_text(encoding="utf-8")
        old_block = (
            "# Add COMMON src and scripts to path for imports\n"
            "common_root = Path(__file__).parent.parent\n"
            "sys.path.insert(0, str(common_root / \"src\"))\n"
            "sys.path.insert(0, str(common_root / \"scripts\"))"
        )
        new_block = (
            "# Add COMMON src and project scripts to path for imports\n"
            "project_root = Path(__file__).parent.parent\n"
            "repo_root = project_root.parent\n"
            "sys.path.insert(0, str(repo_root / \"COMMON\" / \"src\"))\n"
            "sys.path.insert(0, str(project_root / \"scripts\"))"
        )

        if old_block not in content:
            raise ProjectScaffolderError(
                f"Could not find expected import block in {test_path}"
            )

        updated = content.replace(old_block, new_block, 1)
        test_path.write_text(updated, encoding="utf-8")
        self._audit(f"UPDATE_FILE success path={test_path} change=test_import_paths")

    def _audit(self, message: str) -> None:
        if hasattr(self.logger, "audit"):
            self.logger.audit(message)
        else:
            self.logger.debug(message)
