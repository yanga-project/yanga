"""Rewrite `source:<path>#<line>` links in a finished HTML report to real targets, or to plain text when none resolves."""

import re
from argparse import ArgumentParser, Namespace
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import partial
from pathlib import Path, PurePosixPath

from py_app_dev.core.cmd_line import Command, register_arguments_for_config_dataclass
from py_app_dev.core.config import BaseConfigJSONMixin
from py_app_dev.core.logging import logger, time_it
from yanga_core.commands.base import create_config

_SOURCE_ANCHOR = re.compile(r'<a\b[^>]*\bhref="source:([^"#]+)#(\d+)"[^>]*>(.*?)</a>', re.DOTALL)
_COVERAGE_PAGE_PATH = re.compile(r'<span class="current" title="([^"]+)"')
_COVERAGE_LINE_ID = re.compile(r'\bid="([lL]\d+)"')

#: Maps a source path and line to a URL relative to the report root, an absolute URL, or None.
Strategy = Callable[[str, int], str | None]


class SourceLinkStrategy(Enum):
    GCOVR = "gcovr"
    VSCODE = "vscode"


def _gcovr_strategy(report_dir: Path) -> Strategy:
    """In gcovr's nested report a file row shows only the file name; the file's own page names its path in the breadcrumb."""
    contents = {(page.parent.name, page.name): page.read_text(encoding="utf-8") for page in sorted(report_dir.glob("coverage/*/*.html"))}
    rows = [(tree, title, href) for (tree, href), content in contents.items() for title in _COVERAGE_PAGE_PATH.findall(content)]
    line_ids = {(tree, href): set(_COVERAGE_LINE_ID.findall(contents[tree, href])) for tree, _, href in rows}

    def resolve(source_path: str, line: int) -> str | None:
        """Rows with the same page name are one file; an integration test component lists the files it covers in its own tree."""
        matches = [(tree, href) for tree, title, href in rows if source_path == title or source_path.endswith("/" + title)]
        if len({href for _, href in matches}) > 1:
            logger.warning(f"Ambiguous coverage report for {source_path}: {matches}")
            return None
        if not matches:
            return None
        source_parts = PurePosixPath(source_path).parts
        tree, href = next((match for match in matches if match[0] in source_parts), matches[0])
        page = f"coverage/{tree}/{href}"
        # gcovr's github theme marks a line as id="l42", its boost theme as id="L42".
        anchor = next((line_id for line_id in (f"L{line}", f"l{line}") if line_id in line_ids[tree, href]), None)
        if anchor is None:
            logger.warning(f"No line {line} anchor in the coverage page of {source_path}")
            return page
        return f"{page}#{anchor}"

    return resolve


def _vscode_strategy(project_root: Path) -> Strategy:
    root = project_root.resolve()
    return lambda source_path, line: f"vscode://file/{(root / source_path).as_posix()}:{line}"


def resolve_source_links(report_dir: Path, project_root: Path, strategies: list[SourceLinkStrategy]) -> None:
    """Try the strategies in order for every `source:` link under report_dir."""
    available: dict[SourceLinkStrategy, Callable[[], Strategy]] = {
        SourceLinkStrategy.GCOVR: lambda: _gcovr_strategy(report_dir),
        SourceLinkStrategy.VSCODE: lambda: _vscode_strategy(project_root),
    }
    resolvers = [available[strategy]() for strategy in strategies]

    for html_file in report_dir.rglob("*.html"):
        content = html_file.read_text(encoding="utf-8")
        if 'href="source:' in content:
            depth = len(html_file.relative_to(report_dir).parts) - 1
            html_file.write_text(_SOURCE_ANCHOR.sub(partial(_replace, resolvers=resolvers, depth=depth), content), encoding="utf-8")


def _replace(match: re.Match[str], resolvers: list[Strategy], depth: int) -> str:
    source_path, line = match.group(1), match.group(2)
    for resolver in resolvers:
        if url := resolver(source_path, int(line)):
            href = url if "://" in url else "../" * depth + url
            return match.group(0).replace(f"source:{source_path}#{line}", href, 1)
    return match.group(3)


@dataclass
class CommandArgs(BaseConfigJSONMixin):
    report_dir: Path = field(metadata={"help": "Root directory of the HTML report"})
    project_root: Path = field(metadata={"help": "Project root directory, used to build editor links"})
    strategies: list[SourceLinkStrategy] = field(metadata={"help": "Link strategies, tried in order: gcovr, vscode"})


class ResolveSourceLinksCommand(Command):
    def __init__(self) -> None:
        super().__init__("resolve_source_links", "Resolve source: links in an HTML report.")

    @time_it("resolve_source_links")
    def run(self, args: Namespace) -> int:
        cli_args = create_config(CommandArgs, args)
        if not cli_args.report_dir.is_dir():
            logger.error(f"Report directory does not exist: {cli_args.report_dir}")
            return 1
        resolve_source_links(cli_args.report_dir, cli_args.project_root, cli_args.strategies)
        return 0

    def _register_arguments(self, parser: ArgumentParser) -> None:
        register_arguments_for_config_dataclass(parser, CommandArgs)
