from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

from mashumaro import DataClassDictMixin
from py_app_dev.core.config import merge_configs
from py_app_dev.core.exceptions import UserNotificationException
from pypeline.domain.external_project import ExternalProject
from yanga_core.domain.artifact import Artifact, collect_directories, filter_artifacts, for_consumer, with_label
from yanga_core.domain.component_resolver import resolve_include_directories
from yanga_core.domain.components import Component
from yanga_core.domain.config import MockingConfig
from yanga_core.domain.execution_context import ExecutionContext, UserRequest, UserRequestScope, UserRequestTarget
from yanga_core.domain.reports import ReportRelevantFiles, ReportRelevantFileType, ReportRelevantHtmlContent

from yanga.cmake.artifacts_locator import BuildArtifact, CMakeArtifactsLocator
from yanga.cmake.coverage import CoverageArtifactsLocator, CoverageRelevantFile

from .cmake_backend import (
    CMakeAddExecutable,
    CMakeAddLibrary,
    CMakeAddSubdirectory,
    CMakeAddTargetCleanFiles,
    CMakeCommand,
    CMakeComment,
    CMakeCustomCommand,
    CMakeCustomTarget,
    CMakeElement,
    CMakeEmptyLine,
    CMakeIncludeDirectories,
    CMakePath,
    CMakeSetTargetProperties,
    CMakeTargetIncludeDirectories,
    CMakeVariable,
    IncludeScope,
    cmake_directory_provider,
)
from .generator import CMakeGenerator


class GTestCMakeArtifactsLocator(CMakeArtifactsLocator):
    """Defines the paths to the CMake artifacts for GTest."""

    GTEST_PROJECT_NAME = "googletest"

    def __init__(self, output_dir: Path, execution_context: ExecutionContext) -> None:
        super().__init__(output_dir, execution_context.spl_paths)
        self.cmake_gtest_dir = CMakePath(self._locate_gtest(execution_context))

    def _locate_gtest(self, execution_context: ExecutionContext) -> Path:
        """Resolve the GoogleTest source dir from the data registry, where WestInstall publishes it, so the install layout stays an internal detail."""
        for project in execution_context.data_registry.find_data(ExternalProject):
            if project.name == self.GTEST_PROJECT_NAME:
                return project.path
        raise UserNotificationException(
            f"GoogleTest dependency '{self.GTEST_PROJECT_NAME}' was not installed by a WestInstall step (no matching ExternalProject in the data registry)."
        )


@dataclass
class GTestCMakeGeneratorConfig(DataClassDictMixin):
    #: If this is enabled, all includes are defined globally and not component specific
    use_global_includes: bool = False
    #: Mocking configuration
    mocking: MockingConfig | None = None

    @property
    def automock(self) -> bool:
        if self.mocking and self.mocking.enabled is not None:
            return self.mocking.enabled
        return True


class GTestCMakeComponent:
    def __init__(self, component: Component, execution_context: ExecutionContext) -> None:
        self.component = component
        self.execution_context = execution_context

    @property
    def name(self) -> str:
        return self.component.name

    @property
    def executable_name(self) -> str:
        """The name of the component test executable used to run the tests."""
        return self.component.name

    @property
    def partial_link_name(self) -> str:
        """
        The name of the component partial link library containing only the productive sources.

        Required to determine the required mocks for  the component.
        """
        return f"{self.component.name}_PC"

    def is_testable(self) -> bool:
        return self.component.is_testable

    def get_include_directories(self) -> list[CMakePath]:
        registry_dirs = collect_directories(filter_artifacts(self.execution_context.data_registry.find_data(Artifact), with_label("include"), for_consumer(self.component.name)))
        include_dirs = resolve_include_directories(self.execution_context.components) + registry_dirs
        return [CMakePath(path) for path in include_dirs]


class CMakeMockupCreator:
    def __init__(
        self,
        gtest_cmake_component: GTestCMakeComponent,
        component_object_library_target: str,
        artifacts_locator: GTestCMakeArtifactsLocator,
        mocking_config: MockingConfig | None,
    ):
        self.artifacts_locator = artifacts_locator
        self.gtest_cmake_component = gtest_cmake_component
        self.mocking_config = mocking_config
        self.component_object_library_target = component_object_library_target

    def generate(self) -> list[CMakeElement]:
        elements: list[CMakeElement] = []
        # Create the partial link library containing only the productive sources to be able to find the required mocks
        sources = [CMakePath(source) for source in self.gtest_cmake_component.component.sources]
        # Add the component-specific build directory for the component to find the generated mockup sources
        component_build_dir = self.artifacts_locator.get_component_build_dir(self.gtest_cmake_component.name)
        # Custom command to create the partial link library
        partial_link_obj = component_build_dir.joinpath(f"{self.gtest_cmake_component.partial_link_name}.o")
        custom_command = CMakeCustomCommand(
            description="Create partial link library containing only the productive sources",
            outputs=[partial_link_obj],
            depends=[self.component_object_library_target],
            commands=[
                CMakeCommand(
                    "${CMAKE_CXX_COMPILER}",
                    [
                        "-r",
                        "-nostdlib",
                        "-o",
                        partial_link_obj,
                        f"$<TARGET_OBJECTS:{self.component_object_library_target}>",
                    ],
                )
            ],
            command_expand_lists=True,
        )
        elements.append(custom_command)
        # Custom command to run clanguru and generate the mockup sources
        clanguru_args = []
        if self.mocking_config:
            clanguru_args.append("--strict" if self.mocking_config.strict else "--no-strict")
            if self.mocking_config.exclude_symbol_patterns:
                for pattern in self.mocking_config.exclude_symbol_patterns:
                    clanguru_args.extend(["--exclude-symbol-pattern", f'"{pattern}"'])

        generate_mockup_cmake_cmd = CMakeCustomCommand(
            description="Run clanguru to generate mockup sources",
            outputs=[CMakePath(file) for file in self.get_mockup_generated_files()],
            depends=[partial_link_obj],
            commands=[
                CMakeCommand(
                    "clanguru",
                    [
                        "mock",
                        "--filename",
                        f"mockup_{self.gtest_cmake_component.component.name}",
                        *[f"--source-file {source}" for source in sources],
                        "--partial-object-file",
                        partial_link_obj,
                        "--output-dir",
                        component_build_dir,
                        "--compilation-database",
                        self.artifacts_locator.cmake_build_dir.joinpath("compile_commands.json"),
                        *clanguru_args,
                    ],
                )
            ],
        )
        elements.append(generate_mockup_cmake_cmd)
        # Add custom target for the mockup generation
        elements.append(
            CMakeCustomTarget(
                UserRequest(
                    UserRequestScope.COMPONENT,
                    component_name=self.gtest_cmake_component.name,
                    target=UserRequestTarget.MOCKUP,
                ).target_name,
                f"Generate mockup sources for {self.gtest_cmake_component.name}",
                [],
                generate_mockup_cmake_cmd.outputs,
            )
        )
        return elements

    def get_mockup_generated_files(self) -> list[Path]:
        return [self.get_mockup_file("log"), self.get_mockup_file("h"), *self.get_mockup_sources()]

    def get_mockup_sources(self) -> list[Path]:
        return [self.get_mockup_file("cc")]

    def get_mockup_file(self, file_extension: str) -> Path:
        component_build_dir = self.artifacts_locator.get_component_build_dir(self.gtest_cmake_component.name)
        return component_build_dir.joinpath(f"mockup_{self.gtest_cmake_component.name}.{file_extension}").to_path()


class GTestComponentCMakeGenerator:
    def __init__(self, execution_context: ExecutionContext, output_dir: Path, config: GTestCMakeGeneratorConfig) -> None:
        self.execution_context = execution_context
        self.artifacts_locator = GTestCMakeArtifactsLocator(output_dir, execution_context)
        self.config = config

    def generate(self, component: Component) -> list[CMakeElement]:
        component_generator_config = self._determine_component_generator_config(component)

        component_build_dir = self.artifacts_locator.get_component_build_dir(component.name)
        gtest_cmake_component = GTestCMakeComponent(component, self.execution_context)

        elements: list[CMakeElement] = []
        elements.append(CMakeComment(f"Component {component.name}"))
        # A container compiles nothing itself; it only runs its subcomponents' tests.
        if component.is_container:
            elements.extend(self._test_targets(component, self._subcomponent_test_targets(component)))
            elements.append(CMakeEmptyLine())
            return elements

        # Create the component executable
        productive_sources = component.sources

        # Always create the component productive sources object library
        component_sources_object_library = CMakeAddLibrary(
            name=gtest_cmake_component.partial_link_name,
            files=productive_sources,
            compile_options=[
                "-ggdb",  # Include detailed debug information to be able to debug the executable.
                "--coverage",  # Enable coverage tracking information to be generated.
            ],
            component_name=component.name,
        )
        elements.append(component_sources_object_library)
        # Add include directories specific to this component plus the component build dir to find generated mockup sources
        include_dirs: list[CMakePath] = [component_build_dir, *gtest_cmake_component.get_include_directories()]
        if include_dirs and not component_generator_config.use_global_includes:
            # Determine include scope: use PRIVATE for libraries with sources, INTERFACE for header-only
            scope = IncludeScope.INTERFACE if not productive_sources else IncludeScope.PRIVATE
            target_includes = CMakeTargetIncludeDirectories(component_sources_object_library.target_name, include_dirs, scope)
            elements.append(target_includes)

        mockup_generator = None
        if component_generator_config.automock:
            mockup_generator = CMakeMockupCreator(
                gtest_cmake_component,
                component_sources_object_library.target_name,
                self.artifacts_locator,
                component_generator_config.mocking,
            )

        # Components without tests will just be compiled
        if component.is_testable:
            all_sources = component.test_sources
            if mockup_generator:
                all_sources += mockup_generator.get_mockup_sources()
            test_executable = self.add_executable(gtest_cmake_component.executable_name, all_sources, component_sources_object_library.target_name, component.name)
            elements.append(test_executable)

            # Set the executable output directory to the component-specific directory
            component_build_dir = self.artifacts_locator.get_component_build_dir(component.name)
            target_properties = CMakeSetTargetProperties(test_executable.name, {"RUNTIME_OUTPUT_DIRECTORY": component_build_dir})
            elements.append(target_properties)

            # Add component-specific include directories when global includes are disabled
            if include_dirs and not component_generator_config.use_global_includes:
                # Determine visibility: use PRIVATE for executables with sources, INTERFACE for header-only
                scope = IncludeScope.INTERFACE if not all_sources else IncludeScope.PRIVATE
                target_includes = CMakeTargetIncludeDirectories(test_executable.name, include_dirs, scope)
                elements.append(target_includes)

            # Create the custom target to execute the tests
            execute_tests_command = self.run_executable(component.name, test_executable.name)
            elements.append(execute_tests_command)

            # Generate coverage report
            coverage_cmd = self.create_coverage_report(component.name, execute_tests_command, productive_sources, component_sources_object_library.target_name)
            elements.append(coverage_cmd)
            component_coverage_target = UserRequest(
                UserRequestScope.COMPONENT,
                component_name=component.name,
                target=UserRequestTarget.COVERAGE,
            )

            elements.append(
                CMakeCustomTarget(
                    name=component_coverage_target.target_name,
                    description=f"Generate coverage report for {component.name}",
                    commands=[],
                    depends=coverage_cmd.outputs,
                )
            )

            coverage_artifacts_locator = CoverageArtifactsLocator.from_cmake_artifacts_locator(self.artifacts_locator)
            # The gcovr --html-details run populates the component coverage html dir with files
            # that ninja does not track. Register the directory for recursive removal on `clean`.
            elements.append(
                CMakeAddTargetCleanFiles(
                    target=component_coverage_target.target_name,
                    files=[coverage_artifacts_locator.get_component_coverage_reports_dir(component.name)],
                )
            )

            # Register the component coverage html report as relevant for the component report
            # When registering an html content, the path shall be relative to the reports directory
            index_html = (
                coverage_artifacts_locator.get_component_coverage_html_file(component.name)
                .to_path()
                .relative_to(coverage_artifacts_locator.get_component_reports_dir(component.name).to_path())
            )
            self.execution_context.data_registry.insert(
                ReportRelevantFiles(
                    target=component_coverage_target,
                    files_to_be_included=[],
                    file_type=ReportRelevantFileType.COVERAGE_RESULT,
                    html_content=ReportRelevantHtmlContent(
                        name="Coverage Report",
                        index_html=index_html,
                    ),
                ),
                component_coverage_target.target_name,
            )
            # Register the component coverage json report as relevant for the merged coverage report
            self.execution_context.data_registry.insert(
                CoverageRelevantFile(
                    target=component_coverage_target,
                    json_report=self.artifacts_locator.get_component_build_artifact(component.name, BuildArtifact.COVERAGE_JSON),
                ),
                component_coverage_target.target_name,
            )

            # Create the component mockup sources
            if mockup_generator:
                elements.extend(mockup_generator.generate())

            # Create the component custom targets
            elements.extend(self._test_targets(component, execute_tests_command.outputs or []))
        else:
            elements.append(CMakeComment(f"Component {component.name} is not testable, only compiling sources."))
        elements.append(CMakeEmptyLine())

        return elements

    def _test_targets(self, component: Component, depends: Sequence[str | CMakePath]) -> list[CMakeElement]:
        return [
            CMakeCustomTarget(
                UserRequest(UserRequestScope.COMPONENT, component_name=component.name, target=target).target_name,
                f"Execute tests for {component.name}",
                [],
                depends,
                True,
            )
            for target in (UserRequestTarget.TEST, UserRequestTarget.BUILD)
        ]

    def _subcomponent_test_targets(self, component: Component) -> list[str]:
        """Test targets of the testable subcomponents, recursively, so running a container's tests runs theirs too."""
        targets: list[str] = []
        for subcomponent in component.subcomponents:
            if subcomponent.is_testable:
                targets.append(UserRequest(UserRequestScope.COMPONENT, component_name=subcomponent.name, target=UserRequestTarget.TEST).target_name)
            targets.extend(self._subcomponent_test_targets(subcomponent))
        return targets

    def _determine_component_generator_config(self, component: Component) -> GTestCMakeGeneratorConfig:
        """Take over the component mocking configuration over the global generator configuration."""
        result = self.config
        if component.testing and component.testing.mocking:
            if not result.mocking:
                result.mocking = component.testing.mocking
            else:
                result.mocking = merge_configs(result.mocking, component.testing.mocking)
        return result

    def add_executable(self, executable_name: str, sources: list[Path], component_object_library: str, component_name: str) -> CMakeAddExecutable:
        return CMakeAddExecutable(
            name=executable_name,
            sources=[CMakePath(source) for source in sources],
            libraries=["GTest::gtest_main", "GTest::gmock_main", "pthread", component_object_library],
            compile_options=[
                "-ggdb",  # Include detailed debug information to be able to debug the executable.
            ],
            link_options=["--coverage"],  # Enable coverage analysis.
            component_name=component_name,
        )

    def run_executable(self, component_name: str, component_executable_name: str) -> CMakeCustomCommand:
        component_build_dir = self.artifacts_locator.get_component_build_dir(component_name)
        junit_report_file = component_build_dir.joinpath(f"{component_name}_junit.xml")
        # The executable will be in the component-specific directory
        executable_path = component_build_dir.joinpath(component_executable_name)
        command = CMakeCommand(
            executable_path,
            [
                f"--gtest_output=xml:{junit_report_file}",
                "||",
                "${CMAKE_COMMAND}",
                "-E",
                "true",
            ],
        )
        outputs = [component_build_dir.joinpath(f"{component_name}_junit.xml")]
        return CMakeCustomCommand(
            "Run the test executable, generate JUnit report and return success independent of the test result",
            outputs=outputs,
            depends=[component_executable_name],
            commands=[command],
        )

    def create_coverage_report(
        self,
        component_name: str,
        execute_tests_command: CMakeCustomCommand,
        sources: list[Path],
        component_object_library: str,
    ) -> CMakeCustomCommand:
        artifacts_locator = CoverageArtifactsLocator.from_cmake_artifacts_locator(self.artifacts_locator)
        component_build_dir = artifacts_locator.get_component_build_dir(component_name)
        gcovr_config_file = component_build_dir.joinpath("gcovr.cfg")
        gcovr_json_file = artifacts_locator.get_component_build_artifact(component_name, BuildArtifact.COVERAGE_JSON)
        gcovr_html_dir = artifacts_locator.get_component_coverage_reports_dir(component_name)
        gcovr_html_file = artifacts_locator.get_component_coverage_html_file(component_name)

        return CMakeCustomCommand(
            description=f"Generate coverage report for component {component_name}",
            outputs=[gcovr_config_file, gcovr_json_file, gcovr_html_file],
            depends=execute_tests_command.outputs,
            command_expand_lists=True,
            commands=[
                CMakeCommand(
                    "yanga_cmd",
                    [
                        "gcovr_config_component",
                        "--component-objects",
                        f"$<TARGET_OBJECTS:{component_object_library}>",
                        "--source-files",
                        *[CMakePath(src) for src in sources],
                        "--output-file",
                        gcovr_config_file,
                    ],
                ),
                CMakeCommand(
                    "gcovr",
                    [
                        "--config",
                        gcovr_config_file,
                        "--json",
                        "--output",
                        gcovr_json_file,
                        "--json-pretty",
                    ],
                ),
                CMakeCommand(
                    "${CMAKE_COMMAND}",
                    [
                        "-E",
                        "make_directory",
                        gcovr_html_dir,
                    ],
                ),
                CMakeCommand(
                    "gcovr",
                    [
                        "--config",
                        gcovr_config_file,
                        "--add-tracefile",
                        gcovr_json_file,
                        "--html",
                        "--html-details",
                        "--output",
                        gcovr_html_file,
                    ],
                ),
            ],
        )


class GTestCMakeGenerator(CMakeGenerator):
    """Generates CMake elements to build an executable for a variant."""

    def __init__(self, execution_context: ExecutionContext, output_dir: Path, config: dict[str, Any] | None = None) -> None:
        super().__init__(execution_context, output_dir, config)
        self.artifacts_locator = GTestCMakeArtifactsLocator(output_dir, execution_context)

    @property
    def variant_name(self) -> str | None:
        return self.execution_context.variant_name

    @cached_property
    def config_obj(self) -> GTestCMakeGeneratorConfig:
        """Lazily creates and caches a GTestCMakeGeneratorConfig instance."""
        return GTestCMakeGeneratorConfig.from_dict(self.config) if self.config else GTestCMakeGeneratorConfig()

    def generate(self) -> list[CMakeElement]:
        elements: list[CMakeElement] = []
        elements.append(CMakeComment(f"Generated by {self.__class__.__name__}"))
        elements.extend(self.create_gtest_integration_cmake_elements())
        elements.extend(self.create_components_cmake_elements())
        elements.extend(self.create_variant_cmake_elements())
        return elements

    def create_gtest_integration_cmake_elements(self) -> list[CMakeElement]:
        elements: list[CMakeElement] = []
        elements.append(CMakeVariable("CMAKE_CXX_STANDARD", "14"))
        elements.append(CMakeVariable("CMAKE_CXX_STANDARD_REQUIRED", "ON"))
        elements.append(CMakeVariable("gtest_force_shared_crt", "ON", True, "BOOL", "", True))
        elements.append(CMakeComment("Add local GoogleTest directory"))
        elements.append(
            CMakeAddSubdirectory(
                self.artifacts_locator.cmake_gtest_dir,
                self.artifacts_locator.cmake_build_dir.joinpath(".gtest"),
            )
        )
        if self.config_obj.use_global_includes:
            elements.append(self.get_include_directories())
        else:
            elements.append(CMakeComment("Use global includes for all components disabled."))
        return elements

    def get_include_directories(self) -> CMakeIncludeDirectories:
        registry_dirs = collect_directories(filter_artifacts(self.execution_context.data_registry.find_data(Artifact), with_label("include"), for_consumer()))
        include_dirs = resolve_include_directories(self.execution_context.components) + registry_dirs
        # Add the GTest and GMock include directory
        for name in ["googletest", "googlemock"]:
            include_dirs.append(self.artifacts_locator.cmake_gtest_dir.joinpath(f"{name}/include").to_path())
        # Add the component-specific build directories to the include directories to be able to include the generated mockup sources
        for component in self.execution_context.components:
            component_build_dir = self.artifacts_locator.get_component_build_dir(component.name)
            include_dirs.append(component_build_dir.to_path())
        return CMakeIncludeDirectories([CMakePath(path) for path in include_dirs])

    def create_components_cmake_elements(self) -> list[CMakeElement]:
        elements: list[CMakeElement] = []
        component_generator = GTestComponentCMakeGenerator(self.execution_context, self.output_dir, self.config_obj)
        for component in self.execution_context.components:
            elements.extend(component_generator.generate(component))
        return elements

    def create_variant_cmake_elements(self) -> list[CMakeElement]:
        elements: list[CMakeElement] = []
        # Collect all coverage json reports for the variant coverage report
        artifacts_locator = CoverageArtifactsLocator.from_cmake_artifacts_locator(self.artifacts_locator)
        coverage_relevant_json_reports = [entry.json_report for entry in self.execution_context.data_registry.find_data(CoverageRelevantFile)]
        gcovr_config_file = artifacts_locator.cmake_build_dir.joinpath("gcovr.cfg")
        gcovr_html_dir = artifacts_locator.get_variant_coverage_reports_dir()
        gcovr_html_file = artifacts_locator.get_variant_coverage_html_file()

        # One canonical provider for the variant coverage reports directory. Consumers that write into this dir
        # depend on its stamp; ninja then serializes the make_directory through the dep graph.
        gcovr_html_dir_provider = cmake_directory_provider(gcovr_html_dir)
        elements.append(gcovr_html_dir_provider.command)

        # The html coverage reports are generated in the component specific reports directories.
        # We need to create custom commands to copy them to the variant report directory.
        targets_with_coverage_results = [
            entry.target
            for entry in self.execution_context.data_registry.find_data(ReportRelevantFiles)
            if entry.file_type == ReportRelevantFileType.COVERAGE_RESULT and entry.target.scope == UserRequestScope.COMPONENT and entry.target.component_name is not None
        ]
        coverage_report_dependencies: list[CMakePath] = coverage_relevant_json_reports
        component_variant_coverage_html_dirs: list[CMakePath] = []
        for target in targets_with_coverage_results:
            component_name = target.component_name
            if component_name is None:
                raise ValueError("Component name must be set for component scope targets.")
            artifacts_locator = CoverageArtifactsLocator.from_cmake_artifacts_locator(self.artifacts_locator)
            # Get the directory where the component coverage html report was generated. This directory will be copied to the variant report directory
            component_coverage_html_dir = artifacts_locator.get_component_coverage_reports_dir(component_name)
            component_variant_coverage_html_dir = artifacts_locator.get_component_variant_coverage_reports_dir(component_name)
            component_variant_coverage_html_dirs.append(component_variant_coverage_html_dir)
            # copy_directory has no canonical file output (it copies an arbitrary tree), so the tracked output is a stamp we touch ourselves.
            # The destination dir is not given a directory provider: only this command writes into it, so there is no race to gate against.
            copy_done_stamp = component_variant_coverage_html_dir.joinpath(".yanga.stamp")
            copy_coverage_html_cmd = CMakeCustomCommand(
                description=f"Copy coverage html report for component {component_name} to variant report directory",
                outputs=[copy_done_stamp],
                depends=[target.target_name, gcovr_html_dir_provider.stamp],
                commands=[
                    CMakeCommand(
                        "${CMAKE_COMMAND}",
                        [
                            "-E",
                            "copy_directory",
                            component_coverage_html_dir,
                            component_variant_coverage_html_dir,
                        ],
                    ),
                    CMakeCommand("${CMAKE_COMMAND}", ["-E", "touch", copy_done_stamp]),
                ],
            )
            elements.append(copy_coverage_html_cmd)
            coverage_report_dependencies.append(copy_done_stamp)

        coverage_cmd = CMakeCustomCommand(
            description="Generate coverage report for the variant",
            outputs=[gcovr_config_file, gcovr_html_file],
            depends=[gcovr_html_dir_provider.stamp, *coverage_report_dependencies],
            commands=[
                CMakeCommand(
                    "yanga_cmd",
                    [
                        "gcovr_config_variant",
                        "--variant-report-config",
                        self.artifacts_locator.get_build_artifact(BuildArtifact.REPORT_CONFIG),
                        "--output-file",
                        gcovr_config_file,
                    ],
                ),
                CMakeCommand(
                    "gcovr",
                    [
                        "--config",
                        gcovr_config_file,
                        "--html",
                        "--html-details",
                        "--output",
                        gcovr_html_file,
                    ],
                ),
            ],
        )
        elements.append(coverage_cmd)
        variant_coverage_target = UserRequest(
            UserRequestScope.VARIANT,
            target=UserRequestTarget.COVERAGE,
        )
        elements.append(
            CMakeCustomTarget(
                name=variant_coverage_target.target_name,
                description="Generate variant coverage report",
                commands=[],
                depends=coverage_cmd.outputs,
            )
        )
        # gcovr --html-details and copy_directory populate these dirs with files unknown to ninja.
        # Register them for recursive removal on `clean` to avoid "Directory not empty" failures.
        elements.append(
            CMakeAddTargetCleanFiles(
                target=variant_coverage_target.target_name,
                files=[gcovr_html_dir, *component_variant_coverage_html_dirs],
            )
        )
        # Register the variant coverage html report as relevant for the variant report
        self.execution_context.data_registry.insert(
            ReportRelevantFiles(
                target=variant_coverage_target,
                files_to_be_included=[],
                file_type=ReportRelevantFileType.COVERAGE_RESULT,
                html_content=ReportRelevantHtmlContent(
                    name="Coverage Report",
                    # When registering an html content, the path shall be relative to the reports directory
                    index_html=gcovr_html_file.to_path().relative_to(artifacts_locator.cmake_variant_reports_dir.to_path()),
                ),
            ),
            variant_coverage_target.target_name,
        )

        return elements
