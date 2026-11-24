from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from yanga_core.domain.execution_context import UserRequest
from yanga_core.domain.spl_paths import SPLPaths

from .artifacts_locator import CMakeArtifactsLocator
from .cmake_backend import CMakeCommand, CMakeCustomCommand, CMakePath


@dataclass
class CoverageRelevantFile:
    """Used to register files relevant for the merged coverage report."""

    target: UserRequest
    json_report: CMakePath
    #: The `testing` framework whose tests wrote the tracefile
    framework: str


def create_coverage_tracefile_command(
    description: str,
    depends: Sequence[str | CMakePath] | None,
    object_library_targets: list[str],
    sources: list[Path],
    project_dir: Path,
    config_file: CMakePath,
    json_file: CMakePath,
    gcov_prefix_dir: CMakePath | None = None,
) -> CMakeCustomCommand:
    """Write the gcovr config of a test run and its JSON tracefile, which the collector merges."""
    gcov_prefix_arguments: list[str | CMakePath] = ["--gcov-prefix", gcov_prefix_dir] if gcov_prefix_dir else []
    return CMakeCustomCommand(
        description=description,
        outputs=[config_file, json_file],
        depends=depends,
        command_expand_lists=True,
        commands=[
            CMakeCommand(
                "yanga_cmd",
                [
                    "gcovr_config_component",
                    "--component-objects",
                    *[f"$<TARGET_OBJECTS:{target}>" for target in object_library_targets],
                    "--source-files",
                    *[CMakePath(source) for source in sources],
                    "--project-dir",
                    CMakePath(project_dir),
                    *gcov_prefix_arguments,
                    "--output-file",
                    config_file,
                ],
            ),
            CMakeCommand("gcovr", ["--config", config_file, "--json", "--output", json_file, "--json-pretty"]),
        ],
    )


class CoverageArtifactsLocator(CMakeArtifactsLocator):
    def __init__(self, output_dir: Path, spl_paths: SPLPaths) -> None:
        super().__init__(output_dir, spl_paths)

    @classmethod
    def from_cmake_artifacts_locator(cls, cmake_artifacts_locator: CMakeArtifactsLocator) -> "CoverageArtifactsLocator":
        return cls(cmake_artifacts_locator.cmake_build_dir.to_path(), cmake_artifacts_locator.spl_paths)

    def _get_component_coverage_reports_relative_dir(self, component_name: str) -> str:
        # (!) We need to keep the component coverage reports relative path to the `reports` dir identical for both the component and variant reports
        # E.g., reports/coverage/<component_name>
        # This is because we copy the component report into the variant report dir maintaining the relative structure.
        return f"coverage/{component_name}"

    def get_component_coverage_reports_dir(self, component_name: str) -> CMakePath:
        """Path inside the component reports dir where the coverage report is located."""
        return self.get_component_reports_dir(component_name).joinpath(self._get_component_coverage_reports_relative_dir(component_name))

    def get_component_variant_coverage_reports_dir(self, component_name: str) -> CMakePath:
        """Path inside the variant reports dir where the component coverage report shall be located."""
        return self.cmake_variant_reports_dir.joinpath(self._get_component_coverage_reports_relative_dir(component_name))

    def get_component_coverage_html_file(self, component_name: str) -> CMakePath:
        return self.get_component_coverage_reports_dir(component_name).joinpath("index.html")

    def get_variant_coverage_reports_dir(self) -> CMakePath:
        return self.cmake_variant_reports_dir.joinpath("coverage")

    def get_variant_coverage_html_file(self) -> CMakePath:
        return self.get_variant_coverage_reports_dir().joinpath("index.html")
