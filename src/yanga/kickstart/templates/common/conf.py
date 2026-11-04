import datetime
from typing import Any

from yanga_core.docs.sphinx import SphinxConfig

day = datetime.date.today()

copyright = f"{day.year} our team"
version = f"{day.year}.{day.month}.{day.day}"
release = f"{day}"

exclude_patterns = [
    ".venv",
    ".git",
]

html_context: dict[str, Any] = {
    "env": {
        # Add current execution time in UTC
        "timestamp": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S %Z")
    }
}

include_patterns = [
    "index.md",
    "docs/components.md",
]

report_config = SphinxConfig()
html_context.update(report_config.html_context)
include_patterns.extend(report_config.include_patterns)

project = report_config.project

html_title = f"{project} {release}"
html_show_sourcelink = True

extensions = []
extensions.append("sphinx_design")
extensions.append("sphinx_rtd_size")
sphinx_rtd_size_width = "90%"
extensions.append("myst_parser")
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "html_admonition",
    "html_image",
]
extensions.append("sphinx_copybutton")
extensions.append("sphinx_needs")

html_theme = "sphinx_rtd_theme"
html_show_sourcelink = True
html_theme_options = {
    "canonical_url": "",
    "analytics_id": "",
    "display_version": True,
    "prev_next_buttons_location": "bottom",
    "style_external_links": True,
    "logo_only": False,
    # Toc options
    "collapse_navigation": True,
    "sticky_navigation": True,
    "navigation_depth": 6,
    "includehidden": True,
    "titles_only": False,
}

# The suffix of source filenames.
source_suffix = [
    ".md",
    ".rst",
]


def setup(app):  # type: ignore
    app.connect("source-read", report_config.render_with_jinja)
