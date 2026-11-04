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
    assert page.read_text() == (f"Test Report\n===========\n\n.. test-report:: light_controller test results\n   :id: TR_LIGHT_CONTROLLER\n   :file: {junit_report.as_posix()}\n")
    [registered] = execution_context.data_registry.find_data(ReportRelevantFiles)
    assert registered.file_type == ReportRelevantFileType.TEST_RESULT
    assert registered.target.target_name == "light_controller_test"
    assert registered.files_to_be_included == [page]
