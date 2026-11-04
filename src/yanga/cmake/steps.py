from pathlib import Path
from typing import Any

from py_app_dev.core.logging import logger
from pypeline.domain.pipeline import PipelineStep
from yanga_core.domain.execution_context import ExecutionContext

from yanga.cmake.builder import CMakeBuildSystemGenerator, get_toolchain_config_file
from yanga.cmake.cmake_backend import CMakePath
from yanga.cmake.runner import CMakeRunner


class GenerateBuildSystemFiles(PipelineStep[ExecutionContext]):
    """
    Always re-runs.

    pypeline's runnable framework hashes input/output *files* — it cannot detect changes
    in this step's *generator code*. After a yanga upgrade, an unchanged yaml + an unchanged
    on-disk ``variant.cmake`` would be reported as MATCH, so a stale ``variant.cmake`` (written
    by an older yanga) survives the upgrade and cmake reconfigures from it. Symptom: targets
    added by the new yanga (e.g. ``<comp>_clean``) are missing → ``ninja: unknown target``.
    Always-running the step is sub-second pure-Python work and matches ``ExecuteBuild``'s
    "always run; build system handles its own deps" pattern.
    """

    def __init__(self, execution_context: ExecutionContext, group_name: str | None = None, config: dict[str, Any] | None = None) -> None:
        super().__init__(execution_context, group_name, config)
        self.logger = logger.bind()
        self.generated_files: list[Path] = []

    @property
    def output_dir(self) -> Path:
        return self.execution_context.spl_paths.variant_build_dir

    def get_name(self) -> str:
        return self.__class__.__name__

    def run(self) -> int:
        self.logger.info(f"Run {self.__class__.__name__} stage. Output dir: {self.output_dir}")
        generated_files = CMakeBuildSystemGenerator(self.execution_context, self.output_dir).generate()
        for file in generated_files:
            file.to_file()
        self.generated_files = [file.path for file in generated_files]
        return 0

    def get_inputs(self) -> list[Path]:
        return []

    def get_outputs(self) -> list[Path]:
        return []

    def update_execution_context(self) -> None:
        pass


class ExecuteBuild(PipelineStep[ExecutionContext]):
    """The step is always executed. The dependencies are handled by the build system itself."""

    def __init__(self, execution_context: ExecutionContext, group_name: str | None, config: dict[str, Any] | None = None) -> None:
        super().__init__(execution_context, group_name, config)
        self.logger = logger.bind()

    @property
    def output_dir(self) -> Path:
        return self.execution_context.spl_paths.variant_build_dir

    def get_name(self) -> str:
        return self.__class__.__name__

    def run(self) -> int:
        self.logger.debug(f"Run {self.get_name()} stage. Output dir: {self.output_dir}")
        cmake_runner = CMakeRunner(self.execution_context.project_root_dir, self.output_dir)
        toolchain_file = None
        platform = self.execution_context.platform
        platform_name = platform.name if platform else None
        if platform:
            raw = get_toolchain_config_file(platform)
            if raw:
                toolchain_file = CMakePath(self.execution_context.spl_paths.locate_artifact(raw, [platform.file])).to_string()
        self._run(cmake_runner.get_configure_command(toolchain_file, self.execution_context.variant_name, platform_name, self.execution_context.user_request.build_type))
        self._run(cmake_runner.get_build_command(self.execution_context.user_request.target_name))
        return 0

    def _run(self, cmd: list[str | Path]) -> None:
        self.execution_context.create_process_executor(cmd).execute()

    def get_inputs(self) -> list[Path]:
        return []

    def get_outputs(self) -> list[Path]:
        return []

    def update_execution_context(self) -> None:
        pass
