from pathlib import Path

import pytest
from yanga_core.domain.config import ComponentConfig, TestingBlockConfig
from yanga_core.domain.execution_context import ExecutionContext, UserRequest, UserRequestScope
from yanga_core.domain.reports import ReportRelevantFiles, ReportRelevantFileType

from tests.conftest import make_execution_context
from tests.utils import find_elements_of_type
from yanga.cmake.cmake_backend import CMakeCustomTarget, CMakePath
from yanga.cmake.sphinx_test_report import SphinxTestReportCMakeGenerator, TestResultFile


def run_target(component_name: str | None, framework: str = "gtest") -> UserRequest:
    if component_name is None:
        return UserRequest(UserRequestScope.VARIANT, target=f"variant_{framework}_test")
    return UserRequest(UserRequestScope.COMPONENT, component_name=component_name, target=f"{framework}_test")


def junit_result(output_dir: Path, component_name: str | None, framework: str = "gtest") -> TestResultFile:
    name = component_name or "variant_test"
    junit_name = name if framework == "gtest" else f"{name}_{framework}"
    return TestResultFile(target=run_target(component_name, framework), junit_report=CMakePath(output_dir / name / f"{junit_name}_junit.xml"), framework=framework)


def register(execution_context: ExecutionContext, *results: TestResultFile) -> None:
    for result in results:
        execution_context.data_registry.insert(result, result.target.target_name)


def registered_entries(execution_context: ExecutionContext, target_name: str) -> list[ReportRelevantFiles]:
    return [entry for entry in execution_context.data_registry.find_data(ReportRelevantFiles) if entry.target.target_name == target_name]


def test_writes_and_registers_a_test_report_page(execution_context: ExecutionContext, output_dir: Path) -> None:
    register(execution_context, junit_result(output_dir, "light_controller"))

    SphinxTestReportCMakeGenerator(execution_context, output_dir).generate()

    page = output_dir / "light_controller" / "light_controller_test_report.rst"
    lines = page.read_text().splitlines()
    assert lines[:7] == ["Test Results", "============", "", "gtest", "-----", "", ".. test-report:: light_controller test results"]
    assert set(lines[7:]) == {"   :id: TR_LIGHT_CONTROLLER", "   :file: output/light_controller/light_controller_junit.xml", "   :collapse: false"}
    [registered] = registered_entries(execution_context, "light_controller_test")
    assert registered.file_type == ReportRelevantFileType.TEST_RESULT
    assert registered.target.target_name == "light_controller_test"
    assert registered.files_to_be_included == [page]


def test_names_the_page_of_a_variant_test_after_the_variant(execution_context: ExecutionContext, output_dir: Path) -> None:
    register(execution_context, junit_result(output_dir, None))

    SphinxTestReportCMakeGenerator(execution_context, output_dir).generate()

    page = output_dir / "variant_test" / "mock_variant_test_report.rst"
    lines = page.read_text().splitlines()
    assert lines[:7] == ["Test Results", "============", "", "gtest", "-----", "", ".. test-report:: mock_variant test results"]
    assert set(lines[7:]) == {"   :id: TR_MOCK_VARIANT", "   :file: output/variant_test/variant_test_junit.xml", "   :collapse: false"}
    [registered] = registered_entries(execution_context, "test")
    assert registered.files_to_be_included == [page]


@pytest.fixture
def unit_and_integration_context(tmp_path: Path) -> ExecutionContext:
    gtest = [TestingBlockConfig(framework="gtest", sources=["test.cc"])]
    configs = [
        ComponentConfig(name="CompA", path=Path("compA"), sources=["a.c"], testing=gtest),
        ComponentConfig(name="IntegA", path=Path("integ"), integrates=["CompA"], testing=gtest),
    ]
    return make_execution_context(tmp_path, configs)


@pytest.mark.parametrize(
    ("component_name", "entry_target_name", "expected_tags"),
    [
        ("CompA", "CompA_test", {"component", "CompA", "test", "gtest"}),
        ("IntegA", "IntegA_test", {"container", "IntegA", "test", "gtest"}),
        (None, "test", {"variant", "test", "gtest"}),
    ],
    ids=["unit", "integration", "variant-test"],
)
def test_test_report_page_is_tagged_with_its_level(
    unit_and_integration_context: ExecutionContext, output_dir: Path, component_name: str | None, entry_target_name: str, expected_tags: set[str]
) -> None:
    register(unit_and_integration_context, junit_result(output_dir, component_name))

    SphinxTestReportCMakeGenerator(unit_and_integration_context, output_dir).generate()

    [registered] = registered_entries(unit_and_integration_context, entry_target_name)
    assert set(registered.tags) == expected_tags


def light_controller_context(tmp_path: Path, frameworks: list[str]) -> ExecutionContext:
    testing = [TestingBlockConfig(framework=framework, sources=["test.cc"]) for framework in frameworks]
    return make_execution_context(tmp_path, [ComponentConfig(name="light_controller", path=Path("light_controller"), sources=["a.c"], testing=testing)])


def test_entry_page_has_one_section_per_framework_in_testing_order(tmp_path: Path, output_dir: Path) -> None:
    execution_context = light_controller_context(tmp_path, ["pytest", "gtest"])
    register(execution_context, junit_result(output_dir, "light_controller", "gtest"), junit_result(output_dir, "light_controller", "pytest"))

    SphinxTestReportCMakeGenerator(execution_context, output_dir).generate()

    [registered] = registered_entries(execution_context, "light_controller_test")
    [page] = registered.files_to_be_included
    assert page == output_dir / "light_controller" / "light_controller_test_report.rst"
    lines = page.read_text().splitlines()
    assert lines[:6] == ["Test Results", "============", "", "pytest", "------", ""]
    gtest_heading = lines.index("gtest")
    assert lines[gtest_heading + 1] == "-----"
    assert "   :id: TR_LIGHT_CONTROLLER__PYTEST" in lines[:gtest_heading]
    assert "   :id: TR_LIGHT_CONTROLLER" in lines[gtest_heading:]
    assert set(registered.tags) == {"component", "light_controller", "test", "gtest", "pytest"}


def test_gtest_only_page_keeps_its_id(tmp_path: Path, output_dir: Path) -> None:
    execution_context = light_controller_context(tmp_path, ["gtest"])
    register(execution_context, junit_result(output_dir, "light_controller", "gtest"))

    SphinxTestReportCMakeGenerator(execution_context, output_dir).generate()

    [registered] = registered_entries(execution_context, "light_controller_test")
    lines = registered.files_to_be_included[0].read_text().splitlines()
    assert [line for line in lines if line.startswith(".. test-report::")] == [".. test-report:: light_controller test results"]
    assert [line for line in lines if line.startswith("   :id: ")] == ["   :id: TR_LIGHT_CONTROLLER"]
    assert lines[3:5] == ["gtest", "-----"]


def test_unlisted_framework_comes_last(tmp_path: Path, output_dir: Path) -> None:
    execution_context = light_controller_context(tmp_path, ["pytest"])
    register(execution_context, junit_result(output_dir, "light_controller", "gtest"), junit_result(output_dir, "light_controller", "pytest"))

    SphinxTestReportCMakeGenerator(execution_context, output_dir).generate()

    [registered] = registered_entries(execution_context, "light_controller_test")
    lines = registered.files_to_be_included[0].read_text().splitlines()
    assert lines.index("pytest") < lines.index("gtest")


def register_test_results(execution_context: ExecutionContext, output_dir: Path, component_names: list[str], variant_test: bool) -> None:
    names: list[str | None] = [*component_names, *([None] if variant_test else [])]
    register(execution_context, *(junit_result(output_dir, name) for name in names))


def merged_test_report_context(tmp_path: Path, output_dir: Path) -> ExecutionContext:
    gtest = [TestingBlockConfig(framework="gtest", sources=["test.cc"])]
    configs = [
        ComponentConfig(name="CompA", path=Path("compA"), sources=["a.c"], testing=gtest),
        ComponentConfig(name="IntegA", path=Path("integ"), integrates=["CompA"], testing=gtest),
        ComponentConfig(name="net", subcomponents=["tcp"]),
        ComponentConfig(name="tcp", path=Path("tcp"), sources=["tcp.c"], testing=gtest),
    ]
    execution_context = make_execution_context(tmp_path, configs, ["CompA", "IntegA", "net"])
    register_test_results(execution_context, output_dir, ["CompA", "IntegA", "tcp"], variant_test=True)
    return execution_context


@pytest.mark.parametrize(
    ("target_name", "expected_tags", "listed_tests"),
    [
        ("net_test", {"container", "net", "test", "gtest"}, ["tcp"]),
        ("all_components_test", {"component", "merged", "test", "gtest"}, ["CompA", "tcp"]),
        ("all_containers_test", {"container", "merged", "test", "gtest"}, ["IntegA", "tcp"]),
        ("overall_test", {"overall", "test", "gtest"}, ["CompA", "IntegA", "tcp", "variant_test"]),
    ],
)
def test_merged_test_report_page_lists_the_junit_files_of_its_level(tmp_path: Path, output_dir: Path, target_name: str, expected_tags: set[str], listed_tests: list[str]) -> None:
    execution_context = merged_test_report_context(tmp_path, output_dir)

    elements = SphinxTestReportCMakeGenerator(execution_context, output_dir).generate()

    [registered] = [entry for entry in execution_context.data_registry.find_data(ReportRelevantFiles) if entry.target.target_name == target_name]
    assert set(registered.tags) == expected_tags
    assert registered.file_type == ReportRelevantFileType.TEST_RESULT
    [page] = registered.files_to_be_included
    lines = page.read_text().splitlines()
    assert lines[:2] == ["Test Results", "============"]
    assert not [line for line in lines if "test-results" in line]
    assert lines.count("gtest") == len(listed_tests)
    blocks = [lines[index + 1 : index + 4] for index, line in enumerate(lines) if line.startswith(".. test-report::")]
    assert sorted(option for block in blocks for option in block if option.startswith("   :file: ")) == [f"   :file: output/{name}/{name}_junit.xml" for name in listed_tests]
    assert all("   :collapse: false" in block and any(option.startswith("   :id: TR_") for option in block) for block in blocks)
    assert {"mock_variant" if name == "variant_test" else name for name in listed_tests} <= set(lines)
    targets = {target.name: {str(depend) for depend in target.depends or []} for target in find_elements_of_type(elements, CMakeCustomTarget)}
    if registered.target.scope == UserRequestScope.COMPONENT:
        assert page == output_dir / "net" / "net_test_report.rst"
        assert target_name not in targets
    else:
        assert targets[target_name] == {"variant_gtest_test" if name == "variant_test" else f"{name}_gtest_test" for name in listed_tests}


def test_merged_page_has_a_subsection_per_framework(tmp_path: Path, output_dir: Path) -> None:
    testing = [TestingBlockConfig(framework=framework, sources=["test.cc"]) for framework in ["gtest", "pytest"]]
    execution_context = make_execution_context(tmp_path, [ComponentConfig(name="CompA", path=Path("compA"), sources=["a.c"], testing=testing)])
    register(execution_context, junit_result(output_dir, "CompA", "gtest"), junit_result(output_dir, "CompA", "pytest"))

    elements = SphinxTestReportCMakeGenerator(execution_context, output_dir).generate()

    [registered] = registered_entries(execution_context, "all_components_test")
    lines = registered.files_to_be_included[0].read_text().splitlines()
    assert lines[:2] == ["Test Results", "============"]
    assert lines[lines.index("CompA") + 1] == "-----"
    for framework in ["gtest", "pytest"]:
        assert lines[lines.index(framework) + 1] == "~" * len(framework)
    assert {"   :id: TR_ALL_COMPONENTS__COMPA", "   :id: TR_ALL_COMPONENTS__COMPA__PYTEST"} <= set(lines)
    assert {"gtest", "pytest"} <= set(registered.tags)
    targets = {target.name: {str(depend) for depend in target.depends or []} for target in find_elements_of_type(elements, CMakeCustomTarget)}
    assert targets["all_components_test"] == {"CompA_gtest_test", "CompA_pytest_test"}


def test_test_report_ids_are_unique_over_all_pages(tmp_path: Path, output_dir: Path) -> None:
    execution_context = merged_test_report_context(tmp_path, output_dir)

    SphinxTestReportCMakeGenerator(execution_context, output_dir).generate()

    pages = [page for entry in execution_context.data_registry.find_data(ReportRelevantFiles) for page in entry.files_to_be_included]
    report_ids = [line for page in pages for line in page.read_text().splitlines() if line.startswith("   :id: ")]
    assert len(report_ids) == 4 + 1 + 2 + 2 + 4
    assert len(set(report_ids)) == len(report_ids)


def test_merged_page_report_ids_do_not_collide_with_a_component_page_id(tmp_path: Path, output_dir: Path) -> None:
    gtest = [TestingBlockConfig(framework="gtest", sources=["test.cc"])]
    configs = [
        ComponentConfig(name="app", subcomponents=["main"]),
        ComponentConfig(name="main", path=Path("main"), sources=["main.c"], testing=gtest),
        ComponentConfig(name="app_main", path=Path("app_main"), sources=["app_main.c"], testing=gtest),
    ]
    execution_context = make_execution_context(tmp_path, configs, ["app", "app_main"])
    register_test_results(execution_context, output_dir, ["main", "app_main"], variant_test=False)

    SphinxTestReportCMakeGenerator(execution_context, output_dir).generate()

    pages = [page for entry in execution_context.data_registry.find_data(ReportRelevantFiles) for page in entry.files_to_be_included]
    report_ids = [line for page in pages for line in page.read_text().splitlines() if line.startswith("   :id: ")]
    assert len(set(report_ids)) == len(report_ids)
    assert {"   :id: TR_APP_MAIN", "   :id: TR_APP__MAIN"} <= set(report_ids)


@pytest.mark.parametrize(
    ("component_names", "variant_test", "expected_targets"),
    [
        (["CompA"], False, {"CompA_test", "all_components_test", "overall_test"}),
        ([], True, {"test", "overall_test"}),
        ([], False, set()),
    ],
    ids=["no-containers-no-variant-test", "only-variant-test", "no-tests"],
)
def test_merged_test_report_page_is_left_out_for_an_empty_level(
    unit_and_integration_context: ExecutionContext, output_dir: Path, component_names: list[str], variant_test: bool, expected_targets: set[str]
) -> None:
    register_test_results(unit_and_integration_context, output_dir, component_names, variant_test)

    elements = SphinxTestReportCMakeGenerator(unit_and_integration_context, output_dir).generate()

    assert {entry.target.target_name for entry in unit_and_integration_context.data_registry.find_data(ReportRelevantFiles)} == expected_targets
    assert {target.name for target in find_elements_of_type(elements, CMakeCustomTarget)} == expected_targets - {"CompA_test", "test"}
