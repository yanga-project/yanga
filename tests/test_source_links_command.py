from argparse import ArgumentParser
from pathlib import Path

import pytest
from py_app_dev.core.logging import logger

from yanga.commands.source_links import ResolveSourceLinksCommand, SourceLinkStrategy, resolve_source_links

COVERED = "components/light_controller/src/light_controller.c"
UNCOVERED = "components/light_controller/test/test_light_controller.cc"
PAGE = Path("components/light_controller/src/page.html")


def anchor(path: str, line: int) -> str:
    return f'<a class="reference external" href="source:{path}#{line}">{path}:{line}</a>'


def coverage_page(title: str) -> str:
    return f'<div class="breadcrumb"><a href="index.html" class="breadcrumb-home">Index</a><span class="current" title="{title}">{title}</span></div>'


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def report(tmp_path: Path) -> Path:
    report_dir = tmp_path / "report"
    write(report_dir / "coverage/light_controller/index.light_controller.c.abc.html", coverage_page("light_controller.c"))
    write(report_dir / "coverage/light_controller/index.my_util.c.def.html", coverage_page("my_util.c"))
    write(report_dir / "coverage/index.main.c.999.html", coverage_page("spled/main.c"))
    write(report_dir / PAGE, "".join(anchor(path, line) for path, line in [(COVERED, 42), (UNCOVERED, 7), ("components/x/src/util.c", 7), ("spled/main.c", 7)]))
    return report_dir


def test_gcovr_resolves_covered_file(report: Path, tmp_path: Path) -> None:
    resolve_source_links(report, tmp_path, [SourceLinkStrategy.GCOVR])

    content = (report / PAGE).read_text(encoding="utf-8")
    assert 'href="../../../coverage/light_controller/index.light_controller.c.abc.html#L42"' in content
    assert f"source:{COVERED}" not in content


@pytest.mark.parametrize("path", [UNCOVERED, "components/x/src/util.c", "spled/main.c"], ids=["not-covered", "no-slash-boundary", "variant-tree-only"])
def test_unresolved_link_becomes_plain_text(report: Path, tmp_path: Path, path: str) -> None:
    resolve_source_links(report, tmp_path, [SourceLinkStrategy.GCOVR])

    content = (report / PAGE).read_text(encoding="utf-8")
    assert f"{path}:7" in content
    assert f'href="source:{path}' not in content


def test_unresolved_without_coverage_dir(tmp_path: Path) -> None:
    report_dir = tmp_path / "report"
    write(report_dir / PAGE, anchor(COVERED, 42))

    resolve_source_links(report_dir, tmp_path, [SourceLinkStrategy.GCOVR])

    content = (report_dir / PAGE).read_text(encoding="utf-8")
    assert f"{COVERED}:42" in content
    assert "<a" not in content


def test_gcovr_duplicate_rows_warn_and_give_plain_text(report: Path, tmp_path: Path) -> None:
    write(report / "coverage/other/index.light_controller.c.zzz.html", coverage_page("light_controller.c"))
    messages: list[str] = []
    sink_id = logger.add(messages.append, level="WARNING")
    try:
        resolve_source_links(report, tmp_path, [SourceLinkStrategy.GCOVR])
    finally:
        logger.remove(sink_id)

    content = (report / PAGE).read_text(encoding="utf-8")
    assert f"source:{COVERED}" not in content
    assert f"{COVERED}:42" in content
    assert any(COVERED in message for message in messages)


def test_gcovr_same_page_in_several_trees_goes_to_the_component_tree(report: Path, tmp_path: Path) -> None:
    write(report / "coverage/test_integrations_spled/index.light_controller.c.abc.html", coverage_page("light_controller/src/light_controller.c"))
    messages: list[str] = []
    sink_id = logger.add(messages.append, level="WARNING")
    try:
        resolve_source_links(report, tmp_path, [SourceLinkStrategy.GCOVR])
    finally:
        logger.remove(sink_id)

    content = (report / PAGE).read_text(encoding="utf-8")
    assert 'href="../../../coverage/light_controller/index.light_controller.c.abc.html#L42"' in content
    assert not messages


def test_vscode_fallback_for_uncovered_file(report: Path, tmp_path: Path) -> None:
    resolve_source_links(report, tmp_path, [SourceLinkStrategy.GCOVR, SourceLinkStrategy.VSCODE])

    content = (report / PAGE).read_text(encoding="utf-8")
    assert f'href="vscode://file/{(tmp_path / UNCOVERED).as_posix()}:7"' in content
    assert 'href="../../../coverage/light_controller/index.light_controller.c.abc.html#L42"' in content


def test_command_runs_from_cli(report: Path, tmp_path: Path) -> None:
    command = ResolveSourceLinksCommand()
    parser = ArgumentParser()
    command._register_arguments(parser)

    args = parser.parse_args(["--report-dir", str(report), "--project-root", str(tmp_path), "--strategies", "gcovr"])
    assert command.run(args) == 0
    assert 'href="../../../coverage/light_controller/index.light_controller.c.abc.html#L42"' in (report / PAGE).read_text(encoding="utf-8")

    missing = parser.parse_args(["--report-dir", str(tmp_path / "missing"), "--project-root", str(tmp_path), "--strategies", "gcovr"])
    assert command.run(missing) == 1
