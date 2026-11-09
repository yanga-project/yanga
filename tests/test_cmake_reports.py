from pathlib import Path

import pytest
from yanga_core.domain.component_resolver import ComponentResolver
from yanga_core.domain.config import ComponentConfig, DocsConfig
from yanga_core.domain.execution_context import ExecutionContext
from yanga_core.domain.publish_manifest import PublishedFile, PublishKind
from yanga_core.domain.reports import ReportRelevantFiles, ReportRelevantFileType

from tests.utils import assert_element_of_type, assert_elements_of_type, find_elements_of_type
from yanga.cmake.cmake_backend import (
    CMakeAddTargetCleanFiles,
    CMakeCustomTarget,
)
from yanga.cmake.reports import ReportCMakeGenerator


@pytest.fixture
def create_executable_generator(execution_context: ExecutionContext, output_dir: Path) -> ReportCMakeGenerator:
    return ReportCMakeGenerator(execution_context, output_dir)


def test_generate(create_executable_generator: ReportCMakeGenerator) -> None:
    elements = create_executable_generator.generate()
    assert elements

    targets = assert_elements_of_type(elements, CMakeCustomTarget, 8)
    assert {target.name for target in targets} == {
        "CompA_docs",
        "CompA_results",
        "CompA_report",
        "CompBNotTestable_docs",
        "CompBNotTestable_results",
        "CompBNotTestable_report",
        "results",
        "report",
    }


def test_create_variant_cmake_elements(
    create_executable_generator: ReportCMakeGenerator,
) -> None:
    elements = create_executable_generator.create_variant_cmake_elements()

    custom_targets = assert_elements_of_type(elements, CMakeCustomTarget, 2)
    assert {target.name for target in custom_targets} == {"report", "results"}


def test_create_components_cmake_elements(
    create_executable_generator: ReportCMakeGenerator,
) -> None:
    elements = create_executable_generator.create_components_cmake_elements()
    assert {target.name for target in find_elements_of_type(elements, CMakeCustomTarget)} == {
        "CompA_docs",
        "CompA_report",
        "CompA_results",
        "CompBNotTestable_docs",
        "CompBNotTestable_report",
        "CompBNotTestable_results",
    }
    comp_cmd = assert_element_of_type(elements, CMakeCustomTarget, lambda target: target.name == "CompA_docs")
    assert [cmd.command for cmd in comp_cmd.commands] == ["clanguru"]
    comp_cmd = assert_element_of_type(elements, CMakeCustomTarget, lambda target: target.name == "CompA_report")
    assert [cmd.command for cmd in comp_cmd.commands] == ["${CMAKE_COMMAND}", "yanga_cmd", "${CMAKE_COMMAND}", "yanga_cmd"]


def test_report_targets_register_clean_files(create_executable_generator: ReportCMakeGenerator) -> None:
    elements = create_executable_generator.generate()

    clean_files = find_elements_of_type(elements, CMakeAddTargetCleanFiles)
    by_target = {entry.target: entry for entry in clean_files}

    for target_name in ("report", "CompA_report", "CompBNotTestable_report"):
        assert target_name in by_target, f"{target_name} must register its report dir for clean"
        paths = [str(file) for file in by_target[target_name].files]
        assert paths, f"{target_name} clean files should not be empty"


def test_exclude_productive_code(execution_context: ExecutionContext, output_dir: Path) -> None:
    configs = [
        ComponentConfig(name="CompA", path=Path("compA"), sources=["compA_source.cpp"], docs=DocsConfig(sources=["index.md"], exclude_productive_code=True)),
        ComponentConfig(name="CompB", path=Path("compB"), sources=["compB_source.cpp"], docs=DocsConfig(sources=["index.md"], exclude_productive_code=False)),
    ]
    # Override the mock's read-only components with resolved components for this test.
    execution_context.components = ComponentResolver(configs, [config.name for config in configs], execution_context.spl_paths).selected_components  # type: ignore[misc]

    gen = ReportCMakeGenerator(execution_context, output_dir)
    elements = gen.create_components_cmake_elements()

    assert {t.name for t in find_elements_of_type(elements, CMakeCustomTarget)} == {"CompA_docs", "CompA_results", "CompA_report", "CompB_results", "CompB_report", "CompB_docs"}
    assert assert_element_of_type(elements, CMakeCustomTarget, lambda target: target.name == "CompA_docs").commands == []
    # Only component B SOURCES shall be reported as relevant for the report
    report_relevant_files = execution_context.data_registry.find_data(ReportRelevantFiles)
    assert_elements_of_type(
        report_relevant_files, ReportRelevantFiles, 1, lambda elem: elem.file_type == ReportRelevantFileType.SOURCES and elem.target.target_name == "CompB_docs"
    )


def test_variant_report_is_registered_for_the_manifest(create_executable_generator: ReportCMakeGenerator, execution_context: ExecutionContext, output_dir: Path) -> None:
    create_executable_generator.generate()

    assert execution_context.data_registry.find_data(PublishedFile) == [PublishedFile(PublishKind.REPORT, "Variant report", output_dir / "reports/index.html")]


def test_source_pages_are_grouped_under_a_sources_page(execution_context: ExecutionContext, output_dir: Path) -> None:
    configs = [ComponentConfig(name="CompB", path=Path("compB"), sources=["compB_source.cpp"])]
    execution_context.components = ComponentResolver(configs, ["CompB"], execution_context.spl_paths).selected_components  # type: ignore[misc]

    ReportCMakeGenerator(execution_context, output_dir).create_components_cmake_elements()

    entry = assert_element_of_type(
        execution_context.data_registry.find_data(ReportRelevantFiles), ReportRelevantFiles, lambda elem: elem.file_type == ReportRelevantFileType.SOURCES
    )
    assert [file.name for file in entry.files_to_be_included] == ["sources.md"]
    assert [file.name for file in entry.all_files] == ["compB_source.cpp.md"]
    assert entry.files_to_be_included[0].read_text() == "# Sources\n\n```{toctree}\n:maxdepth: 1\n\ncompB_source.cpp.md\n```\n"
