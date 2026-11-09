"""
clang-tidy lint reports.

Add the generator to one platform, ideally the test platform; `lint` and `<component>_lint` then write `clang_tidy_report.md` for the reports:

    generators:
      - step: ClangTidyCMakeGenerator
        module: yanga.cmake.clang_tidy
"""

import json
import re
from argparse import Namespace
from pathlib import Path

import pytest
from clanguru.compilation_options_manager import CompileCommand
from yanga_core.domain.execution_context import ExecutionContext

from tests.utils import find_elements_of_type
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


def test_report_merges_outputs_once_and_lists_parse_failures_apart(tmp_path: Path) -> None:
    input_files = [tmp_path / "main.c.txt", tmp_path / "led.c.txt"]
    for input_file in input_files:
        input_file.write_text(CLANG_TIDY_OUTPUT)
    output_file = tmp_path / "clang_tidy_report.md"

    ClangTidyReportCommand().run(Namespace(input_files=input_files, output_file=output_file, project_dir=None))

    report = output_file.read_text()
    assert "Total issues found: 1" in report
    assert "clang-analyzer-core.NullDereference" in report
    assert "Parse failures" in report
    assert f"`{Path('/work/src/led.c')}:3`: unknown type name 'foo'" in report


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


def test_clang_tidy_steps_rerun_when_project_config_changes(execution_context: ExecutionContext, output_dir: Path) -> None:
    config_file = execution_context.project_root_dir / ".clang-tidy"
    config_file.write_text("Checks: 'bugprone-*'\n")

    elements = ClangTidyCMakeGenerator(execution_context, output_dir).generate()

    tidy_commands = [command for command in find_elements_of_type(elements, CMakeCustomCommand) if command.commands[0].arguments[0] == "clang_tidy"]
    assert all(str(CMakePath(config_file)) in [str(dependency) for dependency in command.depends or []] for command in tidy_commands)
