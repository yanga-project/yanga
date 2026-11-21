from argparse import ArgumentParser
from pathlib import Path

import pytest
from py_app_dev.core.logging import logger
from py_app_dev.core.subprocess import SubprocessExecutor

from yanga.commands.source_links import ResolveSourceLinksCommand, SourceLinkStrategy, resolve_source_links

COVERED = "components/light_controller/src/light_controller.c"
UNCOVERED = "components/light_controller/test/test_light_controller.cc"
PAGE = Path("components/light_controller/src/page.html")


def anchor(path: str, line: int) -> str:
    return f'<a class="reference external" href="source:{path}#{line}">{path}:{line}</a>'


def coverage_page(title: str, line_ids: str = '<a id="L42" href="#L42">42</a>') -> str:
    return f'<div class="breadcrumb"><a href="index.html" class="breadcrumb-home">Index</a><span class="current" title="{title}">{title}</span></div>{line_ids}'


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


@pytest.mark.parametrize("line_id", ["L42", "l42"], ids=["boost-theme", "github-theme"])
def test_gcovr_anchor_follows_the_page(report: Path, tmp_path: Path, line_id: str) -> None:
    write(report / "coverage/light_controller/index.light_controller.c.abc.html", coverage_page("light_controller.c", f'<a id="{line_id}" href="#{line_id}">42</a>'))

    resolve_source_links(report, tmp_path, [SourceLinkStrategy.GCOVR])

    assert f'href="../../../coverage/light_controller/index.light_controller.c.abc.html#{line_id}"' in (report / PAGE).read_text(encoding="utf-8")


@pytest.mark.parametrize("line_ids", ["", '<a id="lightController"></a><a id="L43"></a>'], ids=["no-line-ids", "function-id-only"])
def test_gcovr_missing_line_links_the_page_and_warns(report: Path, tmp_path: Path, line_ids: str) -> None:
    write(report / "coverage/light_controller/index.light_controller.c.abc.html", coverage_page("light_controller.c", line_ids))
    messages: list[str] = []
    sink_id = logger.add(messages.append, level="WARNING")
    try:
        resolve_source_links(report, tmp_path, [SourceLinkStrategy.GCOVR])
    finally:
        logger.remove(sink_id)

    assert 'href="../../../coverage/light_controller/index.light_controller.c.abc.html"' in (report / PAGE).read_text(encoding="utf-8")
    assert any(COVERED in message and "42" in message for message in messages)


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


def git_checkout(project_dir: Path, *remote: str) -> str:
    def git(*arguments: str) -> str:
        result = SubprocessExecutor(["git", *arguments], cwd=project_dir, print_output=False).execute(handle_errors=False)
        return result.stdout.strip() if result else ""

    git("init")
    git("-c", "user.name=yanga", "-c", "user.email=yanga@example.com", "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "init")
    if remote:
        git("remote", "add", "origin", *remote)
    return git("rev-parse", "HEAD")


@pytest.mark.parametrize(("path", "line"), [(COVERED, 42), (UNCOVERED, 7)], ids=["production-source", "test-source"])
def test_repository_links_to_the_code_host_at_the_commit(report: Path, tmp_path: Path, path: str, line: int) -> None:
    commit = git_checkout(tmp_path, "https://example.com/org/repo.git")

    resolve_source_links(report, tmp_path, [SourceLinkStrategy("repository")])

    assert f'href="https://example.com/org/repo/blob/{commit}/{path}#L{line}"' in (report / PAGE).read_text(encoding="utf-8")


@pytest.mark.parametrize(("strategies", "links_to_vscode"), [(["repository", "vscode"], True), (["repository"], False)], ids=["next-strategy", "plain-text"])
def test_repository_without_origin_falls_back(report: Path, tmp_path: Path, strategies: list[str], links_to_vscode: bool) -> None:
    git_checkout(tmp_path)

    resolve_source_links(report, tmp_path, [SourceLinkStrategy(strategy) for strategy in strategies])

    content = (report / PAGE).read_text(encoding="utf-8")
    assert (f'href="vscode://file/{(tmp_path.resolve() / UNCOVERED).as_posix()}:7"' in content) == links_to_vscode
    assert ("<a" in content) == links_to_vscode
    assert f"{UNCOVERED}:7" in content


@pytest.mark.parametrize("path", ["../modules/hal/src/hal.c", "/opt/sdk/src/hal.c"], ids=["outside-project", "absolute"])
def test_repository_leaves_sources_outside_the_project_to_the_next_strategy(tmp_path: Path, path: str) -> None:
    git_checkout(tmp_path, "https://example.com/org/repo.git")
    report_dir = tmp_path / "report"
    write(report_dir / PAGE, anchor(path, 3))

    resolve_source_links(report_dir, tmp_path, [SourceLinkStrategy("repository")])

    content = (report_dir / PAGE).read_text(encoding="utf-8")
    assert f"{path}:3" in content
    assert "<a" not in content
