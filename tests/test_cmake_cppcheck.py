from pathlib import Path

import pytest
from yanga_core.domain.components import Component
from yanga_core.domain.config import ComponentConfig
from yanga_core.domain.execution_context import ExecutionContext
from yanga_core.domain.reports import ReportRelevantFiles

from tests.conftest import make_execution_context
from tests.utils import assert_element_of_type, assert_elements_of_type, find_elements_of_type
from yanga.cmake.cmake_backend import (
    CMakeCustomCommand,
    CMakeCustomTarget,
)
from yanga.cmake.cppcheck import CppCheckCMakeGenerator


@pytest.fixture
def create_executable_generator(execution_context: ExecutionContext, output_dir: Path) -> CppCheckCMakeGenerator:
    return CppCheckCMakeGenerator(execution_context, output_dir)


def test_generate(create_executable_generator: CppCheckCMakeGenerator) -> None:
    elements = create_executable_generator.generate()
    assert elements

    targets = assert_elements_of_type(elements, CMakeCustomTarget, 3)
    assert [target.name for target in targets] == [
        "lint",
        "CompA_lint",
        "CompBNotTestable_lint",
    ]


def test_create_variant_cmake_elements(
    create_executable_generator: CppCheckCMakeGenerator,
) -> None:
    elements = create_executable_generator.create_variant_cmake_elements()

    custom_target = assert_element_of_type(elements, CMakeCustomTarget)
    assert custom_target.name == "lint"


def test_create_components_cmake_elements(
    create_executable_generator: CppCheckCMakeGenerator,
) -> None:
    elements = create_executable_generator.create_components_cmake_elements()
    assert [target.name for target in find_elements_of_type(elements, CMakeCustomTarget)] == [
        "CompA_lint",
        "CompBNotTestable_lint",
    ]
    comp_cmd = assert_element_of_type(elements, CMakeCustomCommand, lambda cmd: "CompA" in cmd.description)
    assert [cmd.command for cmd in comp_cmd.commands] == ["yanga_cmd", "cppcheck", "yanga_cmd"]


def test_component_reports_are_tagged_as_component_static_analysis(create_executable_generator: CppCheckCMakeGenerator, execution_context: ExecutionContext) -> None:
    create_executable_generator.generate()

    assert [set(entry.tags) for entry in execution_context.data_registry.find_data(ReportRelevantFiles)] == [
        {"component", "CompA", "static-analysis"},
        {"component", "CompBNotTestable", "static-analysis"},
    ]


def test_component_without_sources_registers_no_report_and_no_lint_target(execution_context: ExecutionContext, output_dir: Path) -> None:
    execution_context.components.append(Component(name="net", path=execution_context.project_root_dir, subcomponents=list(execution_context.components)))

    elements = CppCheckCMakeGenerator(execution_context, output_dir).generate()

    assert [entry.target.target_name for entry in execution_context.data_registry.find_data(ReportRelevantFiles) if entry.target.component_name == "net"] == []
    assert "net_lint" not in [target.name for target in find_elements_of_type(elements, CMakeCustomTarget)]


def test_integration_component_report_is_tagged_as_container_static_analysis(tmp_path: Path, output_dir: Path) -> None:
    configs = [
        ComponentConfig(name="CompA", path=Path("compA"), sources=["a.c"]),
        ComponentConfig(name="IntegA", path=Path("integ"), sources=["glue.c"], integrates=["CompA"]),
    ]
    execution_context = make_execution_context(tmp_path, configs)

    CppCheckCMakeGenerator(execution_context, output_dir).generate()

    tags = {entry.target.component_name: set(entry.tags) for entry in execution_context.data_registry.find_data(ReportRelevantFiles)}
    assert tags == {"CompA": {"component", "CompA", "static-analysis"}, "IntegA": {"container", "IntegA", "static-analysis"}}
