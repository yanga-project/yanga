from pathlib import Path
from typing import Any

import pytest
from mashumaro.exceptions import InvalidFieldValue, MissingField
from pypeline_semantic_release.check_ci_context import CIContext, CISystem
from yanga_core.domain.component_resolver import ComponentResolver
from yanga_core.domain.config import ComponentConfig, DocsConfig
from yanga_core.domain.execution_context import ExecutionContext, UserRequest, UserRequestScope, UserRequestTarget
from yanga_core.domain.publish_manifest import PublishedFile, PublishKind
from yanga_core.domain.reports import ReportRelevantFiles, ReportRelevantFileType

from tests.utils import assert_element_of_type, assert_elements_of_type, find_elements_of_type
from yanga.cmake.artifacts_locator import CMakeArtifactsLocator
from yanga.cmake.cmake_backend import (
    CMakeAddTargetCleanFiles,
    CMakeCustomTarget,
    CMakePath,
)
from yanga.cmake.reports import ReportCMakeGenerator
from yanga.cmake.sphinx_test_report import TestResultFile


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


def make_generator(execution_context: ExecutionContext, output_dir: Path, config: dict[str, Any] | None) -> ReportCMakeGenerator:
    return ReportCMakeGenerator(execution_context, output_dir, config)


def register_comp_a_test_result(execution_context: ExecutionContext, output_dir: Path) -> None:
    target = UserRequest(UserRequestScope.COMPONENT, component_name="CompA", target=UserRequestTarget.TEST)
    junit_report = CMakeArtifactsLocator(output_dir, execution_context.spl_paths).get_component_build_dir("CompA").joinpath("CompA_junit.xml")
    execution_context.data_registry.insert(TestResultFile(target=target, junit_report=junit_report), target.target_name)


def find_target(elements: list[Any], name: str) -> CMakeCustomTarget:
    return assert_element_of_type(elements, CMakeCustomTarget, lambda target: target.name == name)


@pytest.mark.parametrize("config", [{"source_links": False}, {"resolvers": {"default": ["gcovr"]}}])
def test_source_links_off_writes_same_cmake(execution_context: ExecutionContext, output_dir: Path, config: dict[str, Any]) -> None:
    expected = "\n".join(str(element) for element in make_generator(execution_context, output_dir, None).generate())

    assert "\n".join(str(element) for element in make_generator(execution_context, output_dir, config).generate()) == expected


def test_source_links_on_adds_clanguru_flags(execution_context: ExecutionContext, output_dir: Path) -> None:
    register_comp_a_test_result(execution_context, output_dir)

    elements = make_generator(execution_context, output_dir, {"source_links": True}).generate()

    commands = [cmd for cmd in find_target(elements, "CompA_docs").commands if cmd.command == "clanguru"]
    assert len(commands) == 2
    for cmd in commands:
        arguments = [str(arg) for arg in cmd.arguments]
        assert "--source-links" in arguments
        assert arguments[arguments.index("--project-root") + 1] == str(CMakePath(execution_context.project_root_dir))


def test_source_links_without_resolvers_runs_no_resolver(execution_context: ExecutionContext, output_dir: Path) -> None:
    elements = make_generator(execution_context, output_dir, {"source_links": True}).generate()

    for name in ("CompA_report", "report"):
        assert not [cmd for cmd in find_target(elements, name).commands if "resolve_source_links" in [str(arg) for arg in cmd.arguments]]


@pytest.mark.parametrize(
    ("resolvers", "ci_system", "expected_strategies"),
    [
        ({"default": ["gcovr"], "local": ["gcovr", "vscode"]}, None, ["gcovr", "vscode"]),
        ({"default": ["gcovr"], "local": ["gcovr", "vscode"]}, CISystem.UNKNOWN, ["gcovr", "vscode"]),
        ({"default": ["gcovr"], "local": ["gcovr", "vscode"]}, CISystem.GITHUB_ACTIONS, ["gcovr"]),
        ({"default": ["gcovr"], "ci": ["vscode"]}, CISystem.JENKINS, ["vscode"]),
    ],
)
def test_resolver_profile(
    execution_context: ExecutionContext, output_dir: Path, resolvers: dict[str, list[str]], ci_system: CISystem | None, expected_strategies: list[str]
) -> None:
    if ci_system is not None:
        execution_context.data_registry.insert(CIContext(ci_system, False, None, None), "test")
    locator = CMakeArtifactsLocator(output_dir, execution_context.spl_paths)

    elements = make_generator(execution_context, output_dir, {"source_links": True, "resolvers": resolvers}).generate()

    for name, report_dir in (("CompA_report", locator.get_component_reports_dir("CompA")), ("report", locator.cmake_variant_reports_dir)):
        last = find_target(elements, name).commands[-1]
        assert last.command == "yanga_cmd"
        assert [str(arg) for arg in last.arguments] == [
            "resolve_source_links",
            "--report-dir",
            str(report_dir),
            "--project-root",
            str(CMakePath(execution_context.project_root_dir)),
            "--strategies",
            *expected_strategies,
        ]


def test_resolvers_need_default(execution_context: ExecutionContext, output_dir: Path) -> None:
    with pytest.raises(InvalidFieldValue) as exc_info:
        make_generator(execution_context, output_dir, {"resolvers": {"local": ["vscode"]}}).generate()
    # mashumaro wraps the nested MissingField in InvalidFieldValue
    assert isinstance(exc_info.value.__context__, MissingField)
    assert exc_info.value.__context__.field_name == "default"
