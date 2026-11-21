from pathlib import Path

from yanga_core.domain.execution_context import ExecutionContext, UserRequest, UserRequestScope, UserRequestTarget
from yanga_core.domain.reports import ReportRelevantFiles, ReportRelevantFileType

from yanga.cmake.cmake_backend import CMakePath
from yanga.cmake.sphinx_test_report import SphinxTestReportCMakeGenerator, TestResultFile


def test_writes_and_registers_a_test_report_page(execution_context: ExecutionContext, output_dir: Path) -> None:
    target = UserRequest(UserRequestScope.COMPONENT, component_name="light_controller", target=UserRequestTarget.TEST)
    junit_report = output_dir / "light_controller" / "light_controller_junit.xml"
    execution_context.data_registry.insert(TestResultFile(target=target, junit_report=CMakePath(junit_report)), target.target_name)

    SphinxTestReportCMakeGenerator(execution_context, output_dir).generate()

    page = output_dir / "light_controller" / "light_controller_test_report.rst"
    lines = page.read_text().splitlines()
    assert lines[:4] == ["Test Report", "===========", "", ".. test-report:: light_controller test results"]
    assert set(lines[4:]) == {"   :id: TR_LIGHT_CONTROLLER", "   :file: output/light_controller/light_controller_junit.xml", "   :collapse: false"}
    [registered] = execution_context.data_registry.find_data(ReportRelevantFiles)
    assert registered.file_type == ReportRelevantFileType.TEST_RESULT
    assert registered.target.target_name == "light_controller_test"
    assert registered.files_to_be_included == [page]


def test_names_the_page_of_a_variant_test_after_the_variant(execution_context: ExecutionContext, output_dir: Path) -> None:
    target = UserRequest(UserRequestScope.VARIANT, target=UserRequestTarget.TEST)
    junit_report = output_dir / "variant_test" / "variant_test_junit.xml"
    execution_context.data_registry.insert(TestResultFile(target=target, junit_report=CMakePath(junit_report)), target.target_name)

    SphinxTestReportCMakeGenerator(execution_context, output_dir).generate()

    page = output_dir / "variant_test" / "mock_variant_test_report.rst"
    lines = page.read_text().splitlines()
    assert lines[:4] == ["Test Report", "===========", "", ".. test-report:: mock_variant test results"]
    assert set(lines[4:]) == {"   :id: TR_MOCK_VARIANT", "   :file: output/variant_test/variant_test_junit.xml", "   :collapse: false"}
    [registered] = execution_context.data_registry.find_data(ReportRelevantFiles)
    assert registered.target.target_name == "test"
    assert registered.files_to_be_included == [page]
