# ADR 0001: Report sections per test framework and per coverage tool

**Status:** Accepted

## Context

A component, an integration component and a variant declare one testing block per framework. The report was built for one framework: the test results page and its id are named after the component only (`<name>_test_report.rst`, `TR_<NAME>`), the merged pages give each result one section, and no result or coverage entry says which framework or tool produced it. A second framework's results would overwrite the first, and the merged pages would repeat ids.

The report already has the chapters all components, all containers, variant and overall. More frameworks will come (gtest, pytest, later others such as Tessy), and the report must not grow a page or a chapter with each one.

## Decision

The report grows by sections, not by pages:

- **One "Test results" page per entry,** with one section per framework, in the order of the `testing:` list, each with its own counters and its own unique id. gtest's sections keep the ids they have today, on component, container and merged pages. There is no total on the page.
- **One "Coverage" page per entry,** a markdown page yanga writes, with one section per coverage tool. The gcovr section links the gcovr HTML in the `./<path>/index.html#http://` form, which `fix_html_links` turns into a working link. The page is the coverage entry; the HTML is no longer registered as HTML content, so the report does not list Coverage twice.
- **Coverage data that one tool can read is merged.** Each test generator registers a gcovr tracefile per entry; the collector merges every tracefile of that entry. The all components, all containers and overall pages merge every tracefile.
- **Every result and coverage entry carries the framework and the coverage tool as tags,** so a report template filters on them as it filters on level and kind.
- **A run target per framework,** `<name>_<framework>_test`; the phony `<name>_test` and `<name>_coverage` run every framework of the entry. `<name>_report` stays with `ReportCMakeGenerator`: it runs every target that registered a report entry of the component, so it already runs every framework.
- **A collector generator, `TestResultsCMakeGenerator`,** listed after the test generators, creates the phony targets (`<name>_test`, `<name>_build`, `<name>_coverage` and the variant and merged ones), merges coverage and writes the coverage pages. The test generators only build, run and register.

The sections are built for gtest and pytest, and the Coverage page has the gcovr section only.

## Rejected alternatives

- **A page per framework under each entry.** The number of pages grows with every framework.
- **A chapter per framework.** Doubles the chapters the reader has to go through.
- **Coverage per framework next to merged coverage.** Two numbers for the same code, and both multiply with each framework.
- **Sections inside the gcovr HTML.** The HTML is gcovr's output; the sections belong to the report page.
- **gtest collecting for every framework.** pytest would define the same targets again, gtest merges before a generator listed after it has registered anything, and pytest must work without gtest.
- **`SphinxTestReportCMakeGenerator` collecting.** Its job is the results report; a platform without it would lose its coverage.
- **gtest collecting only when no collector is listed.** Two code paths for one job.
- **pytest reusing gtest's object library to share `.gcda` files.** pytest must work on a platform without the gtest generator.

## Consequences

- Breaking: a platform that tests must list `TestResultsCMakeGenerator`. Accepted while yanga-core is at 0.x and yanga in alpha.
- A gtest-only report keeps its ids; the coverage entry becomes a page that links the same HTML, so the HTML is now one click deeper.
- A framework with its own coverage tool adds a section to the Coverage page; its data is not merged with gcov data.
