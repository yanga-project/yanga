import re
from pathlib import Path

import jinja2
import pytest
from py_app_dev.core.exceptions import UserNotificationException
from yanga_core.docs.sphinx import SphinxReportConfig
from yanga_core.domain.execution_context import UserRequest, UserRequestScope
from yanga_core.domain.reports import ComponentReportData, ReportRelevantFiles, ReportRelevantFileType, ReportRelevantHtmlContent, VariantReportData

from yanga.kickstart.create import KickstartProject


def test_create_project_from_template(tmp_path):
    out_dir = tmp_path / "out"
    KickstartProject(project_dir=out_dir).run()
    files = ["README.md", "AGENTS.md", "poks.json", "yanga.yaml", "src/main.c", "src/greeter/greeter.c"]
    for file in files:
        assert (out_dir / file).exists()


def test_create_project_fails_if_out_is_not_empty(tmp_path: Path) -> None:
    tmp_path.joinpath("some_file.txt").write_text("some content")
    with pytest.raises(UserNotificationException):
        KickstartProject(tmp_path).run()
    KickstartProject(tmp_path, force=True).run()
    assert tmp_path.joinpath("yanga.yaml").exists()


def test_variant_report_toctree_has_no_duplicate_names(tmp_path: Path) -> None:
    KickstartProject(project_dir=tmp_path).run()

    def entry(tags: list[str], file_type: ReportRelevantFileType, name: str) -> ReportRelevantFiles:
        file = tmp_path / "build" / f"{'_'.join(tags)}_{name.replace(' ', '_')}"
        html = ReportRelevantHtmlContent(name=name, index_html=file / "index.html") if file_type == ReportRelevantFileType.HTML else None
        files = [] if html else [file.with_suffix(".md")]
        return ReportRelevantFiles(target=UserRequest(UserRequestScope.VARIANT), file_type=file_type, files_to_be_included=files, html_content=html, tags=tags)

    md, html = ReportRelevantFileType.OTHER, ReportRelevantFileType.HTML
    unit = ComponentReportData(
        name="greeter",
        files=[
            entry(["component", "sources", "greeter"], ReportRelevantFileType.SOURCES, "sources"),
            entry(["component", "test", "greeter"], ReportRelevantFileType.TEST_RESULT, "test"),
            entry(["component", "coverage", "greeter"], html, "Coverage"),
            entry(["component", "static-analysis", "greeter"], html, "Static Analysis"),
        ],
    )
    container = ComponentReportData(
        name="app",
        subcomponents=["greeter"],
        files=[entry(["container", "test", "app"], ReportRelevantFileType.TEST_RESULT, "test"), entry(["container", "coverage", "app"], html, "Coverage")],
    )
    integration = ComponentReportData(name="integ", files=[entry(["container", "test", "integ"], ReportRelevantFileType.TEST_RESULT, "test")])
    variant = VariantReportData(
        files=[
            entry(["component", "merged", "coverage"], html, "Coverage"),
            entry(["container", "merged", "coverage"], html, "Coverage"),
            entry(["overall", "coverage"], html, "Coverage"),
            entry(["variant", "test"], ReportRelevantFileType.TEST_RESULT, "test"),
            entry(["variant", "coverage"], html, "Coverage"),
            entry(["variant", "configuration"], md, "configuration"),
            entry([], md, "untagged"),
        ]
    )
    report_data = SphinxReportConfig(project_dir=tmp_path, variant_name="English", components=[unit, container, integration], variant_data=variant)

    def render(page: Path) -> str:
        return (
            jinja2.Environment(autoescape=jinja2.select_autoescape(default_for_string=False))
            .from_string(page.read_text())
            .render(report_data=report_data, env={"timestamp": "now"})
        )

    def name(line: str) -> str:
        if match := re.match(r"(.+?)\s*<.*>$", line):
            return match.group(1)
        page = tmp_path / f"{line.lstrip('/')}.md"
        if line.startswith("/docs/") and page.exists():
            return next(heading[2:] for heading in render(page).splitlines() if heading.startswith("# "))
        return line

    toctree = render(tmp_path / "index.md").split("```{toctree}")[1].split("```")[0]
    names = [name(line.strip()) for line in toctree.splitlines() if line.strip() and not line.strip().startswith(":")]
    assert len(names) == len(set(names)), names
