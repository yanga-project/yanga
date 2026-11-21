---
status: Done (2026-11-21)
priority: Medium
related: [YANGA-007]
---

# [YANGA-003] Static analysis report as HTML with a folder tree and severities

## Summary

The clang-tidy report is an HTML report like the coverage report, with a folder tree that counts the findings per severity for each folder and file, so that a developer sees where the findings are and which ones matter first.

## Description

The clang-tidy report today is Markdown in the Sphinx report: one section per file name, the findings listed under it, no folders and no weight. clang-tidy itself only marks a finding as `warning` or `error`, so the report cannot say which findings matter more.

YANGA-007 made the coverage report a folder tree (gcovr's nested mode with the `boost.blue` theme). The static analysis report should be read the same way.

A spike on 2026-11-20 checked CodeChecker 6.29.3 on SPLed's clang-tidy output: its static HTML is a flat list of findings plus counts per check and per severity, with no folder overview, so it does not fit. What fits is its table of severities per clang-tidy check (`config/labels/analyzers/clang-tidy.json`, licence Apache-2.0 WITH LLVM-exception): about 1,690 checks, each `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` or `STYLE`. The spike is recorded in the planning vault's epic SB-005.

## Scope decisions

- **HTML written by yanga.** The `clang_tidy_report` command writes the HTML report for a component and for the variant, in place of the Markdown. No new dependency for the HTML.
- **gcovr's boost theme, loaded from the installed gcovr (decided 2026-11-20).** The report uses gcovr's `base.html`, `style.css` and `gcovr.js` from the gcovr package (BSD-3-Clause), nothing copied, and adds two templates of its own: the folder page with counts per severity and the file page with the findings. gcovr does not document these files, so the gcovr range is pinned to the versions tested, and a test renders a page so a gcovr change shows up there.
- **Folder tree as in gcovr's nested report.** The sidebar tree opens and closes; each folder page, starting with the entry page, lists its subfolders and files with their number of findings per severity. Paths relative to the project root; folders with a single child merged into one row, as in the coverage tree.
- **One page per file**: its findings with line, check, severity and message.
- **Own copy of gcovr's `base.html` (decided 2026-11-21).** The boost `base.html` shows the Boost C++ Libraries wordmark, a "Created using GCOVR" footer and a Nested/Flat switch whose Flat mode is a coverage view; none of them is a replaceable block. yanga keeps one copy of that file, with gcovr's BSD-3-Clause notice, without those three parts. `style.css` and `gcovr.js` still come from the installed gcovr; the copies written into each report start with gcovr's copyright notice and a pointer to its licence, since a published report passes them on.
- **SARIF locations are URIs.** A file inside the project is a relative URI with a `uriBaseId` for the project root; a file outside it is a `file://` URI.
- **Severities from CodeChecker's table (decided 2026-11-20).** CodeChecker's `config/labels/analyzers/clang-tidy.json` (Apache-2.0 WITH LLVM-exception) is copied into yanga as data, reduced to the severity per check, with its licence notice. A check that is not in the table gets `MEDIUM`.
- **SARIF file next to the HTML.** The report command also writes the findings as SARIF 2.1.0 (`clang_tidy_report.sarif`), for the component and for the variant, so other tools and databases can read them. Each result carries the check as `ruleId`, the file and line, the message, the SARIF `level` (`error` for parse failures, `warning` for findings) and the severity from the table as a property.
- **The Markdown report goes away**, and with it its test `test_report_merges_outputs_once_and_lists_parse_failures_apart`; the HTML and SARIF tests cover the merge, the deduplication and the parse failures.
- **Parse failures** stay their own kind, listed apart from the findings, as today.
- **Failure policy.** Findings never fail the build, as today.
- **In the Sphinx report** the HTML is linked from the component and variant report the same way as the coverage HTML.
- Out of scope: a setting for the theme or the severities, cppcheck, uploading the SARIF file anywhere, the source code shown on the file page.

## Acceptance criteria

- [x] The component and variant clang-tidy reports are HTML, linked from the component and variant report
- [x] As in gcovr's nested coverage report, the sidebar shows the folders and files with findings as a tree, and each folder page (the entry page for the top level) lists its subfolders and files with the number of findings per severity
- [x] A file page lists each finding with line, check, severity and message
- [x] A check that is not in the severity table gets `MEDIUM`
- [x] Parse failures are listed apart from findings
- [x] The component and variant reports also write a SARIF 2.1.0 file with every finding and parse failure, valid against the SARIF 2.1.0 schema
- [x] The usage documentation describes the report
- [x] `pypeline run` is green

## Plan

**Goal:** `clang_tidy_report` writes an HTML report in gcovr's boost theme and a SARIF file, for each component and for the variant. **Spec:** this item.

### Global Constraints

The general rubric, verbatim:

- **Asked for.** Every changed line traces to the item. No feature, option or clean-up the item did not ask for.
- **Existing pattern.** The change does what the repository already does in the same way. No second way of doing one thing.
- **Smallest form.** No abstraction with a single caller, no configuration for a value that never changes, no code for a state that cannot occur.
- **Names.** A name says what the thing is, in the words of the item and the repository.
- **Checks kept.** Validation and safety checks stay, above all at untrusted input, authentication and secrets.
- **Tests that matter.** The tests check the behaviour the acceptance criteria name, not the implementation's details.
- **Docs.** A feature a user can call ships its usage docs. A comment says why or when, not how.
- **Nothing private.** No personal data and no detail of a private setup in a file, a message or a test, also where no pattern scan would catch it.

Repository rules: `AGENTS.md`. No `docs/rubric.md`. gcovr range `>=8.7,<8.9` (boost theme from 8.7, tested with 8.8); YANGA-007 changes the same `pyproject.toml` line, so whichever lands second rebases.

### Review Focus

- A finding in a header outside the project root: shown with its absolute path, not dropped.
- A variant with no findings: the report still renders, with zero counts.
- The same finding reported by two source files (a header): listed once, as today.
- Message text with `<`, `>` or `&` (C++ templates): escaped in the HTML.
- A check not in the severity table: `MEDIUM`.

### Task 1: severities

- 1.a tester: `tests/test_clang_tidy.py`: a known check (`readability-magic-numbers`) gets CodeChecker's severity (`STYLE`), an unknown check gets `MEDIUM`.
- 1.b implementer: `src/yanga/commands/clang_tidy_severities.json`, the check-to-severity map reduced from CodeChecker 6.29.3's `config/labels/analyzers/clang-tidy.json`, with the licence notice in a `NOTICE`-style header file next to it; a lookup in `src/yanga/commands/clang_tidy.py` that reads it with `importlib.resources`, and the package data entry if the build needs one.

### Task 2: SARIF

- 2.a tester: the report command writes `clang_tidy_report.sarif`; it validates against the SARIF 2.1.0 schema (schema file in `tests/data/`, validated with `jsonschema`, added as a dev dependency); a finding has `ruleId`, file, line, message, `level: warning` and the severity as a property; a parse failure has `level: error`.
- 2.b implementer: build the SARIF dict from the parsed findings with the stdlib `json`.

### Task 3: HTML report

- 3.a tester: the report command writes `index.html` plus one page per folder and file into its output directory; the entry page names each folder and file with findings and the counts per severity; a file page lists line, check, severity and message, escaped; parse failures listed apart; a run with no findings renders.
- 3.b implementer: render with Jinja2, extending gcovr's boost `base.html` loaded with `PackageLoader("gcovr", "formats/html/boost")`, with gcovr's `style.css` and `gcovr.js` and the tree data in the form `gcovr.js` reads; two templates of our own (folder page, file page) in `src/yanga/commands/`. The Markdown report goes away.

### Task 4: wiring and docs

- 4.a tester: the generator registers the component and variant HTML as `ReportRelevantHtmlContent` (as the coverage report does in `src/yanga/cmake/gtest.py`) instead of the Markdown `LINT_RESULT`; the report command gets an output directory.
- 4.b implementer: `src/yanga/cmake/clang_tidy.py`; `docs/reference/cmake.md` describes the HTML report, the SARIF file and the severities.

### Gate

`git add -A`, then `pypeline run`. Then build SPLed's Disco variant on gtest with this yanga and look at the report.
