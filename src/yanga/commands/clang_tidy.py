"""Command line utilities to run clang-tidy on a gcc compilation database and report its findings in Markdown."""

import re
import subprocess
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass, field
from pathlib import Path

from clanguru.compilation_options_manager import CompilationDatabase, CompileCommand
from clanguru.doc_generator import MarkdownFormatter, Section, TextContent
from mashumaro import DataClassDictMixin
from py_app_dev.core.cmd_line import Command, register_arguments_for_config_dataclass
from py_app_dev.core.exceptions import UserNotificationException
from py_app_dev.core.logging import logger
from yanga_core.commands.base import create_config
from yanga_core.commands.cppcheck_report import CppCheckError, CppCheckResults, Location, create_doc_structure

# clang-tidy has no structured output with line numbers, only `file:line:col: severity: message [check]`.
# The lazy file match keeps Windows drive letters (`C:\...`) intact.
DIAGNOSTIC_PATTERN = re.compile(r"^(?P<file>.+?):(?P<line>\d+):(?P<column>\d+): (?P<severity>warning|error): (?P<msg>.*) \[(?P<check>[^\]]+)\]$")
#: clang reports a file it cannot parse under this check name.
PARSE_FAILURE_CHECK = "clang-diagnostic-error"


def parse_clang_tidy_output(content: str) -> CppCheckResults:
    """Parse the diagnostics once each: a header warning repeats for every source file that includes it."""
    errors = []
    seen_lines = set()
    for line in content.splitlines():
        match = DIAGNOSTIC_PATTERN.match(line.strip())
        if match and match[0] not in seen_lines:
            seen_lines.add(match[0])
            location = Location(file=Path(match["file"]), line=int(match["line"]), column=int(match["column"]))
            errors.append(CppCheckError(id=match["check"], severity=match["severity"], msg=match["msg"], locations=[location]))
    return CppCheckResults(errors=errors)


def to_clang_compile_command(command: CompileCommand) -> CompileCommand:
    """Keep only what clang needs to parse the file, so gcc-only flags (e.g. `-fcondition-coverage`) do not stop clang-tidy."""
    language_standards = [option for option in command.get_compile_options() if option.startswith("-std=")]
    return CompileCommand(
        directory=command.directory,
        file=command.file,
        arguments=[str(command.get_compiler()), *command.get_includes_and_defines(), *language_standards, "-c", str(command.file)],
    )


def header_filter(include_directories: list[Path]) -> str:
    """Match headers below the include directories with either path separator, as clang may report both on Windows."""
    return "(" + "|".join(re.escape(directory.as_posix()).replace("/", r"[/\\]") for directory in include_directories) + r")[/\\]"


@dataclass
class ClangCompileCommandsArgs(DataClassDictMixin):
    compilation_database: Path = field(metadata={"help": "gcc compile_commands.json."})
    output_file: Path = field(metadata={"help": "compile_commands.json for clang."})


class ClangCompileCommandsCommand(Command):
    def __init__(self) -> None:
        super().__init__("clang_compile_commands", "Rewrite a compilation database for clang, keeping only the parse flags.")
        self.logger = logger.bind()

    def _register_arguments(self, parser: ArgumentParser) -> None:
        register_arguments_for_config_dataclass(parser, ClangCompileCommandsArgs)

    def run(self, args: Namespace) -> int:
        self.logger.info(f"Running {self.name} with args {args}")
        config = create_config(ClangCompileCommandsArgs, args)
        database = CompilationDatabase.from_json_file(config.compilation_database)
        config.output_file.parent.mkdir(parents=True, exist_ok=True)
        CompilationDatabase([to_clang_compile_command(command) for command in database.commands]).to_json_file(config.output_file)
        return 0


@dataclass
class ClangTidyArgs(DataClassDictMixin):
    source_file: Path = field(metadata={"help": "Source file to analyse."})
    compilation_database_dir: Path = field(metadata={"help": "Directory with the compile_commands.json for clang."})
    output_file: Path = field(metadata={"help": "clang-tidy console output."})
    include_directories: list[Path] = field(default_factory=list, metadata={"help": "Directories whose headers are reported."})


class ClangTidyCommand(Command):
    def __init__(self) -> None:
        super().__init__("clang_tidy", "Run clang-tidy for one source file and keep its output, also when the file does not parse.")
        self.logger = logger.bind()

    def _register_arguments(self, parser: ArgumentParser) -> None:
        register_arguments_for_config_dataclass(parser, ClangTidyArgs)

    def run(self, args: Namespace) -> int:
        self.logger.info(f"Running {self.name} with args {args}")
        config = create_config(ClangTidyArgs, args)
        # A Python step and not a plain CMake command: the backend does not quote arguments, so the build shell would read the `|` in the header filter as a pipe.
        arguments = ["clang-tidy", "-p", str(config.compilation_database_dir)]
        if config.include_directories:
            arguments.append(f"--header-filter={header_filter(config.include_directories)}")
        arguments.append(str(config.source_file))
        try:
            # Findings and parse failures make clang-tidy exit with an error; they belong in the report, not in a failed build.
            result = subprocess.run(arguments, capture_output=True, text=True, errors="replace", check=False)  # noqa: S603
        except FileNotFoundError as exc:
            raise UserNotificationException("clang-tidy not found. Install clang and make sure clang-tidy is on the PATH.") from exc
        config.output_file.parent.mkdir(parents=True, exist_ok=True)
        config.output_file.write_text(result.stdout + result.stderr, encoding="utf-8")
        return 0


@dataclass
class ClangTidyReportArgs(DataClassDictMixin):
    input_files: list[Path] = field(metadata={"help": "clang-tidy console outputs."})
    output_file: Path = field(metadata={"help": "Markdown report."})
    project_dir: Path | None = field(
        default=None,
        metadata={"help": "Project directory to make file paths relative to. If not provided, absolute paths are used."},
    )


def create_report(results: CppCheckResults, project_dir: Path | None) -> str:
    findings = [error for error in results.errors if error.id != PARSE_FAILURE_CHECK]
    parse_failures = [error for error in results.errors if error.id == PARSE_FAILURE_CHECK]
    doc = create_doc_structure(CppCheckResults(errors=findings), "Static Analysis Report", project_dir=project_dir)
    section = Section("Parse failures")
    if parse_failures:
        section.add_content(
            TextContent("clang could not parse these files, so they are not analysed. A missing preprocessor guard around compiler-specific code is the usual cause.")
        )
        for error in parse_failures:
            location = error.locations[0]
            display_path = location.file.relative_to(project_dir) if project_dir and location.file.is_relative_to(project_dir) else location.file
            section.add_content(TextContent(f"- `{display_path}:{location.line}`: {error.msg}"))
    else:
        section.add_content(TextContent("No parse failures."))
    doc.add_section(section)
    return MarkdownFormatter().format(doc)


class ClangTidyReportCommand(Command):
    def __init__(self) -> None:
        super().__init__("clang_tidy_report", "Create clang-tidy report from the console outputs.")
        self.logger = logger.bind()

    def _register_arguments(self, parser: ArgumentParser) -> None:
        register_arguments_for_config_dataclass(parser, ClangTidyReportArgs)

    def run(self, args: Namespace) -> int:
        self.logger.info(f"Running {self.name} with args {args}")
        config = create_config(ClangTidyReportArgs, args)
        output = "\n".join(input_file.read_text(encoding="utf-8", errors="replace") for input_file in config.input_files)
        config.output_file.write_text(create_report(parse_clang_tidy_output(output), config.project_dir))
        return 0
