import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from py_app_dev.core.subprocess import SubprocessExecutor
from sphinx.cmd.build import build_main

CONF_PY = """\
from docutils import nodes
from docutils.parsers.rst import Directive

extensions = ["myst_parser", "yanga.sphinx_pytest"]


class TestDirective(Directive):
    required_arguments = 1

    def run(self):
        return [nodes.paragraph(text=self.arguments[0])]


def setup(app):
    app.add_directive("test", TestDirective)
"""

PYTEST_COV_VARIABLES = ("COVERAGE_PROCESS_START", "COV_CORE_SOURCE", "COV_CORE_CONFIG", "COV_CORE_DATAFILE")

TEST_MODULE = '''\
import pytest


def test_with_spec():
    """.. test:: {{ pytest.test }}"""


@pytest.mark.parametrize("value", [1, 2])
def test_parametrized(value):
    """.. test:: {{ pytest.test }}"""


def test_without_docstring():
    pass
'''


def build_html(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, module_source: str) -> str:
    monkeypatch.delitem(sys.modules, "pkg_tests", raising=False)
    monkeypatch.delitem(sys.modules, "pkg_tests.test_sample", raising=False)
    (tmp_path / "pkg_tests").mkdir()
    (tmp_path / "pkg_tests/test_sample.py").write_text(module_source)
    src = tmp_path / "docs"
    src.mkdir()
    (src / "conf.py").write_text(CONF_PY)
    (src / "index.md").write_text("# Index\n\n```{toctree}\ntest_sample.py\n```\n")
    (src / "test_sample.py.md").write_text("# test_sample.py\n\n```{eval-rst}\n.. automodule:: pkg_tests.test_sample\n   :members:\n```\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    assert build_main(["-q", "-E", "-b", "html", str(src), str(tmp_path / "html")]) == 0

    return (tmp_path / "html/test_sample.py.html").read_text()


def test_docstring_placeholder_becomes_the_test_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    html = build_html(tmp_path, monkeypatch, TEST_MODULE)

    assert "<p>pkg_tests.test_sample.test_with_spec</p>" in html
    assert "test_without_docstring" not in html


@pytest.mark.parametrize("placeholder", ["{{ pytest.test }}", "{{pytest.test}}", "{{  pytest.test  }}", "{{\tpytest.test\t}}", "{{ pytest.test}}"])
def test_placeholder_accepts_the_spacing_of_jinja(placeholder: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = f'''def test_with_spec():\n    """.. test:: {placeholder}"""\n'''

    html = build_html(tmp_path, monkeypatch, module)

    assert "<p>pkg_tests.test_sample.test_with_spec</p>" in html


def test_title_matches_the_junit_names(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    html = build_html(tmp_path, monkeypatch, TEST_MODULE)
    junit = tmp_path / "junit.xml"
    env = {key: value for key, value in os.environ.items() if key not in PYTEST_COV_VARIABLES}

    SubprocessExecutor(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", f"--rootdir={tmp_path}", f"--junitxml={junit}", tmp_path / "pkg_tests/test_sample.py"],
        cwd=tmp_path,
        env=env,
        print_output=False,
    ).execute(handle_errors=False)

    titles = set(re.findall(r"<p>(pkg_tests\.[^<]*)</p>", html))
    testcases = ET.ElementTree(file=junit).iter("testcase")
    names = {f"{case.get('classname')}.{case.get('name', '').split('[')[0]}" for case in testcases}
    assert "pkg_tests.test_sample.test_parametrized" in titles
    assert titles == names - {"pkg_tests.test_sample.test_without_docstring"}
