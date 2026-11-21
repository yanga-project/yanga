"""
clang-tidy lint reports.

Add the generator to one platform, ideally the test platform; `lint` and `<component>_lint` then write an HTML report (`index.html`) and `clang_tidy_report.sarif` for the reports:

    generators:
      - step: ClangTidyCMakeGenerator
        module: yanga.cmake.clang_tidy
"""

import html
import json
import re
from argparse import Namespace
from collections.abc import Callable
from pathlib import Path

import jsonschema
import pytest
from clanguru.compilation_options_manager import CompileCommand
from yanga_core.domain.config import ComponentConfig
from yanga_core.domain.execution_context import ExecutionContext
from yanga_core.domain.reports import ReportRelevantFiles, ReportRelevantFileType

from tests.conftest import make_execution_context
from tests.utils import find_elements_of_type
from yanga.cmake.artifacts_locator import CMakeArtifactsLocator
from yanga.cmake.clang_tidy import ClangTidyCMakeGenerator
from yanga.cmake.cmake_backend import CMakeCustomCommand, CMakeCustomTarget, CMakePath
from yanga.commands.clang_tidy import ClangCompileCommandsCommand, ClangTidyReportCommand, header_filter, parse_clang_tidy_output, to_clang_compile_command

CLANG_TIDY_OUTPUT = r"""C:\work\src\main.c:12:5: warning: Dereference of null pointer [clang-analyzer-core.NullDereference]
   12 |     *ptr = 1;
      |     ^
C:\work\src\main.c:10:5: note: 'ptr' initialized to a null pointer value
/work/src/led.c:3:1: error: unknown type name 'foo' [clang-diagnostic-error]
2 warnings generated.
"""


def test_parse_keeps_warnings_and_errors_and_drops_notes() -> None:
    errors = parse_clang_tidy_output(CLANG_TIDY_OUTPUT).errors

    assert [(error.id, error.severity, error.locations[0].file, error.locations[0].line) for error in errors] == [
        ("clang-analyzer-core.NullDereference", "warning", Path(r"C:\work\src\main.c"), 12),
        ("clang-diagnostic-error", "error", Path("/work/src/led.c"), 3),
    ]


TEMPLATE_MESSAGE = "template argument std::vector<int> & x > y is unused"


def write_project_outputs(project_dir: Path) -> list[Path]:
    """Two source outputs that both report the same header finding, one finding outside the project and one parse failure."""
    header_finding = f"{project_dir / 'comp/include/vec.h'}:7:3: warning: header finding [yanga-test-unknown-check]"
    main_output = f"""{project_dir / "comp/src/main.c"}:271:9: warning: 42 is a magic number [readability-magic-numbers]
{project_dir / "comp/src/main.c"}:280:5: warning: {TEMPLATE_MESSAGE} [yanga-test-unknown-check]
{header_finding}
{Path("/opt/vendor/ext.h")}:4:1: warning: 7 is a magic number [readability-magic-numbers]
{project_dir / "comp/src/led.c"}:3:1: error: unknown type name 'foo' [clang-diagnostic-error]
"""
    util_output = f"""{project_dir / "comp/src/util.c"}:5:9: warning: 5 is a magic number [readability-magic-numbers]
{project_dir / "comp/src/util.c"}:6:9: warning: 6 is a magic number [readability-magic-numbers]
{header_finding}
"""
    input_files = [project_dir / "main.c.txt", project_dir / "util.c.txt"]
    for input_file, output in zip(input_files, [main_output, util_output], strict=True):
        input_file.write_text(output)
    return input_files


def run_report(input_files: list[Path], output_dir: Path, project_dir: Path) -> Path:
    ClangTidyReportCommand().run(Namespace(input_files=input_files, output_dir=output_dir, project_dir=project_dir))
    return output_dir


def visible_text(page: str) -> str:
    page = re.sub(r"<(script|style)\b.*?</\1>", " ", page, flags=re.DOTALL | re.IGNORECASE)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", page)).split())


@pytest.mark.parametrize(("check", "severity"), [("readability-magic-numbers", "STYLE"), ("yanga-test-unknown-check", "MEDIUM")])
def test_severity_from_codechecker_table_and_medium_for_unknown_checks(check: str, severity: str) -> None:
    from yanga.commands.clang_tidy import severity_of

    assert severity_of(check) == severity


def test_report_writes_valid_sarif_with_findings_once_and_parse_failures_as_errors(tmp_path: Path, get_test_data_path: Callable[[str], Path]) -> None:
    input_files = write_project_outputs(tmp_path)
    input_files.append(tmp_path / "sample.txt")
    input_files[-1].write_text(CLANG_TIDY_OUTPUT)

    sarif = json.loads((run_report(input_files, tmp_path / "report", tmp_path) / "clang_tidy_report.sarif").read_text())

    jsonschema.validate(sarif, json.loads(get_test_data_path("sarif-schema-2.1.0.json").read_text()))
    results = sarif["runs"][0]["results"]
    [magic_number] = [result for result in results if result["message"]["text"] == "42 is a magic number"]
    location = magic_number["locations"][0]["physicalLocation"]
    assert magic_number["ruleId"] == "readability-magic-numbers"
    assert location["artifactLocation"] == {"uri": "comp/src/main.c", "uriBaseId": "PROJECTROOT"}
    assert sarif["runs"][0]["originalUriBaseIds"]["PROJECTROOT"]["uri"] == tmp_path.as_uri() + "/"
    [outside] = [result for result in results if result["message"]["text"] == "7 is a magic number"]
    assert outside["locations"][0]["physicalLocation"]["artifactLocation"] == {"uri": Path("/opt/vendor/ext.h").absolute().as_uri()}
    assert location["region"]["startLine"] == 271
    assert magic_number["level"] == "warning"
    assert magic_number["properties"]["severity"] == "STYLE"
    assert [result["message"]["text"] for result in results].count("header finding") == 1
    assert {result["level"] for result in results if result["ruleId"] == "clang-diagnostic-error"} == {"error"}
    assert all(result["properties"]["severity"] in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "STYLE"} for result in results if result["level"] == "warning")


@pytest.mark.parametrize(
    ("name", "counts"),
    [
        ("comp", "0 0 2 0 3"),
        ("src", "0 0 1 0 3"),
        ("main.c", "0 0 1 0 1"),
        ("util.c", "0 0 0 0 2"),
        ("vec.h", "0 0 1 0 0"),
        ("ext.h", "0 0 0 0 1"),
    ],
)
def test_report_tree_counts_findings_per_severity_for_each_folder_and_file(tmp_path: Path, name: str, counts: str) -> None:
    output_dir = run_report(write_project_outputs(tmp_path), tmp_path / "report", tmp_path)

    index = (output_dir / "index.html").read_text()
    assert 'id="file-tree"' in index
    assert re.search(r"CRITICAL\s+HIGH\s+MEDIUM\s+LOW\s+STYLE", visible_text(index), re.IGNORECASE)
    counts_pattern = r"\s+".join(counts.split())
    row = re.compile(rf"(^|[\s/]){re.escape(name)}\s+{counts_pattern}(\s|$)")
    assert any(row.search(visible_text(page.read_text())) for page in output_dir.rglob("*.html"))


def test_report_file_page_lists_findings_escaped_and_parse_failures_apart(tmp_path: Path) -> None:
    output_dir = run_report(write_project_outputs(tmp_path), tmp_path / "report", tmp_path)

    pages = {page: page.read_text() for page in output_dir.rglob("*.html")}
    [file_page] = [page for page, content in pages.items() if "42 is a magic number" in content]
    assert file_page.name != "index.html"
    text = visible_text(pages[file_page])
    assert all(value in text for value in ["271", "readability-magic-numbers", "STYLE", "42 is a magic number"])
    assert "std::vector&lt;int&gt; &amp; x &gt; y" in pages[file_page]
    assert not any(TEMPLATE_MESSAGE in content for content in pages.values())
    index = visible_text(pages[output_dir / "index.html"])
    assert "Parse failures" in index
    assert "unknown type name 'foo'" in index


def test_report_pages_drop_gcovr_branding_and_copied_assets_keep_its_licence_notice(tmp_path: Path) -> None:
    output_dir = run_report(write_project_outputs(tmp_path), tmp_path / "report", tmp_path)

    for page in output_dir.rglob("*.html"):
        content = page.read_text()
        assert 'id="file-tree"' in content
        assert all(branding not in content for branding in ["boost-wordmark", "Created using", 'id="view-toggle"'])
    for asset in ["style.css", "gcovr.js"]:
        notice = re.match(r"\s*(/\*.*?\*/|(//[^\n]*\n)+)", (output_dir / asset).read_text(), re.DOTALL)
        assert notice, asset
        assert "gcovr authors" in notice[0]
        assert "BSD-3-Clause" in notice[0]


def test_report_without_findings_still_renders(tmp_path: Path) -> None:
    input_file = tmp_path / "main.c.txt"
    input_file.write_text("No warnings.\n")

    output_dir = run_report([input_file], tmp_path / "report", tmp_path)

    assert 'id="file-tree"' in (output_dir / "index.html").read_text()
    assert json.loads((output_dir / "clang_tidy_report.sarif").read_text())["runs"][0]["results"] == []


def test_clang_compile_command_keeps_only_parse_flags() -> None:
    command = CompileCommand(
        directory=Path("/build"),
        file=Path("/src/main.c"),
        command="/usr/bin/gcc -DSPLE_TESTABLE_STATIC= -I/src/inc -isystem /sys -std=gnu11 -fcondition-coverage -Wall -o main.o -c /src/main.c",
    )

    assert to_clang_compile_command(command).arguments == [
        str(Path("/usr/bin/gcc")),
        "-DSPLE_TESTABLE_STATIC=",
        "-I/src/inc",
        "-isystem",
        "/sys",
        "-std=gnu11",
        "-c",
        str(Path("/src/main.c")),
    ]


def test_clang_compile_commands_command_writes_database(tmp_path: Path) -> None:
    database = tmp_path / "compile_commands.json"
    database.write_text(json.dumps([{"directory": "/build", "file": "/src/main.c", "command": "gcc -fcondition-coverage -c /src/main.c"}]))
    output_file = tmp_path / "clang_tidy" / "compile_commands.json"

    ClangCompileCommandsCommand().run(Namespace(compilation_database=database, output_file=output_file))

    assert json.loads(output_file.read_text())[0]["arguments"] == ["gcc", "-c", str(Path("/src/main.c"))]


@pytest.mark.parametrize(
    ("header", "matches"),
    [
        ("/work/comp/include/led.h", True),
        (r"\work\comp\include\led.h", True),
        ("/work/other/inc/x.h", True),
        ("/work/comp/include_gen/x.h", False),
        ("/usr/include/stdio.h", False),
    ],
)
def test_header_filter_matches_include_directories_with_both_separators(header: str, matches: bool) -> None:
    pattern = header_filter([Path("/work/comp/include"), Path("/work/other/inc")])

    assert bool(re.search(pattern, header)) == matches


@pytest.mark.parametrize(
    ("context_fixture", "expected_targets", "expected_tidy_commands"),
    [
        ("execution_context", ["CompA_lint", "CompBNotTestable_lint", "lint"], 2),
        ("container_execution_context", ["tcp_lint", "udp_lint", "lint"], 2),
    ],
    ids=["components", "containers-without-sources-skipped"],
)
def test_generate_one_clang_tidy_step_per_source(
    request: pytest.FixtureRequest, context_fixture: str, expected_targets: list[str], expected_tidy_commands: int, output_dir: Path
) -> None:
    execution_context: ExecutionContext = request.getfixturevalue(context_fixture)
    elements = ClangTidyCMakeGenerator(execution_context, output_dir).generate()

    assert [target.name for target in find_elements_of_type(elements, CMakeCustomTarget)] == expected_targets
    tidy_commands = [command for command in find_elements_of_type(elements, CMakeCustomCommand) if command.commands[0].arguments[0] == "clang_tidy"]
    assert len(tidy_commands) == expected_tidy_commands
    assert all(len(command.depends or []) == 2 for command in tidy_commands)


@pytest.mark.parametrize(
    ("test_net_sources", "expected_targets", "expected_descriptions"),
    [
        ([], ["tcp_lint", "udp_lint", "lint"], ["Run clang-tidy for tcp tcp.cpp", "Run clang-tidy for udp udp.cpp"]),
        (
            ["glue.cpp"],
            ["tcp_lint", "udp_lint", "test_net_lint", "lint"],
            ["Run clang-tidy for tcp tcp.cpp", "Run clang-tidy for udp udp.cpp", "Run clang-tidy for test_net glue.cpp"],
        ),
    ],
    ids=["integration-without-own-sources-skipped", "integration-analysed-for-own-sources-only"],
)
def test_generate_clang_tidy_steps_only_for_own_sources(
    tmp_path: Path, test_net_sources: list[str], expected_targets: list[str], expected_descriptions: list[str], output_dir: Path
) -> None:
    configs = [
        ComponentConfig(name="tcp", path=Path("tcp"), sources=["tcp.cpp"]),
        ComponentConfig(name="udp", path=Path("udp"), sources=["udp.cpp"]),
        ComponentConfig(name="test_net", path=Path("itest"), sources=test_net_sources, integrates=["tcp", "udp"]),
    ]
    elements = ClangTidyCMakeGenerator(make_execution_context(tmp_path, configs), output_dir).generate()

    assert [target.name for target in find_elements_of_type(elements, CMakeCustomTarget)] == expected_targets
    tidy_commands = [command for command in find_elements_of_type(elements, CMakeCustomCommand) if command.commands[0].arguments[0] == "clang_tidy"]
    assert [command.description for command in tidy_commands] == expected_descriptions


def test_clang_tidy_steps_rerun_when_project_config_changes(execution_context: ExecutionContext, output_dir: Path) -> None:
    config_file = execution_context.project_root_dir / ".clang-tidy"
    config_file.write_text("Checks: 'bugprone-*'\n")

    elements = ClangTidyCMakeGenerator(execution_context, output_dir).generate()

    tidy_commands = [command for command in find_elements_of_type(elements, CMakeCustomCommand) if command.commands[0].arguments[0] == "clang_tidy"]
    assert all(str(CMakePath(config_file)) in [str(dependency) for dependency in command.depends or []] for command in tidy_commands)


def test_generator_registers_html_report_for_each_component_and_the_variant(execution_context: ExecutionContext, output_dir: Path) -> None:
    elements = ClangTidyCMakeGenerator(execution_context, output_dir).generate()

    locator = CMakeArtifactsLocator(output_dir, execution_context.spl_paths)
    registered = execution_context.data_registry.find_data(ReportRelevantFiles)
    assert {entry.target.target_name for entry in registered} == {"CompA_lint", "CompBNotTestable_lint", "lint"}
    assert all(entry.file_type == ReportRelevantFileType.HTML and entry.html_content for entry in registered)
    index_files = {
        (locator.get_component_reports_dir(entry.target.component_name) if entry.target.component_name else locator.cmake_variant_reports_dir).to_path()
        / entry.html_content.index_html
        for entry in registered
        if entry.html_content
    }
    report_arguments = [command.commands[0].arguments for command in find_elements_of_type(elements, CMakeCustomCommand) if command.commands[0].arguments[0] == "clang_tidy_report"]
    assert "--output-file" not in [str(argument) for arguments in report_arguments for argument in arguments]
    output_dirs = [arguments[arguments.index("--output-dir") + 1] for arguments in report_arguments]
    assert index_files == {directory.to_path() / "index.html" for directory in output_dirs if isinstance(directory, CMakePath)}


def test_component_report_is_written_and_registered_under_its_own_folder(execution_context: ExecutionContext, output_dir: Path) -> None:
    elements = ClangTidyCMakeGenerator(execution_context, output_dir).generate()

    locator = CMakeArtifactsLocator(output_dir, execution_context.spl_paths)
    registered = {entry.target.target_name: entry.html_content.index_html for entry in execution_context.data_registry.find_data(ReportRelevantFiles) if entry.html_content}
    assert registered == {
        "CompA_lint": Path("clang_tidy/CompA/index.html"),
        "CompBNotTestable_lint": Path("clang_tidy/CompBNotTestable/index.html"),
        "lint": Path("clang_tidy/index.html"),
    }
    report_arguments = [command.commands[0].arguments for command in find_elements_of_type(elements, CMakeCustomCommand) if command.commands[0].arguments[0] == "clang_tidy_report"]
    output_dirs = {str(arguments[arguments.index("--output-dir") + 1]) for arguments in report_arguments}
    assert output_dirs == {
        str(locator.get_component_reports_dir("CompA").joinpath("clang_tidy/CompA")),
        str(locator.get_component_reports_dir("CompBNotTestable").joinpath("clang_tidy/CompBNotTestable")),
        str(locator.cmake_variant_reports_dir.joinpath("clang_tidy")),
    }


def test_variant_lint_copies_each_component_report_into_the_variant_report(execution_context: ExecutionContext, output_dir: Path) -> None:
    elements = ClangTidyCMakeGenerator(execution_context, output_dir).generate()

    locator = CMakeArtifactsLocator(output_dir, execution_context.spl_paths)
    commands = find_elements_of_type(elements, CMakeCustomCommand)
    copy_commands = {
        (str(arguments[arguments.index("copy_directory") + 1]), str(arguments[arguments.index("copy_directory") + 2])): command
        for command in commands
        for arguments in [step.arguments for step in command.commands]
        if "copy_directory" in arguments
    }
    expected_copies = {
        (str(locator.get_component_reports_dir(name).joinpath(f"clang_tidy/{name}")), str(locator.cmake_variant_reports_dir.joinpath(f"clang_tidy/{name}")))
        for name in ["CompA", "CompBNotTestable"]
    }
    assert set(copy_commands) == expected_copies
    for (source_dir, _), command in copy_commands.items():
        assert f"{source_dir}/index.html" in {str(dependency) for dependency in command.depends or []}
    [lint_target] = [target for target in find_elements_of_type(elements, CMakeCustomTarget) if target.name == "lint"]
    lint_dependencies = {str(dependency) for dependency in lint_target.depends or []}
    assert all({str(output) for output in command.outputs or []} <= lint_dependencies for command in copy_commands.values())
