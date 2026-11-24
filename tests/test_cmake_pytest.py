import importlib.util
import sys
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock

import pytest
from py_app_dev.core.exceptions import UserNotificationException
from pypeline.domain.external_project import ExternalProject
from yanga_core.domain.components import TestingBlock
from yanga_core.domain.config import ComponentConfig, TestingBlockConfig
from yanga_core.domain.execution_context import ExecutionContext, UserRequest, UserRequestScope, UserRequestTarget

from tests.conftest import make_execution_context
from tests.utils import assert_element_of_type, find_elements_of_type
from yanga.cmake.artifacts_locator import CMakeArtifactsLocator
from yanga.cmake.cmake_backend import (
    CMakeAddLibrary,
    CMakeCustomCommand,
    CMakeCustomTarget,
    CMakeElement,
    CMakeSetTargetProperties,
    CMakeTargetLinkLibraries,
    LibraryType,
)
from yanga.cmake.coverage import CoverageRelevantFile
from yanga.cmake.gtest import GTestCMakeGenerator
from yanga.cmake.pytest import PytestCMakeGenerator
from yanga.cmake.sphinx_test_report import TestResultFile
from yanga.cmake.test_results import TestResultsCMakeGenerator

LINUX_NO_UNDEFINED = "$<$<PLATFORM_ID:Linux>:-Wl,-z,defs>"


def comp_a_config(*testing: TestingBlockConfig) -> ComponentConfig:
    return ComponentConfig(name="CompA", path=Path("compA"), sources=["compA.c"], testing=list(testing))


def pytest_block(mocking: dict[str, Any] | None = None) -> TestingBlockConfig:
    return TestingBlockConfig(framework="pytest", sources=["test_compA.py"], mockup_sources=["fake_a.c"], config={"mocking": mocking} if mocking else {})


def scopes_context(tmp_path: Path) -> ExecutionContext:
    configs = [
        comp_a_config(pytest_block()),
        ComponentConfig(name="CompB", path=Path("compB"), sources=["compB.c"]),
        ComponentConfig(
            name="IntegAB",
            path=Path("integ"),
            integrates=["CompA", "CompB"],
            testing=[TestingBlockConfig(framework="pytest", sources=["test_integ.py"], mockup_sources=["fake_integ.c"])],
        ),
    ]
    execution_context = make_execution_context(tmp_path, configs)
    cast(Mock, execution_context).variant_testing = [TestingBlock(framework="pytest", sources=[tmp_path / "test_variant.py"], mockup_sources=[tmp_path / "fake_os.c"])]
    return execution_context


def command_line(command: CMakeCustomCommand) -> str:
    return " ".join(str(arg) for cmake_command in command.commands for arg in cmake_command.arguments)


def target_properties(elements: list[CMakeElement], target: str) -> dict[str, str]:
    return {key: str(value) for props in find_elements_of_type(elements, CMakeSetTargetProperties) if props.target == target for key, value in props.properties.items()}


def bind_command(elements: list[CMakeElement], name: str) -> CMakeCustomCommand:
    return assert_element_of_type(elements, CMakeCustomCommand, lambda cmd: str(cmd.commands[0].command) == "clanguru" and f"--filename {name}_binding " in command_line(cmd))


NO_COVERAGE_OPTIONS = ["-fno-profile-arcs", "-fno-test-coverage", "$<$<AND:$<C_COMPILER_ID:GNU>,$<VERSION_GREATER_EQUAL:$<C_COMPILER_VERSION>,14>>:-fno-condition-coverage>"]


@pytest.mark.parametrize(
    ("name", "build_folder", "object_libraries", "mockup_source", "sources"),
    [
        ("CompA", "CompA", ["CompA_pytest_PC_lib"], "compA/fake_a.c", ["compA/compA.c"]),
        ("IntegAB", "IntegAB", ["IntegAB_pytest_PC_lib"], "integ/fake_integ.c", ["compA/compA.c", "compB/compB.c"]),
        ("mock_variant", "variant_test", ["CompA_pytest_PC_lib", "CompB_pytest_PC_lib"], "fake_os.c", ["compA/compA.c", "compB/compB.c"]),
    ],
    ids=["component", "integration-component", "variant"],
)
def test_test_scope_builds_its_test_library(
    tmp_path: Path, output_dir: Path, name: str, build_folder: str, object_libraries: list[str], mockup_source: str, sources: list[str]
) -> None:
    elements = PytestCMakeGenerator(scopes_context(tmp_path), output_dir).generate()

    build_dir = f"${{CMAKE_BUILD_DIR}}/{build_folder}"
    for object_library in object_libraries:
        [library] = [element for element in find_elements_of_type(elements, CMakeAddLibrary) if element.target_name == object_library]
        assert library.type is LibraryType.OBJECT
        assert {"-ggdb", "--coverage"} <= set(library.compile_options)
        assert target_properties(elements, object_library)["POSITION_INDEPENDENT_CODE"] == "ON"
    mockups = assert_element_of_type(elements, CMakeAddLibrary, lambda lib: lib.target_name == f"{name}_pytest_mockups_lib")
    assert mockups.files == [tmp_path / mockup_source]
    assert mockups.compile_options == ["-ggdb", *NO_COVERAGE_OPTIONS]
    assert target_properties(elements, mockups.target_name)["POSITION_INDEPENDENT_CODE"] == "ON"

    partial_object = f"{build_dir}/{name}_pytest_PC.o"
    partial_link = assert_element_of_type(elements, CMakeCustomCommand, lambda cmd: [str(output) for output in cmd.outputs or []] == [partial_object])
    linked_objects = [*object_libraries, mockups.target_name]
    assert {arg for arg in command_line(partial_link).split() if arg.startswith("$<TARGET_OBJECTS:")} == {f"$<TARGET_OBJECTS:{target}>" for target in linked_objects}
    assert set(linked_objects) <= {str(depend) for depend in partial_link.depends or []}

    bind = bind_command(elements, name)
    source_files = " ".join(f"--source-file {(tmp_path / source).as_posix()}" for source in sources)
    assert command_line(bind) == (
        f"bind --filename {name}_binding --library-name {name}_pytest {source_files} --partial-object-file {partial_object}"
        f" --output-dir {build_dir} --compilation-database ${{CMAKE_BUILD_DIR}}/compile_commands.json"
    )
    assert {str(output) for output in bind.outputs or []} == {f"{build_dir}/{name}_binding{suffix}" for suffix in (".py", "_mocks.c", ".log")}

    shared = assert_element_of_type(elements, CMakeAddLibrary, lambda lib: lib.target_name == f"{name}_pytest_lib")
    assert shared.type is LibraryType.SHARED
    assert shared.compile_options == NO_COVERAGE_OPTIONS
    assert shared.files == [output_dir / build_folder / f"{name}_binding_mocks.c"]
    link_items = {item for link in find_elements_of_type(elements, CMakeTargetLinkLibraries) if link.target == shared.target_name for item in link.libraries}
    assert link_items == {*linked_objects, "--coverage", LINUX_NO_UNDEFINED}
    expected_properties = {
        "OUTPUT_NAME": f"{name}_pytest",
        "PREFIX": '""',
        "WINDOWS_EXPORT_ALL_SYMBOLS": "ON",
        "LIBRARY_OUTPUT_DIRECTORY": build_dir,
        "RUNTIME_OUTPUT_DIRECTORY": build_dir,
    }
    assert expected_properties.items() <= target_properties(elements, shared.target_name).items()


@pytest.mark.parametrize(
    ("platform_mocking", "block_mocking", "expected_arguments"),
    [
        (None, None, ""),
        ({"strict": False, "exclude_symbol_patterns": ["Os_[A-Z]*"]}, None, ' --no-strict --exclude-symbol-pattern "Os_[A-Z]*"'),
        ({"strict": False, "exclude_symbol_patterns": ["Os_[A-Z]*"]}, {"strict": True, "exclude_symbol_patterns": ["^Rte_.*$"]}, ' --strict --exclude-symbol-pattern "^Rte_.*$"'),
        (None, {"strict": True}, " --strict"),
    ],
    ids=["no-mocking", "platform", "block-over-platform", "block"],
)
def test_bind_takes_the_block_mocking_over_the_platform_mocking(
    tmp_path: Path, output_dir: Path, platform_mocking: dict[str, Any] | None, block_mocking: dict[str, Any] | None, expected_arguments: str
) -> None:
    execution_context = make_execution_context(tmp_path, [comp_a_config(pytest_block(block_mocking))])

    elements = PytestCMakeGenerator(execution_context, output_dir, {"mocking": platform_mocking} if platform_mocking else None).generate()

    assert command_line(bind_command(elements, "CompA")).endswith(f"--compilation-database ${{CMAKE_BUILD_DIR}}/compile_commands.json{expected_arguments}")


@pytest.mark.parametrize(
    ("platform_mocking", "block_mocking"),
    [({"enabled": False}, None), (None, {"enabled": False})],
    ids=["platform", "block"],
)
def test_disabled_mocking_is_an_error(tmp_path: Path, output_dir: Path, platform_mocking: dict[str, Any] | None, block_mocking: dict[str, Any] | None) -> None:
    execution_context = make_execution_context(tmp_path, [comp_a_config(pytest_block(block_mocking))])

    with pytest.raises(UserNotificationException, match=r"mocking\.enabled"):
        PytestCMakeGenerator(execution_context, output_dir, {"mocking": platform_mocking} if platform_mocking else None).generate()


@pytest.mark.parametrize(
    "testing",
    [
        [TestingBlockConfig(framework="pytest", mockup_sources=["fake_a.c"])],
        [TestingBlockConfig(framework="gtest", sources=["test_compA.cc"])],
        [],
    ],
    ids=["pytest-without-sources", "gtest-only", "no-tests"],
)
def test_component_without_pytest_sources_gets_only_its_object_library(tmp_path: Path, output_dir: Path, testing: list[TestingBlockConfig]) -> None:
    elements = PytestCMakeGenerator(make_execution_context(tmp_path, [comp_a_config(*testing)]), output_dir).generate()

    assert [library.target_name for library in find_elements_of_type(elements, CMakeAddLibrary)] == ["CompA_pytest_PC_lib"]
    assert find_elements_of_type(elements, CMakeCustomCommand) == []
    assert find_elements_of_type(elements, CMakeTargetLinkLibraries) == []


def test_component_without_sources_cannot_have_a_pytest_test_scope(tmp_path: Path, output_dir: Path) -> None:
    configs = [ComponentConfig(name="CompH", path=Path("compH"), testing=[TestingBlockConfig(framework="pytest", sources=["test_compH.py"])])]

    with pytest.raises(UserNotificationException, match="CompH") as error:
        PytestCMakeGenerator(make_execution_context(tmp_path, configs), output_dir).generate()
    assert "sources" in str(error.value)


def test_container_gets_nothing(tmp_path: Path, output_dir: Path) -> None:
    configs = [
        ComponentConfig(name="net", subcomponents=["tcp", "udp"]),
        ComponentConfig(name="tcp", path=Path("tcp"), sources=["tcp.c"], testing=[TestingBlockConfig(framework="pytest", sources=["test_tcp.py"])]),
        ComponentConfig(name="udp", path=Path("udp"), sources=["udp.c"]),
    ]

    elements = PytestCMakeGenerator(make_execution_context(tmp_path, configs, ["net"]), output_dir).generate()

    assert {library.target_name for library in find_elements_of_type(elements, CMakeAddLibrary)} == {"tcp_pytest_PC_lib", "udp_pytest_PC_lib", "tcp_pytest_lib"}
    assert not [command for command in find_elements_of_type(elements, CMakeCustomCommand) if "net_" in command.to_string()]


def test_no_element_uses_the_gtest_names(tmp_path: Path, output_dir: Path) -> None:
    elements = PytestCMakeGenerator(scopes_context(tmp_path), output_dir).generate()

    cmake_code = "\n".join(element.to_string() for element in elements)
    for name in ("CompA", "CompB", "IntegAB", "variant_test"):
        for gtest_name in (f"{name}_PC_lib", f"{name}_PC.o", f"{name}_mockup", f"mockup_{name}"):
            assert gtest_name not in cmake_code


SCOPES = pytest.mark.parametrize(
    ("name", "build_folder", "test_file", "object_libraries", "sources"),
    [
        ("CompA", "CompA", "compA/test_compA.py", ["CompA_pytest_PC_lib"], ["compA/compA.c"]),
        ("IntegAB", "IntegAB", "integ/test_integ.py", ["IntegAB_pytest_PC_lib"], ["compA/compA.c", "compB/compB.c"]),
        ("mock_variant", "variant_test", "test_variant.py", ["CompA_pytest_PC_lib", "CompB_pytest_PC_lib"], ["compA/compA.c", "compB/compB.c"]),
    ],
    ids=["component", "integration-component", "variant"],
)


def run_target(name: str) -> UserRequest:
    if name == "mock_variant":
        return UserRequest(UserRequestScope.VARIANT, target="variant_pytest_test")
    return UserRequest(UserRequestScope.COMPONENT, component_name=name, target="pytest_test")


def coverage_target(name: str) -> UserRequest:
    if name == "mock_variant":
        return UserRequest(UserRequestScope.VARIANT, target="variant_test_coverage")
    return UserRequest(UserRequestScope.COMPONENT, component_name=name, target=UserRequestTarget.COVERAGE)


@SCOPES
def test_test_scope_runs_pytest_on_its_test_library(
    tmp_path: Path, output_dir: Path, name: str, build_folder: str, test_file: str, object_libraries: list[str], sources: list[str]
) -> None:
    elements = PytestCMakeGenerator(scopes_context(tmp_path), output_dir).generate()

    build_dir = f"${{CMAKE_BUILD_DIR}}/{build_folder}"
    junit = f"{build_dir}/{name}_pytest_junit.xml"
    test_path = (tmp_path / test_file).as_posix()
    run = assert_element_of_type(elements, CMakeCustomCommand, lambda cmd: [str(output) for output in cmd.outputs or []] == [junit])
    [command] = run.commands
    gcov_prefix = f" GCOV_PREFIX={build_dir}/pytest_gcov" if name == "mock_variant" else ""
    assert " ".join([str(command.command), *(str(arg) for arg in command.arguments)]) == (
        f"${{CMAKE_COMMAND}} -E env PYTHONPATH={build_dir}{gcov_prefix} {Path(sys.executable).as_posix()} -m pytest -p no:cacheprovider"
        f" --junitxml={junit} {test_path} || ${{CMAKE_COMMAND}} -E true"
    )
    assert run.working_directory is not None
    assert run.working_directory.to_path() == tmp_path
    assert {f"{name}_pytest_lib", f"{build_dir}/{name}_binding.py", test_path} <= {Path(str(depend)).as_posix() for depend in run.depends or []}
    target = assert_element_of_type(elements, CMakeCustomTarget, lambda tgt: tgt.name == run_target(name).target_name)
    assert junit in [str(depend) for depend in target.depends or []]


@SCOPES
def test_test_scope_registers_its_junit_file_and_tracefile(
    tmp_path: Path, output_dir: Path, name: str, build_folder: str, test_file: str, object_libraries: list[str], sources: list[str]
) -> None:
    execution_context = scopes_context(tmp_path)

    elements = PytestCMakeGenerator(execution_context, output_dir).generate()

    build_dir = CMakeArtifactsLocator(output_dir, execution_context.spl_paths).cmake_build_dir.joinpath(build_folder)
    junit = build_dir.joinpath(f"{name}_pytest_junit.xml")
    tracefile = build_dir.joinpath(f"{name}_pytest_coverage.json")
    gcovr_config = build_dir.joinpath(f"{name}_pytest_gcovr.cfg")
    assert TestResultFile(target=run_target(name), junit_report=junit, framework="pytest", test_sources=[]) in execution_context.data_registry.find_data(TestResultFile)
    assert CoverageRelevantFile(target=coverage_target(name), json_report=tracefile, framework="pytest") in execution_context.data_registry.find_data(CoverageRelevantFile)

    command = assert_element_of_type(elements, CMakeCustomCommand, lambda cmd: str(tracefile) in [str(output) for output in cmd.outputs or []])
    assert [str(output) for output in command.outputs or []] == [str(gcovr_config), str(tracefile)]
    assert str(junit) in [str(depend) for depend in command.depends or []]
    config_command, gcovr_command = command.commands
    arguments = [str(arg) for arg in config_command.arguments]
    assert (str(config_command.command), arguments[0]) == ("yanga_cmd", "gcovr_config_component")
    assert {arg for arg in arguments if arg.startswith("$<TARGET_OBJECTS:")} == {f"$<TARGET_OBJECTS:{library}>" for library in object_libraries}
    assert {(tmp_path / source).as_posix() for source in sources} <= set(arguments)
    assert arguments[arguments.index("--output-file") + 1] == str(gcovr_config)
    if name == "mock_variant":
        assert arguments[arguments.index("--gcov-prefix") + 1] == f"{build_dir}/pytest_gcov"
    else:
        assert "--gcov-prefix" not in arguments
    assert [str(gcovr_command.command), *(str(arg) for arg in gcovr_command.arguments)][:6] == ["gcovr", "--config", str(gcovr_config), "--json", "--output", str(tracefile)]


def test_component_test_runs_gtest_and_pytest(tmp_path: Path, output_dir: Path) -> None:
    execution_context = make_execution_context(tmp_path, [comp_a_config(TestingBlockConfig(framework="gtest", sources=["test_compA.cc"]), pytest_block())])
    execution_context.data_registry.insert(ExternalProject(name="googletest", revision="v1.17.0", path=Path("ext/gtest/v1.17.0")), provider="WestInstall")

    elements = [
        *GTestCMakeGenerator(execution_context, output_dir).generate(),
        *PytestCMakeGenerator(execution_context, output_dir).generate(),
        *TestResultsCMakeGenerator(execution_context, output_dir).generate(),
    ]

    component_test = assert_element_of_type(elements, CMakeCustomTarget, lambda tgt: tgt.name == "CompA_test")
    assert {"CompA_gtest_test", "CompA_pytest_test"} <= {str(depend) for depend in component_test.depends or []}
    names = [target.name for target in find_elements_of_type(elements, CMakeCustomTarget)]
    assert len(names) == len(set(names))


def test_missing_pytest_is_an_error(tmp_path: Path, output_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    find_spec = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda name, *args: None if name == "pytest" else find_spec(name, *args))

    with pytest.raises(UserNotificationException, match="pytest"):
        PytestCMakeGenerator(make_execution_context(tmp_path, [comp_a_config(pytest_block())]), output_dir).generate()


@pytest.mark.parametrize(
    "variant_testing",
    [[], [TestingBlock(framework="gtest", sources=[Path("test_variant.cc")])], [TestingBlock(framework="pytest", mockup_sources=[Path("fake_os.c")])]],
    ids=["no-tests", "gtest-only", "pytest-without-sources"],
)
def test_variant_without_pytest_sources_gets_no_run_target(tmp_path: Path, output_dir: Path, variant_testing: list[TestingBlock]) -> None:
    execution_context = make_execution_context(tmp_path, [comp_a_config(pytest_block())])
    cast(Mock, execution_context).variant_testing = variant_testing

    elements = PytestCMakeGenerator(execution_context, output_dir).generate()

    names = {target.name for target in find_elements_of_type(elements, CMakeCustomTarget)}
    assert "CompA_pytest_test" in names
    assert "variant_pytest_test" not in names
    assert [entry.target.target_name for entry in execution_context.data_registry.find_data(TestResultFile)] == ["CompA_pytest_test"]
