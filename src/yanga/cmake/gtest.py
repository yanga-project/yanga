from collections.abc import Sequence
from dataclasses import dataclass, replace
from functools import cached_property
from pathlib import Path
from typing import Any

from mashumaro import DataClassDictMixin
from py_app_dev.core.config import merge_configs
from py_app_dev.core.exceptions import UserNotificationException
from pypeline.domain.external_project import ExternalProject
from yanga_core.domain.artifact import Artifact, collect_directories, filter_artifacts, for_consumer, with_label
from yanga_core.domain.component_resolver import find_testing_block, resolve_include_directories
from yanga_core.domain.components import Component, TestingBlock
from yanga_core.domain.config import MockingConfig
from yanga_core.domain.execution_context import ExecutionContext, UserRequest, UserRequestScope, UserRequestTarget

from yanga.cmake.artifacts_locator import BuildArtifact, CMakeArtifactsLocator
from yanga.cmake.coverage import CoverageArtifactsLocator, CoverageRelevantFile, create_coverage_tracefile_command
from yanga.cmake.sphinx_test_report import GTEST_FRAMEWORK, TestResultFile

from .cmake_backend import (
    CMakeAddExecutable,
    CMakeAddLibrary,
    CMakeAddSubdirectory,
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
)
from .generator import CMakeGenerator

VARIANT_TEST_NAME = "variant_test"


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
        return self.component.is_testable(GTEST_FRAMEWORK)

    def get_include_directories(self) -> list[CMakePath]:
        registry_dirs = collect_directories(filter_artifacts(self.execution_context.data_registry.find_data(Artifact), with_label("include"), for_consumer(self.component.name)))
        include_dirs = resolve_include_directories(self.execution_context.components) + registry_dirs
        return [CMakePath(path) for path in include_dirs]


class CMakeMockupCreator:
    """Mock what the partial link of ``object_library_targets`` leaves undefined, for one component or the whole variant."""

    def __init__(
        self,
        name: str,
        sources: list[Path],
        build_dir: CMakePath,
        object_library_targets: list[str],
        mockup_target_name: str,
        artifacts_locator: GTestCMakeArtifactsLocator,
        mocking_config: MockingConfig | None,
    ):
        self.name = name
        self.sources = sources
        self.build_dir = build_dir
        # Mockup library objects belong here too, so clanguru does not mock the symbols the mockups define.
        self.object_library_targets = object_library_targets
        self.mockup_target_name = mockup_target_name
        self.artifacts_locator = artifacts_locator
        self.mocking_config = mocking_config

    def generate(self) -> list[CMakeElement]:
        elements: list[CMakeElement] = []
        # Create the partial link library containing only the productive sources to be able to find the required mocks
        sources = [CMakePath(source) for source in self.sources]
        component_build_dir = self.build_dir
        # Custom command to create the partial link library
        partial_link_obj = component_build_dir.joinpath(f"{self.name}_PC.o")
        custom_command = CMakeCustomCommand(
            description="Create partial link library containing only the productive sources",
            outputs=[partial_link_obj],
            depends=list(self.object_library_targets),
            commands=[
                CMakeCommand(
                    "${CMAKE_CXX_COMPILER}",
                    [
                        "-r",
                        "-nostdlib",
                        "-o",
                        partial_link_obj,
                        *[f"$<TARGET_OBJECTS:{target}>" for target in self.object_library_targets],
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
            outputs=self.get_mockup_generated_files(),
            depends=[partial_link_obj],
            commands=[
                CMakeCommand(
                    "clanguru",
                    [
                        "mock",
                        "--filename",
                        f"mockup_{self.name}",
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
                self.mockup_target_name,
                f"Generate mockup sources for {self.name}",
                [],
                generate_mockup_cmake_cmd.outputs,
            )
        )
        return elements

    def get_mockup_generated_files(self) -> list[CMakePath]:
        return [self.get_mockup_file("log"), self.get_mockup_file("h"), *self.get_mockup_sources()]

    def get_mockup_sources(self) -> list[CMakePath]:
        return [self.get_mockup_file("cc")]

    def get_mockup_file(self, file_extension: str) -> CMakePath:
        return self.build_dir.joinpath(f"mockup_{self.name}.{file_extension}")


class GTestComponentCMakeGenerator:
    def __init__(self, execution_context: ExecutionContext, output_dir: Path, config: GTestCMakeGeneratorConfig) -> None:
        self.execution_context = execution_context
        self.artifacts_locator = GTestCMakeArtifactsLocator(output_dir, execution_context)
        self.config = config

    def generate(self, component: Component) -> list[CMakeElement]:
        testing_block = find_testing_block(component.testing, GTEST_FRAMEWORK)
        component_generator_config = self._determine_component_generator_config(testing_block)

        component_build_dir = self.artifacts_locator.get_component_build_dir(component.name)
        gtest_cmake_component = GTestCMakeComponent(component, self.execution_context)

        elements: list[CMakeElement] = []
        elements.append(CMakeComment(f"Component {component.name}"))
        # A container compiles nothing itself; the collector runs its subcomponents' tests.
        if component.is_container:
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

        # Components without gtest tests will just be compiled
        if testing_block and gtest_cmake_component.is_testable():
            mockup_library = None
            if testing_block.mockup_sources:
                mockup_library = self.add_mockup_library(f"{component.name}_mockups", testing_block.mockup_sources, component.name)
                elements.append(mockup_library)
                if include_dirs and not component_generator_config.use_global_includes:
                    elements.append(CMakeTargetIncludeDirectories(mockup_library.target_name, include_dirs, IncludeScope.PRIVATE))

            mockup_generator = None
            if component_generator_config.automock:
                mockup_generator = CMakeMockupCreator(
                    component.name,
                    component.sources,
                    component_build_dir,
                    [component_sources_object_library.target_name, *([mockup_library.target_name] if mockup_library else [])],
                    UserRequest(UserRequestScope.COMPONENT, component_name=component.name, target=UserRequestTarget.MOCKUP).target_name,
                    self.artifacts_locator,
                    component_generator_config.mocking,
                )

            # A new list: the generated mocks belong to the executable, not to the test sources the report shows.
            all_sources = [*testing_block.sources, *(source.to_path() for source in (mockup_generator.get_mockup_sources() if mockup_generator else []))]
            test_executable = self.add_executable(gtest_cmake_component.executable_name, all_sources, [component_sources_object_library.target_name], component.name)
            if mockup_library:
                test_executable.libraries.append(mockup_library.target_name)
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
            # Register the JUnit report for the generators that render it (e.g. SphinxTestReportCMakeGenerator)
            component_test_target = UserRequest(UserRequestScope.COMPONENT, component_name=component.name, target=f"{GTEST_FRAMEWORK}_test")
            elements.append(CMakeCustomTarget(component_test_target.target_name, f"Execute tests for {component.name}", [], execute_tests_command.outputs or [], True))
            self.execution_context.data_registry.insert(
                TestResultFile(
                    target=component_test_target,
                    junit_report=self.artifacts_locator.get_component_build_dir(component.name).joinpath(f"{component.name}_junit.xml"),
                    framework=GTEST_FRAMEWORK,
                    test_sources=testing_block.sources,
                ),
                component_test_target.target_name,
            )

            # Generate the coverage tracefile; the collector merges it and builds the reports
            coverage_cmd = self.create_coverage_report(component.name, execute_tests_command, productive_sources, component_sources_object_library.target_name)
            elements.append(coverage_cmd)
            component_coverage_target = UserRequest(
                UserRequestScope.COMPONENT,
                component_name=component.name,
                target=UserRequestTarget.COVERAGE,
            )
            self.execution_context.data_registry.insert(
                CoverageRelevantFile(
                    target=component_coverage_target,
                    json_report=self.artifacts_locator.get_component_build_artifact(component.name, BuildArtifact.COVERAGE_JSON),
                    framework=GTEST_FRAMEWORK,
                ),
                component_coverage_target.target_name,
            )

            # Create the component mockup sources
            if mockup_generator:
                elements.extend(mockup_generator.generate())
        else:
            elements.append(CMakeComment(f"Component {component.name} is not testable, only compiling sources."))
        elements.append(CMakeEmptyLine())

        return elements

    def _determine_component_generator_config(self, testing_block: TestingBlock | None) -> GTestCMakeGeneratorConfig:
        """Merge the block's ``config.mocking`` over the platform mocking into a new config; the shared generator config stays untouched."""
        if not (testing_block and testing_block.config.get("mocking")):
            return self.config
        block_mocking = MockingConfig.from_dict(testing_block.config["mocking"])
        return replace(self.config, mocking=merge_configs(self.config.mocking, block_mocking) if self.config.mocking else block_mocking)

    def add_mockup_library(self, name: str, mockup_sources: list[Path], component_name: str | None) -> CMakeAddLibrary:
        """Test-only helper sources: compiled without coverage, linked into the test executable."""
        return CMakeAddLibrary(name=name, files=mockup_sources, compile_options=["-ggdb"], component_name=component_name)

    def add_executable(self, executable_name: str, sources: Sequence[Path | CMakePath], object_libraries: list[str], component_name: str | None) -> CMakeAddExecutable:
        return CMakeAddExecutable(
            name=executable_name,
            sources=[source if isinstance(source, CMakePath) else CMakePath(source) for source in sources],
            libraries=["GTest::gtest_main", "GTest::gmock_main", "pthread", *object_libraries],
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

        return create_coverage_tracefile_command(
            f"Generate coverage report for component {component_name}",
            execute_tests_command.outputs,
            [component_object_library],
            sources,
            self.execution_context.project_root_dir,
            gcovr_config_file,
            gcovr_json_file,
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
        elements.extend(self.create_variant_test_cmake_elements())
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

    def create_variant_test_cmake_elements(self) -> list[CMakeElement]:
        """
        One test executable for the variant's gtest block, linked against the objects of all selected components.

        It runs with ``GCOV_PREFIX``, so its ``.gcda`` files do not mix into the coverage of the component tests.
        """
        testing_block = find_testing_block(self.execution_context.variant_testing, GTEST_FRAMEWORK)
        if not (testing_block and testing_block.sources):
            return []
        component_generator = GTestComponentCMakeGenerator(self.execution_context, self.output_dir, self.config_obj)
        generator_config = component_generator._determine_component_generator_config(testing_block)
        build_dir = self.artifacts_locator.cmake_build_dir.joinpath(VARIANT_TEST_NAME)
        gcov_dir = build_dir.joinpath("gcov")
        components = self._variant_test_components()
        # The same target names the component generator gives the component object libraries
        object_libraries = [f"{component.name}_PC_lib" for component in components]
        compiled_object_libraries = [f"{component.name}_PC_lib" for component in components if component.sources]
        production_sources = [source for component in components for source in component.sources]
        include_dirs = [build_dir, *self.get_include_directories().paths]

        elements: list[CMakeElement] = [CMakeComment(f"Variant test of {self.variant_name}")]
        mockup_library = None
        if testing_block.mockup_sources:
            mockup_library = component_generator.add_mockup_library(f"{VARIANT_TEST_NAME}_mockups", testing_block.mockup_sources, None)
            elements.append(mockup_library)
            if not generator_config.use_global_includes:
                elements.append(CMakeTargetIncludeDirectories(mockup_library.target_name, include_dirs, IncludeScope.PRIVATE))
        mockup_libraries = [mockup_library.target_name] if mockup_library else []

        mockup_generator = None
        if generator_config.automock:
            mockup_generator = CMakeMockupCreator(
                VARIANT_TEST_NAME,
                production_sources,
                build_dir,
                [*compiled_object_libraries, *mockup_libraries],
                UserRequest(UserRequestScope.VARIANT, target=UserRequestTarget.MOCKUP).target_name,
                self.artifacts_locator,
                generator_config.mocking,
            )
        test_executable = component_generator.add_executable(
            f"{self.variant_name}_{VARIANT_TEST_NAME}",
            [*testing_block.sources, *(mockup_generator.get_mockup_sources() if mockup_generator else [])],
            [*object_libraries, *mockup_libraries],
            None,
        )
        elements.append(test_executable)
        elements.append(CMakeSetTargetProperties(test_executable.name, {"RUNTIME_OUTPUT_DIRECTORY": build_dir}))
        if not generator_config.use_global_includes:
            elements.append(CMakeTargetIncludeDirectories(test_executable.name, include_dirs, IncludeScope.PRIVATE))

        junit_report = build_dir.joinpath(f"{VARIANT_TEST_NAME}_junit.xml")
        execute_tests_command = CMakeCustomCommand(
            "Run the variant test executable, generate JUnit report and return success independent of the test result",
            outputs=[junit_report],
            depends=[test_executable.name],
            commands=[
                CMakeCommand(
                    "${CMAKE_COMMAND}",
                    [
                        "-E",
                        "env",
                        f"GCOV_PREFIX={gcov_dir}",
                        build_dir.joinpath(test_executable.name),
                        f"--gtest_output=xml:{junit_report}",
                        "||",
                        "${CMAKE_COMMAND}",
                        "-E",
                        "true",
                    ],
                )
            ],
        )
        elements.append(execute_tests_command)
        variant_test_target = UserRequest(UserRequestScope.VARIANT, target=f"variant_{GTEST_FRAMEWORK}_test")
        elements.append(CMakeCustomTarget(variant_test_target.target_name, f"Execute the variant test of {self.variant_name}", [], [junit_report], True))
        self.execution_context.data_registry.insert(
            TestResultFile(target=variant_test_target, junit_report=junit_report, framework=GTEST_FRAMEWORK, test_sources=testing_block.sources),
            variant_test_target.target_name,
        )

        elements.extend(self.create_variant_test_coverage(execute_tests_command, compiled_object_libraries, production_sources, gcov_dir))
        if mockup_generator:
            elements.extend(mockup_generator.generate())
        elements.append(CMakeEmptyLine())
        return elements

    def _variant_test_components(self) -> list[Component]:
        """
        The components whose objects the variant ships.

        An integration component holds test-only copies of the objects of the components it integrates; linking it too
        would define their symbols twice.
        """
        return [component for component in self.execution_context.components if not component.is_container and not component.integrates]

    def create_variant_test_coverage(self, execute_tests_command: CMakeCustomCommand, object_libraries: list[str], sources: list[Path], gcov_dir: CMakePath) -> list[CMakeElement]:
        """Write the tracefile of the variant test; the collector builds its own coverage page."""
        build_dir = self.artifacts_locator.cmake_build_dir.joinpath(VARIANT_TEST_NAME)
        gcovr_config_file = build_dir.joinpath("gcovr.cfg")
        gcovr_json_file = build_dir.joinpath(BuildArtifact.COVERAGE_JSON.path)
        coverage_cmd = create_coverage_tracefile_command(
            "Generate coverage report for the variant test",
            execute_tests_command.outputs,
            object_libraries,
            sources,
            self.execution_context.project_root_dir,
            gcovr_config_file,
            gcovr_json_file,
            gcov_dir,
        )
        coverage_target = UserRequest(UserRequestScope.VARIANT, target=f"{VARIANT_TEST_NAME}_coverage")
        self.execution_context.data_registry.insert(
            CoverageRelevantFile(target=coverage_target, json_report=gcovr_json_file, framework=GTEST_FRAMEWORK),
            coverage_target.target_name,
        )
        return [coverage_cmd]
