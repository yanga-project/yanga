import os
import shutil
from pathlib import Path

from py_app_dev.core.exceptions import UserNotificationException
from py_app_dev.core.logging import logger


class ProjectBuilder:
    def __init__(self, project_dir: Path, input_dir: Path | None = None) -> None:
        self.project_dir = project_dir
        self.input_dir = input_dir if input_dir else Path(__file__).parent.joinpath("templates")

        self.dirs: list[Path] = []
        self.check_target_directory_flag = True

    def with_disable_target_directory_check(self) -> "ProjectBuilder":
        self.check_target_directory_flag = False
        return self

    def with_dir(self, dir: Path | str) -> "ProjectBuilder":
        self.dirs.append(self.resolve_file_path(dir))
        return self

    def resolve_file_paths(self, files: list[Path | str]) -> list[Path]:
        return [self.resolve_file_path(file) for file in files]

    def resolve_file_path(self, file: Path | str) -> Path:
        return self.input_dir.joinpath(file) if isinstance(file, str) else file

    @staticmethod
    def _check_target_directory(project_dir: Path) -> None:
        if project_dir.is_dir() and any(project_dir.iterdir()):
            raise UserNotificationException(f"Project directory '{project_dir}' is not empty. Use --force to override.")

    def build(self) -> None:
        if self.check_target_directory_flag:
            self._check_target_directory(self.project_dir)
        for dir in self.dirs:
            shutil.copytree(dir, self.project_dir, dirs_exist_ok=True)


class KickstartProject:
    def __init__(self, project_dir: Path, force: bool = False, with_sources: bool = True) -> None:
        self.logger = logger.bind()
        self.project_dir = project_dir
        self.force = force
        self.with_sources = with_sources

    def run(self) -> None:
        self.logger.info(f"Kickstart new project in '{Path(os.path.abspath(self.project_dir)).as_posix()}'")
        project_builder = ProjectBuilder(self.project_dir)
        if self.force:
            project_builder.with_disable_target_directory_check()
        project_builder.with_dir("common")
        if self.with_sources:
            project_builder.with_dir("mini")
        project_builder.build()
