---
status: Done (2026-11-24)
priority: Medium
related: [YANGA-005, YANGA-013]
---

# [YANGA-012] Builds with several test frameworks: test results and coverage

## Summary

As the owner of a product line that tests with more than one framework, I want each framework's test results and each coverage tool's coverage reported side by side on the pages that exist today, so that the report shows every test without collisions and without a new page or chapter for each framework.

## Description

Components, integration components and variants declare one testing block per framework, but the report side assumes one framework per component:

- The test results page and its need id are named per component (`<name>_test_report.rst`, `TR_<NAME>`), so two JUnit files for one component would collide.
- `TestResultFile` and the coverage registration do not say which framework or tool produced them, and no report entry carries a framework tag.
- The merged coverage pages combine gcovr tracefiles and do not know about a second framework.

The pytest generator (YANGA-013) is the second framework, and more may follow.

## What exists

- [src/yanga/cmake/sphinx_test_report.py](../../src/yanga/cmake/sphinx_test_report.py): `TestResultFile`, the results pages and their ids.
- [src/yanga/cmake/gtest.py](../../src/yanga/cmake/gtest.py): result and coverage registration, merged and overall coverage.
- [docs/reference/cmake.md](../reference/cmake.md): the generators' documentation.
- yanga-core `src/yanga_core/domain/reports.py`: `ReportRelevantFiles`, `TEST_RESULT`, `COVERAGE_RESULT`, tags.
- SPLedY `doc/components.md` and `doc/containers.md`: a report template that lists each entry's pages by kind.

## Scope decisions

- **Results per framework, coverage per coverage tool, on one page each.** The report must stay readable with any number of frameworks (gtest, pytest, later others such as Tessy), so it grows by sections, not by pages or chapters. A component, an integration component and a variant keep one "Test results" page, with one section per framework in the order of the `testing:` list, each with its own counters and its own unique id; gtest's results keep the id they have today. There is no total on this page. They get one "Coverage" page, a markdown page yanga writes, with one section per coverage tool; the gcovr HTML stays as it is and is linked from the gcovr section. Coverage data that one tool can read is merged: each test generator writes a gcovr tracefile per entry and registers it, and the collector generator merges every tracefile of that entry, whichever generator wrote it. The all components, all containers and overall pages list every framework's results and merge every tracefile, as they merge component tracefiles today. Every result and coverage entry carries the framework (`gtest`, `pytest`, as named in `testing:`) and the coverage tool (`gcovr`) as tags. Each framework has its own run target `<name>_<framework>_test` (`<name>_gtest_test`, `<name>_pytest_test`); the phony targets `<name>_test`, `<name>_coverage` and `<name>_report` run every framework the entry has; the collector generator creates `<name>_test` and `<name>_coverage`, and `<name>_report` stays with `ReportCMakeGenerator`. The variant keeps its `variant_test_coverage` target, now over every framework. The same id rule holds on component, container and merged pages: every section has a unique id, gtest's sections keep the ids they have today, and the format of new ids is left to the builder. The markdown Coverage page links the gcovr HTML with the `./<path>/index.html#http://` form yanga-core already writes for HTML content, so `fix_html_links` makes it a working link; the markdown page is the coverage entry and the gcovr HTML is no longer registered as HTML content, because yanga-core lists every HTML content entry and the report would show Coverage twice; yanga-core does not change. Merged pages have one section per component with one subsection per framework. This epic builds the sections for gtest and pytest and the gcovr section only. Rejected: a page per framework, and single-framework coverage next to merged coverage, because both multiply the pages with each new framework; sections inside the gcovr HTML; pytest reusing gtest's object library to share `.gcda` files, because pytest must work on a platform without the gtest generator. This is YANGA-012, which joins this epic, is refined with these decisions instead of a new item, and comes before the pytest generator registers results.
- **A collector generator, `TestResultsCMakeGenerator` (module `yanga.cmake.test_results`).** A platform lists it after its test generators. It creates the phony `<name>_test` and `<name>_coverage` targets, merges the coverage tracefiles per entry, and writes the Coverage pages and the merged coverage pages. The test generators only build, run and register. Rejected: gtest collecting for every framework, because pytest would then define the same targets again, gtest merges before a generator listed after it has registered anything, and pytest must work without gtest; `SphinxTestReportCMakeGenerator` collecting, because its job is the results report and a platform without it would lose its coverage; gtest collecting only when no collector is listed, because that is two code paths for one job. This breaks platforms that test: they must list the new generator. Accepted, because yanga-core is at 0.x and yanga is in alpha.
- **`<name>_report` stays with `ReportCMakeGenerator`** (decided 2026-11-24). It already runs every target that registered a report entry of the component through `<name>_results`, so it runs every framework; the collector creating it too would define it twice. `TestResultsCMakeGenerator` creates `<name>_test` and `<name>_coverage`, and `<name>_build` beside `<name>_test` as gtest did before.
- **Order and release.** clanguru `bind` first, released. YANGA-012 in parallel, as it does not need clanguru. Then the yanga pytest generator, blocked by both. Then SPLedY, with editable installs of clanguru and yanga, before the yanga release; yanga is released only when SPLedY is green.

## What users see

- **Report: the "Test results" page gets one section per framework, and the "Coverage" entry becomes a markdown page with one section per coverage tool, linking the gcovr HTML.** gtest's results keep their ids. Not breaking for configuration; a gtest-only report looks the same apart from the section heading. UAT: yes, the reports of SPLedY are read. Why: today the pages assume one framework, and a second one would overwrite the first (YANGA-012). Approved by the human (2026-11-24)
- **New generator `TestResultsCMakeGenerator` (module `yanga.cmake.test_results`)**, listed after the test generators. It creates the phony test, coverage and report targets of each entry and the coverage pages. Not marked breaking, by the human's decision (2026-11-24): yanga is Pre-Alpha (`Development Status :: 2 - Pre-Alpha`), so this change goes out as a minor release, not 3.0.0. A platform that tests must add it, or loses its coverage and phony targets; the release notes give the one line to add. UAT: yes, SPLedY's gtest platform lists it. Why: something must collect what every framework produced, and that job belongs to no framework. Approved by the human (2026-11-24)
- **Report entries carry the framework and the coverage tool as tags.** Not breaking: tags are added, none removed. UAT: no, covered by tests. Why: a report template can then filter per framework, as it filters per level and kind today. Approved by the human (2026-11-24)
- **CMake targets per framework**: `<name>_gtest_test` and `<name>_pytest_test` run one framework; the phony `<name>_test`, `<name>_coverage` and `<name>_report` run every framework the entry has. Not breaking: the existing target names stay and still run gtest. UAT: yes, `yanga run --target <name>_test` in SPLedY runs both. Why: a user must be able to run one framework or all of them. Approved by the human (2026-11-24)

## Decision records and glossary

- [ADR 0001](../explanation/decisions/0001-report-sections-per-framework-and-coverage-tool.md)

## Out of scope

A generator for a second framework (YANGA-013); a coverage tool other than gcovr.

## Acceptance criteria

- [x] The "Test results" page of an entry has one section per framework, each with its own id, gtest keeping its current id; the "Coverage" page is a markdown page with one section per coverage tool, the gcovr section linking the HTML merged from every tracefile of the entry; every result and coverage entry carries the framework and the coverage tool as tags. Check: yanga's report tests in `pypeline run`.
- [x] With `TestResultsCMakeGenerator` listed, `<name>_test`, `<name>_coverage` and `<name>_report` run every framework of the entry, `<name>_gtest_test` runs gtest alone, and `variant_test_coverage` covers every framework; without it, no phony target is defined twice. Check: yanga's generator tests in `pypeline run`.
- [x] The report sections ADR is in yanga's docs. Check: the docs build in `pypeline run`.
- [x] A gtest-only report keeps the ids of its test results. Check: yanga's report tests in `pypeline run`.

## Plan

1. `sphinx_test_report`: `TestResultFile` carries its framework; the results page of an entry gets one section per framework in the order of the `testing:` list, each with its own counters and unique id, gtest keeping its current id; no total on the page.
2. `test_results.py` (new `TestResultsCMakeGenerator`): the phony `<name>_test` and `<name>_coverage` over every registered framework; the per-entry merge of all registered gcovr tracefiles (`coverage.py`, extended); the markdown Coverage page per entry as the coverage entry, linking the gcovr HTML in the `./<path>/index.html#http://` form, no longer registered as HTML content; the merged coverage pages; the variant's `variant_test_coverage` over every framework. First check that such a markdown link survives the Sphinx build and `fix_html_links` and that the gcovr folder is copied from component to variant report; stop and ask if not.
3. `gtest`: only build, run and register: its run target becomes `<name>_gtest_test`; it registers its JUnit file and a gcovr tracefile per entry; the phony targets, the coverage merge and the coverage pages move to the collector.
4. `sphinx_test_report`, collector: every result and coverage entry gets the framework and the coverage tool as tags; container and merged pages have one section per component with one subsection per framework, unique ids, gtest keeping its current ids.
5. `docs`: `docs/reference/cmake.md` (the new generator and the line a platform adds); the ADR in `docs/explanation/decisions/`, listed in the toctree of `docs/explanation/index.md`.
