"""Sphinx extension that names a pytest test in its docstring spec, so the spec title matches the test's JUnit result."""

import re
from typing import Any

from sphinx.application import Sphinx

PLACEHOLDER = re.compile(r"\{\{\s*pytest\.test\s*\}\}")


def replace_test_placeholder(app: Sphinx, what: str, name: str, obj: Any, options: Any, lines: list[str]) -> None:
    lines[:] = [PLACEHOLDER.sub(lambda _: name, line) for line in lines]


def setup(app: Sphinx) -> dict[str, Any]:
    app.setup_extension("sphinx.ext.autodoc")
    app.connect("autodoc-process-docstring", replace_test_placeholder)
    return {"parallel_read_safe": True}
