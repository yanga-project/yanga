from pathlib import Path

from py_app_dev.core.exceptions import UserNotificationException
from py_app_dev.core.find import find_elements_of_type
from py_app_dev.core.logging import logger
from py_app_dev.core.pipeline import PipelineLoader
from yanga_core.domain.config import PlatformConfig
from yanga_core.domain.config_utils import collect_configs_by_id
from yanga_core.domain.execution_context import ExecutionContext

from yanga.cmake.artifacts_locator import CMakeArtifactsLocator

from .clean import ComponentCleanCMakeGenerator
from .cmake_backend import (
    CMakeAddExecutable,
    CMakeAddLibrary,
    CMakeComment,
    CMakeCustomCommand,
    CMakeCustomTarget,
    CMakeElement,
    CMakeInclude,
    CMakeMinimumVersion,
    CMakePath,
    CMakeProject,
    CMakeVariable,
)
from .generator import CMakeFile, CMakeGenerator, GeneratedFile, GeneratedFileIf
from .targets import Target, TargetsData, TargetType
from .variant_config import ConfigCMakeGenerator


def get_toolchain_config_file(platform: PlatformConfig) -> str | None:
    """Return the raw toolchain file path from platform configs (id='toolchain'), or None."""
    toolchain_config = next((cfg for cfg in platform.configs if cfg.id == "toolchain"), None)
    if toolchain_config and toolchain_config.file:
        return str(toolchain_config.file)
    return None


class CMakeGeneratorReference:
    def __init__(self, group_name: str | None, _class: type[CMakeGenerator]) -> None:
        self.group_name = group_name
        self._class = _class

    @property
    def name(self) -> str:
        return self._class.__name__


class CMakeBuildSystemGenerator:
    def __init__(
        self,
        execution_context: ExecutionContext,
        output_dir: Path,
    ):
        self.logger = logger.bind()
        self.execution_context = execution_context
        self.output_dir = output_dir
        # The directory where the CMakeLists.txt file is located
        self.cmake_current_list_dir = CMakePath(self.output_dir, "CMAKE_CURRENT_LIST_DIR")
        self.artifacts_locator = CMakeArtifactsLocator(output_dir, execution_context.spl_paths)

    @property
    def variant_cmake_file(self) -> CMakePath:
        return self.cmake_current_list_dir.joinpath("variant.cmake")

    @property
    def config_cmake_file(self) -> CMakePath:
        return self.cmake_current_list_dir.joinpath("config.cmake")

    @property
    def variant_name(self) -> str:
        return self.execution_context.variant_name or "MyProject"

    def generate(self) -> list[GeneratedFileIf]:
        files: list[GeneratedFileIf] = []
        cmake_files: list[CMakeFile] = []
        cmake_files.append(self.create_config_cmake_file())
        cmake_files.append(self.create_variant_cmake_file())
        files.extend(cmake_files)
        files.append(self.create_target_dependencies_file(cmake_files))
        return files

    def create_cmake_lists(self) -> CMakeFile:
        cmake_file = CMakeFile(self.output_dir.joinpath("CMakeLists.txt"))
        cmake_file.append(CMakeMinimumVersion("4.1"))
        platform = self.execution_context.platform
        if platform:
            toolchain_file = get_toolchain_config_file(platform)
            if toolchain_file:
                cmake_file.append(
                    CMakeVariable(
                        "CMAKE_TOOLCHAIN_FILE",
                        CMakePath(self.execution_context.spl_paths.locate_artifact(toolchain_file, [platform.file])).to_string(),
                    )
                )
        cmake_file.append(CMakeProject(self.variant_name))
        return cmake_file

    def create_variant_cmake_file(self) -> CMakeFile:
        cmake_file = CMakeFile(self.variant_cmake_file.to_path())
        cmake_build_dir_var = self.artifacts_locator.cmake_build_dir.to_cmake_element()
        if cmake_build_dir_var:
            cmake_file.append(cmake_build_dir_var)
        platform = self.execution_context.platform
        if platform:
            try:
                steps_references = PipelineLoader[CMakeGenerator](platform.generators, self.execution_context.project_root_dir).load_steps()
                for step_reference in steps_references:
                    step = step_reference._class(self.execution_context, self.output_dir, step_reference.config)
                    cmake_file.extend(step.generate())
            except FileNotFoundError as e:
                raise UserNotificationException(e) from e
            except TypeError as e:
                raise UserNotificationException(f"{e}. Please check {platform.file} for {step}.") from e
        cmake_file.extend(ComponentCleanCMakeGenerator(self.execution_context, self.output_dir, existing_elements=cmake_file.content).generate())
        cmake_file.extend(self.create_cmake_config_includes())
        return cmake_file

    def create_cmake_config_includes(self) -> list[CMakeElement]:
        """User CMake files (configs with id 'cmake'), included last so they see every generated target."""
        includes: list[CMakeElement] = []
        for config in collect_configs_by_id(self.execution_context, "cmake"):
            if not config.file:
                raise UserNotificationException("A 'cmake' config must reference a file; inline 'content' is not a CMake file.")
            located = self.execution_context.spl_paths.locate_artifact(str(config.file), [config.location.file if config.location else None])
            includes.append(CMakeInclude(CMakePath(located).to_string()))
        return includes

    def create_config_cmake_file(self) -> CMakeFile:
        cmake_file = CMakeFile(self.config_cmake_file.to_path())
        config_generator = ConfigCMakeGenerator(self.execution_context, self.output_dir)
        cmake_file.extend(config_generator.generate())
        cmake_file.append(CMakeComment("Enable generation of compile_commands.json for IDEs and code analysis tools"))
        cmake_file.append(CMakeVariable("CMAKE_EXPORT_COMPILE_COMMANDS", "ON", True, "BOOL", "", True))
        return cmake_file

    def create_target_dependencies_file(self, cmake_files: list[CMakeFile]) -> GeneratedFileIf:
        """
        Create a json file that contains the CMake target dependencies tree for the current variant and each component.

        Parse all cmake files, search for the custom targets and their dependencies, and create a json file.
        This file is required to create a graph of the targets and their dependencies.
        """
        targets: list[Target] = []

        # Extract all elements from cmake files
        all_elements = []
        for cmake_file in cmake_files:
            all_elements.extend(cmake_file.content)

        # Find all custom commands
        custom_commands = find_elements_of_type(all_elements, CMakeCustomCommand)
        for custom_command in custom_commands:
            dependencies = []
            outputs = []
            commands = []

            # Extract dependencies
            if custom_command.depends:
                dependencies.extend([str(dep) for dep in custom_command.depends])

            # Extract outputs
            if custom_command.outputs:
                outputs.extend([str(output) for output in custom_command.outputs])

            # Extract commands
            if custom_command.commands:
                commands.extend([str(command) for command in custom_command.commands])

            targets.append(
                Target(
                    name=custom_command.id,
                    description=custom_command.description,
                    depends=dependencies,
                    outputs=outputs,
                    commands=commands,
                    target_type=TargetType.CUSTOM_COMMAND,
                )
            )

        # Find all custom targets
        custom_targets = find_elements_of_type(all_elements, CMakeCustomTarget)
        for custom_target in custom_targets:
            dependencies = []
            outputs = []
            commands = []

            # Extract dependencies
            if custom_target.depends:
                dependencies.extend([str(dep) for dep in custom_target.depends])

            # Extract outputs/byproducts
            if custom_target.byproducts:
                outputs.extend([str(byproduct) for byproduct in custom_target.byproducts])

            # Extract commands
            if custom_target.commands:
                commands.extend([str(command) for command in custom_target.commands])

            targets.append(
                Target(
                    name=custom_target.name,
                    description=custom_target.description,
                    depends=dependencies,
                    outputs=outputs,
                    commands=commands,
                    target_type=TargetType.CUSTOM_TARGET,
                )
            )

        # Find all executables
        executables = find_elements_of_type(all_elements, CMakeAddExecutable)
        for executable in executables:
            dependencies = []

            # Add library dependencies
            if executable.libraries:
                dependencies.extend(executable.libraries)

            # Add any additional dependencies
            if executable.sources:
                dependencies.extend([str(source) for source in executable.sources])

            targets.append(
                Target(
                    name=executable.name,
                    description=f"Executable target: {executable.name}",
                    depends=dependencies,
                    outputs=[executable.name],  # The executable itself is the output
                    target_type=TargetType.EXECUTABLE,
                )
            )

        # Find all object libraries
        object_libraries = find_elements_of_type(all_elements, CMakeAddLibrary)
        for obj_lib in object_libraries:
            targets.append(
                Target(
                    name=obj_lib.target_name,
                    description=f"Object library: {obj_lib.name}",
                    # Object libraries depend on their source files
                    depends=[str(file) for file in obj_lib.files],
                    outputs=[obj_lib.target_name],
                    target_type=TargetType.OBJECT_LIBRARY,
                )
            )

        targets_data = TargetsData(targets=targets)
        return GeneratedFile(
            self.cmake_current_list_dir.joinpath("targets_data.json").to_path(),
            targets_data.to_json_string(),
        )
