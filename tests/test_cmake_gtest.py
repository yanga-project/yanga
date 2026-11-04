from pathlib import Path

import pytest
from py_app_dev.core.data_registry import DataRegistry
from py_app_dev.core.exceptions import UserNotificationException
from pypeline.domain.external_project import ExternalProject
from yanga_core.domain.components import Component
from yanga_core.domain.config import MockingConfig, TestingConfig
from yanga_core.domain.execution_context import ExecutionContext

from tests.utils import assert_element_of_type, assert_elements_of_type, find_elements_of_type
from yanga.cmake.cmake_backend import (
    CMakeAddExecutable,
    CMakeAddLibrary,
    CMakeAddTargetCleanFiles,
    CMakeCustomCommand,
    CMakeCustomTarget,
    CMakeElement,
    CMakeInclude,
    CMakeIncludeDirectories,
    CMakeTargetIncludeDirectories,
    CMakeVariable,
    IncludeScope,
)
from yanga.cmake.gtest import GTestCMakeArtifactsLocator, GTestCMakeGenerator, GTestCMakeGeneratorConfig, GTestComponentCMakeGenerator
from yanga.cmake.sphinx_test_report import TestResultFile


@pytest.fixture
def execution_context(execution_context: ExecutionContext) -> ExecutionContext:
    """Extend the shared context with the googletest dependency the WestInstall step publishes at runtime; the GTest generator resolves it from the registry."""
    execution_context.data_registry.insert(ExternalProject(name="googletest", revision="v1.17.0", path=Path("ext/gtest/v1.17.0")), provider="WestInstall")
    return execution_context


@pytest.fixture
def gtest_cmake_generator(execution_context: ExecutionContext, output_dir: Path) -> GTestCMakeGenerator:
    return GTestCMakeGenerator(execution_context, output_dir)


def test_gtest_dir_is_resolved_from_the_external_project_registry(execution_context: ExecutionContext, output_dir: Path) -> None:
    locator = GTestCMakeArtifactsLocator(output_dir, execution_context)
    assert locator.cmake_gtest_dir.to_path() == Path("ext/gtest/v1.17.0")


def test_missing_googletest_dependency_raises(execution_context: ExecutionContext, output_dir: Path) -> None:
    execution_context.data_registry = DataRegistry()  # nothing installed googletest
    with pytest.raises(UserNotificationException, match="googletest"):
        GTestCMakeArtifactsLocator(output_dir, execution_context)


def test_generate(gtest_cmake_generator: GTestCMakeGenerator) -> None:
    elements = gtest_cmake_generator.generate()
    assert elements

    variables = assert_elements_of_type(elements, CMakeVariable, 3)
    assert [var.name for var in variables] == ["CMAKE_CXX_STANDARD", "CMAKE_CXX_STANDARD_REQUIRED", "gtest_force_shared_crt"]
    assert_elements_of_type(elements, CMakeInclude, 0)


def test_create_variant_cmake_elements(
    gtest_cmake_generator: GTestCMakeGenerator,
) -> None:
    elements = gtest_cmake_generator.create_gtest_integration_cmake_elements()
    assert elements


def test_cmake_build_components_file(
    gtest_cmake_generator: GTestCMakeGenerator,
) -> None:
    elements = gtest_cmake_generator.create_components_cmake_elements()

    object_libraries = assert_elements_of_type(elements, CMakeAddLibrary, 2)
    assert {lib.name for lib in object_libraries} == {"CompA_PC", "CompBNotTestable_PC"}
    executable = assert_element_of_type(elements, CMakeAddExecutable)
    assert executable.name == "CompA"
    targets = assert_elements_of_type(elements, CMakeCustomTarget, 4)
    assert {target.name for target in targets} == {"CompA_mockup", "CompA_test", "CompA_build", "CompA_coverage"}


def test_get_include_directories(gtest_cmake_generator: GTestCMakeGenerator) -> None:
    assert len(gtest_cmake_generator.get_include_directories().paths) == 6


def test_gtest_cmake_generator_coverage(execution_context: ExecutionContext, output_dir: Path) -> None:
    elements = GTestCMakeGenerator(execution_context, output_dir).generate()

    # Test that coverage targets are created
    targets = assert_elements_of_type(elements, CMakeCustomTarget, 5)
    assert {target.name for target in targets} == {"CompA_mockup", "CompA_test", "CompA_build", "CompA_coverage", "coverage"}

    # Test component coverage target
    component_coverage_target = assert_element_of_type(elements, CMakeCustomTarget, lambda tgt: tgt.name == "CompA_coverage")
    assert "Generate coverage report for CompA" in component_coverage_target.description

    # Test variant coverage target
    variant_coverage_target = assert_element_of_type(elements, CMakeCustomTarget, lambda tgt: tgt.name == "coverage")
    assert "Generate variant coverage report" in variant_coverage_target.description

    # Test that coverage commands are generated
    coverage_commands = find_elements_of_type(elements, CMakeCustomCommand)
    component_coverage_cmds = [cmd for cmd in coverage_commands if "coverage report for component" in cmd.description]
    variant_coverage_cmds = [cmd for cmd in coverage_commands if "coverage report for the variant" in cmd.description]

    assert len(component_coverage_cmds) == 1, "Should generate component coverage commands"
    assert len(variant_coverage_cmds) == 1, "Should generate variant coverage commands"

    # Test that coverage outputs are generated (config, JSON, HTML)
    component_cmd = component_coverage_cmds[0]
    assert component_cmd.outputs, "Component coverage command should have outputs"
    output_paths = [str(output) for output in component_cmd.outputs]
    assert any("gcovr.cfg" in path for path in output_paths), "Should generate gcovr config"
    assert any("coverage.json" in path for path in output_paths), "Should generate JSON report"
    assert any("index.html" in path for path in output_paths), "Should generate HTML report"

    # Test that the right tools are used
    assert component_cmd.commands, "Component coverage command should have subcommands"
    command_tools = [str(cmd.command) for cmd in component_cmd.commands]
    assert any("yanga_cmd" in tool for tool in command_tools), "Should use yanga_cmd for config"
    assert any("gcovr" in tool for tool in command_tools), "Should use gcovr for reports"


def test_junit_report_is_registered_as_test_result(execution_context: ExecutionContext, output_dir: Path) -> None:
    GTestCMakeGenerator(execution_context, output_dir).generate()

    test_results = execution_context.data_registry.find_data(TestResultFile)
    assert [entry.target.target_name for entry in test_results] == ["CompA_test"]
    assert test_results[0].junit_report.to_path().name == "CompA_junit.xml"


def test_coverage_targets_register_clean_files(execution_context: ExecutionContext, output_dir: Path) -> None:
    elements = GTestCMakeGenerator(execution_context, output_dir).generate()

    clean_files = find_elements_of_type(elements, CMakeAddTargetCleanFiles)
    by_target = {entry.target: entry for entry in clean_files}

    assert "CompA_coverage" in by_target, "Component coverage target must register its html dir for clean"
    component_paths = [str(file) for file in by_target["CompA_coverage"].files]
    assert any("reports/coverage/CompA" in path for path in component_paths), f"Component coverage clean files should include reports/coverage/CompA, got {component_paths}"

    assert "coverage" in by_target, "Variant coverage target must register its html dirs for clean"
    variant_paths = [str(file) for file in by_target["coverage"].files]
    assert any(path.endswith("reports/coverage") for path in variant_paths), f"Variant coverage clean files should include the variant reports/coverage dir, got {variant_paths}"
    assert any("reports/coverage/CompA" in path for path in variant_paths), f"Variant coverage clean files should include the per-component variant subdir, got {variant_paths}"


def test_no_path_is_both_tracked_output_and_clean_file(execution_context: ExecutionContext, output_dir: Path) -> None:
    """
    Regression: a path must not appear simultaneously as a tracked output and a clean file.

    Ninja's clean calls POSIX remove() on tracked outputs, which fails on
    non-empty directories. Such directories must be tracked only via stamp files.
    """
    elements = GTestCMakeGenerator(execution_context, output_dir).generate()

    tracked_outputs = {str(output) for cmd in find_elements_of_type(elements, CMakeCustomCommand) for output in cmd.outputs or []}
    clean_files = {str(file) for entry in find_elements_of_type(elements, CMakeAddTargetCleanFiles) for file in entry.files}

    overlap = tracked_outputs & clean_files
    assert not overlap, f"Paths must not be both tracked outputs and clean files: {overlap}"


def test_coverage_command_has_expand_lists_enabled(execution_context: ExecutionContext, output_dir: Path) -> None:
    elements = GTestCMakeGenerator(execution_context, output_dir).generate()

    coverage_commands = find_elements_of_type(elements, CMakeCustomCommand)
    component_coverage_cmds = [cmd for cmd in coverage_commands if "coverage report for component" in cmd.description]
    assert len(component_coverage_cmds) == 1

    component_cmd = component_coverage_cmds[0]
    assert component_cmd.command_expand_lists is True, "Coverage command should have command_expand_lists enabled for TARGET_OBJECTS expansion"


def test_automock_enabled_by_default(execution_context: ExecutionContext, output_dir: Path) -> None:
    # Run IUT
    elements = GTestCMakeGenerator(execution_context, output_dir).generate()

    # Expect the partial link library required to find the symbols to be mocked
    executable = assert_element_of_type(elements, CMakeAddExecutable, lambda exec: exec.name == "CompA")
    expected_test_source = f"{execution_context.project_root_dir.as_posix()}/compA/test_compA_source.cpp"
    assert [str(source) for source in executable.sources] == [expected_test_source, f"{output_dir.as_posix()}/CompA/mockup_CompA.cc"]
    assert [source.as_posix() for source in execution_context.components[0].test_sources] == [expected_test_source]
    assert set(executable.libraries) == {"GTest::gtest_main", "GTest::gmock_main", "pthread", "CompA_PC_lib"}
    custom_command = assert_element_of_type(elements, CMakeCustomCommand, lambda cmd: cmd.description.startswith("Run the test executable"))
    assert len(custom_command.commands) == 1
    # The command should now be the full path to the executable in the component directory
    command_str = str(custom_command.commands[0].command)
    assert "CompA" in command_str, f"Expected CompA in command path: {command_str}"
    # Check that the arguments include the component-specific JUnit XML path
    args = [str(arg) for arg in custom_command.commands[0].arguments]
    junit_arg = next((arg for arg in args if "junit.xml" in arg), None)
    assert junit_arg is not None, f"JUnit XML argument not found in: {args}"
    assert "CompA" in junit_arg, f"Component-specific path not found in JUnit argument: {junit_arg}"


def test_automock_disabled_generates_no_mock_targets(execution_context: ExecutionContext, output_dir: Path) -> None:
    # Run IUT
    elements = GTestCMakeGenerator(execution_context, output_dir, {"mocking": {"enabled": False}}).generate()

    # No mockup-related custom targets should be generated.
    targets = assert_elements_of_type(elements, CMakeCustomTarget, 4)
    assert {target.name for target in targets} == {"CompA_test", "CompA_build", "CompA_coverage", "coverage"}

    # No partial link library should be generated.
    object_libraries = assert_elements_of_type(elements, CMakeAddLibrary, 2)
    assert {lib.target_name for lib in object_libraries} == {"CompA_PC_lib", "CompBNotTestable_PC_lib"}

    executable = assert_element_of_type(elements, CMakeAddExecutable, lambda exec: exec.name == "CompA")
    assert [str(source) for source in executable.sources] == [f"{execution_context.project_root_dir.as_posix()}/compA/test_compA_source.cpp"]
    assert set(executable.libraries) == {"GTest::gtest_main", "GTest::gmock_main", "pthread", "CompA_PC_lib"}


def test_use_global_includes_disabled_generates_no_global_include_directories(execution_context: ExecutionContext, output_dir: Path) -> None:
    # Global include directories should not be generated in the variant elements
    variant_elements = GTestCMakeGenerator(execution_context, output_dir, {"use_global_includes": False}).create_gtest_integration_cmake_elements()

    # Check that no CMakeIncludeDirectories is present in variant elements
    include_directories = find_elements_of_type(variant_elements, CMakeIncludeDirectories)
    assert len(include_directories) == 0


def test_use_global_includes_enabled_generates_global_include_directories(execution_context: ExecutionContext, output_dir: Path) -> None:
    # Global include directories should be generated in the variant elements
    variant_elements = GTestCMakeGenerator(execution_context, output_dir, {"use_global_includes": True}).create_gtest_integration_cmake_elements()

    # Check that CMakeIncludeDirectories is present in variant elements
    include_directories = find_elements_of_type(variant_elements, CMakeIncludeDirectories)
    assert len(include_directories) == 1  # Should have one CMakeIncludeDirectories element


def test_use_global_includes_disabled_adds_component_specific_include_directories(execution_context: ExecutionContext, output_dir: Path) -> None:
    # The resolved component carries its include directories already resolved under its path.
    component = find_elements_of_type(execution_context.components, Component)[0]  # CompA, path "compA"
    component.include_directories = [component.path / "inc", component.path / "src"]

    # Generate elements with use_global_includes=False
    elements = GTestCMakeGenerator(execution_context, output_dir, {"use_global_includes": False}).generate()

    # Find the executable
    executable = assert_element_of_type(elements, CMakeAddExecutable)
    assert executable.name == "CompA"

    # Check that CMakeTargetIncludeDirectories elements are generated
    target_includes = find_elements_of_type(elements, CMakeTargetIncludeDirectories)
    assert len(target_includes) > 0, "No CMakeTargetIncludeDirectories elements found"

    # Find the target include directories for our executable
    component_target_includes = [ti for ti in target_includes if ti.target_name == "CompA"]
    assert len(component_target_includes) > 0, "No target include directories found for target CompA"

    # The declared include directories are resolved under the component path.
    all_paths = [Path(str(path.path)).as_posix() for ti in component_target_includes for path in ti.paths]
    assert any(p.endswith("compA/inc") for p in all_paths), f"Component include directory not found in target includes: {all_paths}"
    assert any(p.endswith("compA/src") for p in all_paths), f"Component include directory not found in target includes: {all_paths}"

    # Verify that the visibility is PRIVATE for executables with sources
    component_ti = component_target_includes[0]
    assert component_ti.scope == IncludeScope.PRIVATE, f"Expected PRIVATE visibility, got {component_ti.scope}"


def test_component_specific_directories_are_used(execution_context: ExecutionContext, output_dir: Path) -> None:
    elements = GTestCMakeGenerator(execution_context, output_dir).generate()

    # Find custom commands that contain component-specific paths
    custom_commands = find_elements_of_type(elements, CMakeCustomCommand)

    # Look for JUnit XML output files in component-specific directories
    junit_outputs = [cmd for cmd in custom_commands if cmd.outputs and any("_junit.xml" in str(output) for output in cmd.outputs)]
    assert len(junit_outputs) > 0, "No JUnit XML custom commands found"

    # Verify the JUnit XML file is in a component-specific directory
    junit_cmd = junit_outputs[0]
    assert junit_cmd.outputs
    junit_output_path = str(junit_cmd.outputs[0])
    assert "CompA_junit.xml" in junit_output_path, f"Expected CompA_junit.xml in path: {junit_output_path}"
    # The path should contain the component name as a subdirectory
    assert "CompA" in junit_output_path, f"Component subdirectory not found in JUnit path: {junit_output_path}"

    # Look for mockup generation commands
    mockup_commands = [cmd for cmd in custom_commands if cmd.outputs and any("mockup_" in str(output) for output in cmd.outputs)]
    assert len(mockup_commands) > 0, "No mockup generation commands found"

    # Verify mockup files are in component-specific directories
    mockup_cmd = mockup_commands[0]
    assert mockup_cmd.outputs
    mockup_output_paths = [str(output) for output in mockup_cmd.outputs]
    for path in mockup_output_paths:
        assert "mockup_CompA" in path, f"Expected mockup_CompA in path: {path}"
        assert "CompA" in path, f"Component subdirectory not found in mockup path: {path}"


def test_executable_output_directory_is_set(execution_context: ExecutionContext, output_dir: Path) -> None:
    elements = GTestCMakeGenerator(execution_context, output_dir).generate()

    # Import the target properties class for type checking
    from yanga.cmake.cmake_backend import CMakeSetTargetProperties

    # Find CMakeSetTargetProperties elements
    target_properties = find_elements_of_type(elements, CMakeSetTargetProperties)
    assert len(target_properties) > 0, "No target properties found"

    # Find the properties for CompA executable
    comp_a_properties = [tp for tp in target_properties if tp.target == "CompA"]
    assert len(comp_a_properties) == 1, f"Expected 2 target properties for CompA (runtime and discovery), found {len(comp_a_properties)}"

    # Find the runtime output directory property
    runtime_props = [tp for tp in comp_a_properties if "RUNTIME_OUTPUT_DIRECTORY" in tp.properties]
    assert len(runtime_props) == 1, "RUNTIME_OUTPUT_DIRECTORY property not found"

    runtime_dir = str(runtime_props[0].properties["RUNTIME_OUTPUT_DIRECTORY"])
    assert "CompA" in runtime_dir, f"Component subdirectory not found in runtime output directory: {runtime_dir}"


def test_component_mocking_config_overrides_global(execution_context: ExecutionContext, output_dir: Path) -> None:
    global_mocking_config = GTestCMakeGeneratorConfig.from_dict({"mocking": {"enabled": True, "exclude_symbol_patterns": ["GlobalPattern1", "GlobalPattern2"], "strict": False}})
    component = Component(
        name="CompA",
        path=Path("CompA"),
        sources=[],
        testing=TestingConfig(sources=["test_compA_source.cpp"], mocking=MockingConfig(exclude_symbol_patterns=["CompAPattern1"], strict=True)),
    )
    generator = GTestComponentCMakeGenerator(execution_context, output_dir, global_mocking_config)

    config = generator._determine_component_generator_config(component)

    assert config.mocking is not None
    assert config.mocking.enabled is True, "Inherited global mocking enabled"
    assert config.mocking.exclude_symbol_patterns == ["CompAPattern1"], "Overridden exclude patterns"
    assert config.mocking.strict is True, "Overridden strict setting"


@pytest.fixture
def container_elements(container_execution_context: ExecutionContext, output_dir: Path) -> list[CMakeElement]:
    container_execution_context.data_registry.insert(ExternalProject(name="googletest", revision="v1.17.0", path=Path("ext/gtest/v1.17.0")), provider="WestInstall")
    return GTestCMakeGenerator(container_execution_context, output_dir).generate()


def test_container_test_target_runs_subcomponent_tests(container_elements: list[CMakeElement]) -> None:
    targets = {target.name: list(target.depends or []) for target in find_elements_of_type(container_elements, CMakeCustomTarget)}

    assert targets["net_test"] == targets["net_build"] == ["tcp_test"]
    assert targets["group_test"] == ["tcp_test"]


def test_container_compiles_nothing(container_elements: list[CMakeElement]) -> None:
    assert [library.name for library in find_elements_of_type(container_elements, CMakeAddLibrary)] == ["tcp_PC", "udp_PC"]
    assert [executable.name for executable in find_elements_of_type(container_elements, CMakeAddExecutable)] == ["tcp"]
