from pathlib import Path

import pytest
from yanga_core.domain.config import ComponentConfig, TestingBlockConfig
from yanga_core.domain.execution_context import ExecutionContext, UserRequest, UserRequestScope, UserRequestTarget
from yanga_core.domain.reports import ReportRelevantFiles, ReportRelevantFileType

from tests.conftest import make_execution_context
from tests.utils import assert_element_of_type, find_elements_of_type
from yanga.cmake.cmake_backend import CMakeAddTargetCleanFiles, CMakeCustomCommand, CMakeCustomTarget, CMakeElement, CMakePath
from yanga.cmake.coverage import CoverageRelevantFile
from yanga.cmake.reports import ReportCMakeGenerator
from yanga.cmake.sphinx_test_report import SphinxTestReportCMakeGenerator, TestResultFile
from yanga.cmake.test_results import TestResultsCMakeGenerator

VARIANT_COVERAGE = UserRequest(UserRequestScope.VARIANT, target="variant_test_coverage")


def block(framework: str) -> TestingBlockConfig:
    return TestingBlockConfig(framework=framework, sources=[f"test_{framework}"])


def config(name: str, *frameworks: str, integrates: list[str] | None = None) -> ComponentConfig:
    return ComponentConfig(name=name, path=Path(name), sources=[f"{name}.c"], testing=[block(framework) for framework in frameworks], integrates=integrates or [])


def register(execution_context: ExecutionContext, output_dir: Path, name: str | None, *frameworks: str) -> None:
    for framework in frameworks:
        if name is None:
            run_target = UserRequest(UserRequestScope.VARIANT, target=f"variant_{framework}_test")
            coverage_target = VARIANT_COVERAGE
        else:
            run_target = UserRequest(UserRequestScope.COMPONENT, component_name=name, target=f"{framework}_test")
            coverage_target = UserRequest(UserRequestScope.COMPONENT, component_name=name, target=UserRequestTarget.COVERAGE)
        directory = output_dir / (name or "variant_test")
        execution_context.data_registry.insert(
            TestResultFile(target=run_target, junit_report=CMakePath(directory / f"{framework}_junit.xml"), framework=framework), run_target.target_name
        )
        execution_context.data_registry.insert(
            CoverageRelevantFile(target=coverage_target, json_report=CMakePath(directory / f"{framework}_coverage.json"), framework=framework),
            f"{coverage_target.target_name}_{framework}",
        )


def tracefile(output_dir: Path, name: str, framework: str) -> str:
    return f"{output_dir.as_posix()}/{name}/{framework}_coverage.json"


def generate(execution_context: ExecutionContext, output_dir: Path) -> list[CMakeElement]:
    return TestResultsCMakeGenerator(execution_context, output_dir).generate()


def target_depends(elements: list[CMakeElement]) -> dict[str, list[str]]:
    return {target.name: [str(depend) for depend in target.depends or []] for target in find_elements_of_type(elements, CMakeCustomTarget)}


def merge_command(elements: list[CMakeElement], html_file: str) -> CMakeCustomCommand:
    return assert_element_of_type(elements, CMakeCustomCommand, lambda command: html_file in [str(output) for output in command.outputs or []])


def command_arguments(command: CMakeCustomCommand) -> list[str]:
    return [str(argument) for cmake_command in command.commands for argument in cmake_command.arguments]


def merged_tracefiles(command: CMakeCustomCommand) -> list[str]:
    arguments = command_arguments(command)
    return [arguments[index + 1] for index, argument in enumerate(arguments) if argument == "--add-tracefile"]


def coverage_entry(execution_context: ExecutionContext, target_name: str) -> ReportRelevantFiles:
    [entry] = [
        entry
        for entry in execution_context.data_registry.find_data(ReportRelevantFiles)
        if entry.target.target_name == target_name and entry.file_type == ReportRelevantFileType.COVERAGE_RESULT
    ]
    return entry


def coverage_page(link: str) -> str:
    return f"# Coverage\n\n## gcovr\n\n```{{toctree}}\n:maxdepth: 1\n\ngcovr report <{link}#http://>\n```"


def merged_context(tmp_path: Path, output_dir: Path) -> ExecutionContext:
    configs = [
        config("CompA", "gtest", "pytest"),
        config("IntegA", "gtest", integrates=["CompA"]),
        ComponentConfig(name="net", subcomponents=["tcp", "udp"]),
        config("tcp", "gtest"),
        config("udp"),
    ]
    execution_context = make_execution_context(tmp_path, configs, ["CompA", "IntegA", "net"])
    register(execution_context, output_dir, "CompA", "gtest", "pytest")
    register(execution_context, output_dir, "IntegA", "gtest")
    register(execution_context, output_dir, "tcp", "gtest")
    register(execution_context, output_dir, None, "gtest")
    return execution_context


def test_phony_test_targets_run_every_framework(tmp_path: Path, output_dir: Path) -> None:
    execution_context = make_execution_context(tmp_path, [config("CompA", "gtest", "pytest"), ComponentConfig(name="net", subcomponents=["CompA"])], ["net"])
    register(execution_context, output_dir, "CompA", "gtest", "pytest")
    register(execution_context, output_dir, None, "gtest")

    targets = target_depends(generate(execution_context, output_dir))

    assert targets["CompA_test"] == targets["CompA_build"] == ["CompA_gtest_test", "CompA_pytest_test"]
    assert targets["net_test"] == targets["net_build"] == ["CompA_test"]
    assert targets["test"] == ["variant_gtest_test"]


def test_component_report_runs_every_framework(tmp_path: Path, output_dir: Path) -> None:
    execution_context = make_execution_context(tmp_path, [config("CompA", "gtest", "pytest")])
    register(execution_context, output_dir, "CompA", "gtest", "pytest")
    html_file = "${CMAKE_BUILD_DIR}/CompA/reports/coverage/CompA/index.html"

    elements = generate(execution_context, output_dir)
    elements += SphinxTestReportCMakeGenerator(execution_context, output_dir).generate()
    elements += ReportCMakeGenerator(execution_context, output_dir).generate()

    targets = target_depends(elements)
    assert "CompA_results" in targets["CompA_report"]
    assert {"CompA_test", "CompA_coverage"} <= set(targets["CompA_results"])
    assert targets["CompA_test"] == ["CompA_gtest_test", "CompA_pytest_test"]
    assert merged_tracefiles(merge_command(elements, html_file)) == [tracefile(output_dir, "CompA", "gtest"), tracefile(output_dir, "CompA", "pytest")]


def test_container_without_tests_keeps_its_targets(tmp_path: Path, output_dir: Path) -> None:
    execution_context = make_execution_context(tmp_path, [config("CompA", "gtest"), config("udp"), ComponentConfig(name="net", subcomponents=["udp"])], ["CompA", "net"])
    register(execution_context, output_dir, "CompA", "gtest")

    targets = target_depends(generate(execution_context, output_dir))

    assert targets["net_test"] == targets["net_build"] == []


def test_component_coverage_merges_every_tracefile(tmp_path: Path, output_dir: Path) -> None:
    execution_context = make_execution_context(tmp_path, [config("CompA", "gtest", "pytest")])
    register(execution_context, output_dir, "CompA", "gtest", "pytest")
    html_file = "${CMAKE_BUILD_DIR}/CompA/reports/coverage/CompA/index.html"

    elements = generate(execution_context, output_dir)

    merge = merge_command(elements, html_file)
    arguments = command_arguments(merge)
    assert arguments[arguments.index("--root") + 1] == tmp_path.as_posix()
    assert merged_tracefiles(merge) == [tracefile(output_dir, "CompA", "gtest"), tracefile(output_dir, "CompA", "pytest")]
    assert arguments[arguments.index("--output") + 1] == html_file
    assert target_depends(elements)["CompA_coverage"] == [html_file]
    clean = assert_element_of_type(elements, CMakeAddTargetCleanFiles, lambda element: element.target == "CompA_coverage")
    assert [str(file) for file in clean.files] == [html_file.removesuffix("/index.html")]


def test_coverage_page_links_the_gcovr_html(tmp_path: Path, output_dir: Path) -> None:
    execution_context = make_execution_context(tmp_path, [config("CompA", "gtest", "pytest")])
    register(execution_context, output_dir, "CompA", "gtest", "pytest")

    generate(execution_context, output_dir)

    entry = coverage_entry(execution_context, "CompA_coverage")
    page = output_dir / "CompA" / "CompA_coverage.md"
    assert entry.files_to_be_included == [page]
    assert page.read_text().rstrip() == coverage_page("./coverage/CompA/index.html")
    assert entry.html_content is None
    assert set(entry.tags) == {"component", "CompA", "coverage", "gcovr", "gtest", "pytest"}


def test_variant_test_coverage_covers_every_framework(tmp_path: Path, output_dir: Path) -> None:
    execution_context = make_execution_context(tmp_path, [config("CompA")])
    register(execution_context, output_dir, None, "gtest", "pytest")
    html_file = "${CMAKE_BUILD_DIR}/reports/variant_test_coverage/index.html"

    elements = generate(execution_context, output_dir)

    assert merged_tracefiles(merge_command(elements, html_file)) == [tracefile(output_dir, "variant_test", "gtest"), tracefile(output_dir, "variant_test", "pytest")]
    assert target_depends(elements)["variant_test_coverage"] == [html_file]
    entry = coverage_entry(execution_context, "variant_test_coverage")
    assert entry.files_to_be_included == [output_dir / "variant_test_coverage.md"]
    assert (output_dir / "variant_test_coverage.md").read_text().rstrip() == coverage_page("./variant_test_coverage/index.html")
    assert set(entry.tags) == {"variant", "coverage", "gcovr", "gtest", "pytest"}


@pytest.mark.parametrize(
    ("target_name", "html_file", "page", "link", "tags", "tracefiles"),
    [
        (
            "coverage",
            "reports/coverage/index.html",
            "coverage.md",
            "./coverage/index.html",
            {"component", "merged", "coverage", "gcovr", "gtest", "pytest"},
            [("CompA", "gtest"), ("CompA", "pytest"), ("tcp", "gtest")],
        ),
        (
            "net_coverage",
            "net/reports/coverage/net/index.html",
            "net/net_coverage.md",
            "./coverage/net/index.html",
            {"container", "net", "coverage", "gcovr", "gtest"},
            [("tcp", "gtest")],
        ),
        (
            "all_containers_coverage",
            "reports/all_containers_coverage/index.html",
            "all_containers_coverage.md",
            "./all_containers_coverage/index.html",
            {"container", "merged", "coverage", "gcovr", "gtest"},
            [("IntegA", "gtest"), ("tcp", "gtest")],
        ),
        (
            "overall_coverage",
            "reports/overall_coverage/index.html",
            "overall_coverage.md",
            "./overall_coverage/index.html",
            {"overall", "coverage", "gcovr", "gtest", "pytest"},
            [("CompA", "gtest"), ("CompA", "pytest"), ("IntegA", "gtest"), ("tcp", "gtest"), ("variant_test", "gtest")],
        ),
    ],
)
def test_merged_coverage_reads_the_tracefiles_of_its_level(
    tmp_path: Path, output_dir: Path, target_name: str, html_file: str, page: str, link: str, tags: set[str], tracefiles: list[tuple[str, str]]
) -> None:
    execution_context = merged_context(tmp_path, output_dir)

    elements = generate(execution_context, output_dir)

    merge = merge_command(elements, f"${{CMAKE_BUILD_DIR}}/{html_file}")
    assert "--config" not in command_arguments(merge)
    assert sorted(merged_tracefiles(merge)) == sorted(tracefile(output_dir, name, framework) for name, framework in tracefiles)
    assert target_depends(elements)[target_name] == [f"${{CMAKE_BUILD_DIR}}/{html_file}"]
    entry = coverage_entry(execution_context, target_name)
    assert entry.files_to_be_included == [output_dir / page]
    assert (output_dir / page).read_text().rstrip() == coverage_page(link)
    assert entry.html_content is None
    assert set(entry.tags) == tags
    assert set(coverage_entry(execution_context, "IntegA_coverage").tags) == {"container", "IntegA", "coverage", "gcovr", "gtest"}


def test_component_in_nested_containers_counts_once_in_all_containers_coverage(tmp_path: Path, output_dir: Path) -> None:
    configs = [config("tcp", "gtest"), ComponentConfig(name="net", subcomponents=["tcp"]), ComponentConfig(name="group", subcomponents=["net"])]
    execution_context = make_execution_context(tmp_path, configs, ["group"])
    register(execution_context, output_dir, "tcp", "gtest")

    elements = generate(execution_context, output_dir)

    merge = merge_command(elements, "${CMAKE_BUILD_DIR}/reports/all_containers_coverage/index.html")
    assert merged_tracefiles(merge) == [tracefile(output_dir, "tcp", "gtest")]


@pytest.mark.parametrize("component_name", ["CompA", "net"])
def test_coverage_html_copy_depends_on_the_report_file(tmp_path: Path, output_dir: Path, component_name: str) -> None:
    execution_context = merged_context(tmp_path, output_dir)

    elements = generate(execution_context, output_dir)

    copy = assert_element_of_type(
        elements, CMakeCustomCommand, lambda command: command.description == f"Copy coverage html report for component {component_name} to variant report directory"
    )
    assert f"${{CMAKE_BUILD_DIR}}/{component_name}/reports/coverage/{component_name}/index.html" in [str(depend) for depend in copy.depends or []]


def test_no_tests_no_targets(execution_context: ExecutionContext, output_dir: Path) -> None:
    elements = generate(execution_context, output_dir)

    assert not find_elements_of_type(elements, CMakeCustomTarget)
    assert not find_elements_of_type(elements, CMakeCustomCommand)
    assert not list(execution_context.data_registry.find_data(ReportRelevantFiles))
