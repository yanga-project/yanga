"""Command line utilities to run clang-tidy on a gcc compilation database and report its findings as HTML and SARIF."""

import hashlib
import json
import re
import subprocess
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any
from urllib.parse import quote

from clanguru.compilation_options_manager import CompilationDatabase, CompileCommand
from jinja2 import ChoiceLoader, Environment, PackageLoader
from mashumaro import DataClassDictMixin
from py_app_dev.core.cmd_line import Command, register_arguments_for_config_dataclass
from py_app_dev.core.exceptions import UserNotificationException
from py_app_dev.core.logging import logger
from yanga_core.commands.base import create_config
from yanga_core.commands.cppcheck_report import CppCheckError, CppCheckResults, Location

# clang-tidy has no structured output with line numbers, only `file:line:col: severity: message [check]`.
# The lazy file match keeps Windows drive letters (`C:\...`) intact.
DIAGNOSTIC_PATTERN = re.compile(r"^(?P<file>.+?):(?P<line>\d+):(?P<column>\d+): (?P<severity>warning|error): (?P<msg>.*) \[(?P<check>[^\]]+)\]$")
#: clang reports a file it cannot parse under this check name.
PARSE_FAILURE_CHECK = "clang-diagnostic-error"
#: CodeChecker's severity per clang-tidy check, see templates/clang_tidy/clang_tidy_severities.NOTICE.
CHECK_SEVERITIES: dict[str, str] = json.loads(resources.files(__package__).joinpath("templates/clang_tidy/clang_tidy_severities.json").read_text(encoding="utf-8"))
SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "STYLE"]
#: A published report passes gcovr's style.css and gcovr.js on, so they keep gcovr's notice.
GCOVR_NOTICE = (
    "/* From gcovr (https://github.com/gcovr/gcovr). Copyright (c) 2013-2026 the gcovr authors, Copyright (c) 2013 Sandia Corporation.\n"
    "   Licensed under BSD-3-Clause, see LICENSE.txt in gcovr's distribution. */\n"
)


def severity_of(check: str) -> str:
    return CHECK_SEVERITIES.get(check, "MEDIUM")


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
    output_dir: Path = field(metadata={"help": "Directory for the HTML report and the SARIF file."})
    project_dir: Path | None = field(
        default=None,
        metadata={"help": "Project directory to make file paths relative to. If not provided, absolute paths are used."},
    )


def display_path(file: Path, project_dir: Path | None) -> Path:
    return file.relative_to(project_dir) if project_dir and file.is_relative_to(project_dir) else file


def artifact_location(file: Path, project_dir: Path | None) -> dict[str, str]:
    if project_dir and file.is_relative_to(project_dir):
        return {"uri": quote(file.relative_to(project_dir).as_posix()), "uriBaseId": "PROJECTROOT"}
    return {"uri": file.absolute().as_uri()}


def create_sarif(errors: list[CppCheckError], project_dir: Path | None) -> dict[str, Any]:
    results = [
        {
            "ruleId": error.id,
            "level": "error" if error.id == PARSE_FAILURE_CHECK else "warning",
            "message": {"text": error.msg},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": artifact_location(error.locations[0].file, project_dir),
                        "region": {"startLine": error.locations[0].line, "startColumn": error.locations[0].column},
                    }
                }
            ],
            "properties": {"severity": severity_of(error.id)},
        }
        for error in errors
    ]
    run: dict[str, Any] = {"tool": {"driver": {"name": "clang-tidy"}}, "results": results}
    if project_dir:
        run["originalUriBaseIds"] = {"PROJECTROOT": {"uri": project_dir.absolute().as_uri() + "/"}}
    return {"$schema": "https://json.schemastore.org/sarif-2.1.0.json", "version": "2.1.0", "runs": [run]}


def page_name(path: str) -> str:
    """One flat directory of pages, as gcovr's tree finds the current page by its file name."""
    safe_name = re.sub(r"[^\w.-]", "_", Path(path).name)
    return f"{safe_name}.{hashlib.sha256(path.encode()).hexdigest()[:8]}.html"


def add_pages(name: str, node: dict[str, Any] | list[dict[str, Any]], parent_path: str, pages: list[tuple[str, str, dict[str, Any]]]) -> dict[str, Any]:
    """Return the gcovr tree entry of a folder or file and add its page and the pages below it."""
    # Folders with a single folder inside are one row, as in gcovr's tree.
    while isinstance(node, dict) and len(node) == 1 and isinstance(next(iter(node.values())), dict):
        child_name, node = next(iter(node.items()))
        name = Path(name, child_name).as_posix()
    path = Path(parent_path, name).as_posix() if parent_path else name
    link = page_name(path)
    if isinstance(node, list):
        pages.append(("clang_tidy_file.html", link, {"path": path, "findings": sorted(node, key=lambda finding: finding["line"])}))
        return {"name": name, "link": link, "isDirectory": False, "counts": [[finding["severity"] for finding in node].count(severity) for severity in SEVERITIES]}
    children = [add_pages(child_name, child, path, pages) for child_name, child in sorted(node.items(), key=lambda item: (isinstance(item[1], list), item[0].lower()))]
    pages.append(("clang_tidy_folder.html", link, {"path": path, "rows": children}))
    return {"name": name, "link": link, "isDirectory": True, "children": children, "counts": [sum(counts) for counts in zip(*[child["counts"] for child in children], strict=True)]}


def write_html_report(errors: list[CppCheckError], project_dir: Path | None, output_dir: Path) -> None:
    """Render gcovr's boost theme (gcovr's own nested coverage look) with our folder and file pages."""
    tree: dict[str, Any] = {}
    parse_failures = []
    for error in errors:
        location = error.locations[0]
        if error.id == PARSE_FAILURE_CHECK:
            parse_failures.append({"location": f"{display_path(location.file, project_dir).as_posix()}:{location.line}", "message": error.msg})
            continue
        *folders, file_name = display_path(location.file, project_dir).parts
        node = tree
        for folder in folders:
            node = node.setdefault(folder, {})
        node.setdefault(file_name, []).append({"line": location.line, "check": error.id, "severity": severity_of(error.id), "message": error.msg})
    pages: list[tuple[str, str, dict[str, Any]]] = []
    tree_data = [add_pages(name, node, "", pages) for name, node in sorted(tree.items(), key=lambda item: (isinstance(item[1], list), item[0].lower()))]
    environment = Environment(
        loader=ChoiceLoader([PackageLoader("yanga", "commands/templates/clang_tidy"), PackageLoader("gcovr", "formats/html/boost")]),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    context: dict[str, Any] = {
        "theme": "blue",
        "info": {
            "head": "clang-tidy",
            "encoding": "utf-8",
            "html_nested": True,
            "static_report": False,
            "diff_report": False,
        },
        "ROOT_FNAME": "index.html",
        "GCOVR_TREE_DATA": tree_data,
        "css_link": "style.css",
        "javascript_link": "gcovr.js",
        "severities": SEVERITIES,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for template in ["style.css", "gcovr.js"]:
        output_dir.joinpath(template).write_text(GCOVR_NOTICE + environment.get_template(template).render(context), encoding="utf-8")
    pages.append(("clang_tidy_folder.html", "index.html", {"path": "", "rows": tree_data, "parse_failures": parse_failures}))
    for template, link, page_context in pages:
        output_dir.joinpath(link).write_text(environment.get_template(template).render(context | page_context), encoding="utf-8")


class ClangTidyReportCommand(Command):
    def __init__(self) -> None:
        super().__init__("clang_tidy_report", "Create the clang-tidy HTML report and SARIF file from the console outputs.")
        self.logger = logger.bind()

    def _register_arguments(self, parser: ArgumentParser) -> None:
        register_arguments_for_config_dataclass(parser, ClangTidyReportArgs)

    def run(self, args: Namespace) -> int:
        self.logger.info(f"Running {self.name} with args {args}")
        config = create_config(ClangTidyReportArgs, args)
        output = "\n".join(input_file.read_text(encoding="utf-8", errors="replace") for input_file in config.input_files)
        errors = parse_clang_tidy_output(output).errors
        write_html_report(errors, config.project_dir, config.output_dir)
        config.output_dir.joinpath("clang_tidy_report.sarif").write_text(json.dumps(create_sarif(errors, config.project_dir), indent=2), encoding="utf-8")
        return 0
