from argparse import ArgumentParser, Namespace
from pathlib import Path

import pytest
from yanga_core.domain.execution_context import UserRequest, UserRequestScope, UserRequestTarget
from yanga_core.domain.reports import ComponentReportData, ReportData, ReportRelevantFiles, ReportRelevantFileType

from yanga.commands.gcovr import CreateComponentGcovrConfigCommand, CreateVariantGcovrConfigCommand


def component(tmp_path: Path, name: str, file_type: ReportRelevantFileType) -> ComponentReportData:
    target = UserRequest(UserRequestScope.COMPONENT, variant_name="Disco", component_name=name, target=UserRequestTarget.COVERAGE)
    return ComponentReportData(files=[ReportRelevantFiles(target=target, file_type=file_type, files_to_be_included=[])], build_dir=tmp_path / name, name=name)


@pytest.mark.parametrize(
    ("file_type", "expected_lines"),
    [
        (ReportRelevantFileType.COVERAGE_RESULT, 2),
        (ReportRelevantFileType.SOURCES, 1),
    ],
    ids=["with-coverage", "without-coverage"],
)
def test_variant_config_lists_the_coverage_json_of_every_component_with_a_coverage_target(tmp_path: Path, file_type: ReportRelevantFileType, expected_lines: int) -> None:
    report_config = tmp_path / "report_config.json"
    ReportData(project_dir=tmp_path, components=[component(tmp_path, "spled", file_type)]).to_json_file(report_config)
    output_file = tmp_path / "gcovr.cfg"

    CreateVariantGcovrConfigCommand().run(Namespace(variant_report_config=report_config, output_file=output_file))

    lines = output_file.read_text().splitlines()
    assert lines[0] == f"root = {tmp_path.as_posix()}"
    assert len(lines) == expected_lines
    if expected_lines == 2:
        assert lines[1] == f"add-tracefile = {(tmp_path / 'spled' / 'coverage.json').as_posix()}"


@pytest.mark.parametrize("with_gcov_prefix", [True, False])
def test_component_config_reads_the_gcda_files_under_the_gcov_prefix(tmp_path: Path, with_gcov_prefix: bool) -> None:
    object_file = tmp_path / "CMakeFiles" / "x.dir" / "a.c.o"
    object_file.parent.mkdir(parents=True)
    object_file.write_text("object")
    gcno_file = object_file.with_suffix(".gcno")
    gcno_file.write_text("notes")
    gcov_prefix = tmp_path / "gcov"
    output_file = tmp_path / "gcovr.cfg"
    command = CreateComponentGcovrConfigCommand()
    command.register_parser(ArgumentParser().add_subparsers())
    argv = ["--component-objects", str(object_file), "--source-files", str(tmp_path / "a.c"), "--project-dir", str(tmp_path), "--output-file", str(output_file)]

    command.run(command.parser.parse_args(argv + ["--gcov-prefix", str(gcov_prefix)] * with_gcov_prefix))

    resolved_gcno = gcno_file.resolve()
    copied_gcno = gcov_prefix / resolved_gcno.relative_to(resolved_gcno.anchor)
    lines = output_file.read_text().splitlines()
    assert f"root = {tmp_path.as_posix()}" in lines
    object_directory = (gcov_prefix if with_gcov_prefix else object_file.parent).as_posix()
    assert f"search-path = {object_directory}" in lines
    assert f"gcov-object-directory = {object_directory}" in lines
    assert copied_gcno.exists() == with_gcov_prefix
    if with_gcov_prefix:
        assert copied_gcno.read_text() == "notes"
