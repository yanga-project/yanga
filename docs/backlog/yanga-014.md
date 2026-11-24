---
status: Done (2026-11-24)
priority: Medium
blocked_by: [YANGA-013]
---

# [YANGA-014] Traceability for pytest tests

## Summary

As a developer on a yanga product line, I want my pytest test specifications to appear as needs in the component and variant reports, so that each spec links to the requirements it tests and to its pytest result, as gtest specs do today.

## Description

A gtest test spec is a `@trace {{ gtest.test }}` doc comment above the `TEST`. yanga's `ReportCMakeGenerator` renders every test source a test generator registers with its results through `clanguru docs` onto the component's Sources page, which turns the doc comment into a `test` need. The project's `results` link rule then links the need to its JUnit result, and a schema rule fails the build for a spec without a result.

pytest tests (YANGA-013) have none of this. `PytestCMakeGenerator` registers its results with no test sources, so the report renders no `.py` file, no pytest spec becomes a need, and nothing links to the specs or to the pytest results. `clanguru docs` reads C only.

This item is part of the epic SB-009 (pytest test framework for yanga).

## Scope decisions

- **C stays with clanguru.** It parses with libclang and the compile database, so a variant's report shows only the needs its features keep. Rejected: sphinx-codelinks (useblocks) for C and Python together, because it parses with tree-sitter, which does not run the C preprocessor, so it would show needs from disabled `#ifdef CONFIG_...` blocks.
- **Python test sources are rendered by a Sphinx extension.** A test spec is a need directive in the test function's docstring, and the report renders the test module with the extension, so the directive becomes a need. Candidates: `sphinx.ext.autodoc` (part of Sphinx; imports the module, so the test library and the binding must be built before the docs) and `sphinx-autoapi` (reads the source without importing it). A short spike on one SPLedY component chooses; the choice and its reason are written into this item. The human approved both candidates in advance (2026-11-24), so the build does not wait for the choice.
- **pytest registers its test sources** with its results, as gtest does, and the report decides per file how to render it: `clanguru docs` for C and C++, the Python extension for `.py`.
- **The title of a pytest spec comes from a placeholder**, as `{{ gtest.test }}` does for gtest, so the author writes no test name by hand. The spike settles the placeholder and the form of the name that matches pytest's JUnit `classname` and `name`.
- **Spike result (2026-11-24): `sphinx.ext.autodoc`, placeholder `{{ pytest.test }}`, title `<module>.<function>`.** The report page of a registered `.py` test source holds `automodule` of the module's dotted path relative to the project root, with `:members:`, so only test functions with a docstring appear. autodoc imports the module; the report runs after the tests, so the test library and the binding exist, and yanga puts the project root and each pytest scope's build folder on `PYTHONPATH` for the report build. A yanga Sphinx extension, which the project lists in its `conf.py`, loads autodoc and replaces `{{ pytest.test }}` in a docstring with `<module>.<function>` (for example `components.light_controller.test.test_light_controller.test_power_on_turns_the_light_green`), which is pytest's JUnit `classname` plus `.` plus `name` without the `[params]` of a parametrized test, because pytest runs in the project folder. The `results` rule matches `classname == title.rpartition('.')[0] and case.split('[')[0] == title.rpartition('.')[2]`; checked with sphinx-needs and sphinx-test-reports: the spec links every result of a parametrized test and the schema rule passes. Rejected: `sphinx-autoapi`, because it does not run without a project-wide `autoapi_dirs` and writes its own page tree, so it cannot place one registered test file on a component's Sources page. autodoc is part of Sphinx, so the report needs no new dependency.
- **The `results` link rule and the schema rule belong to the project** (its `conf.py`), as for gtest. The yanga docs show the rule for pytest names.

## What users see

- **pytest test sources on the component's Sources page**, with their test specs as needs. Not breaking: new pages only. UAT: yes, through SPLED-008. Why: nothing renders Python test sources today. Approved by the human (2026-11-24)
- **A title placeholder for pytest test specs** (its name settled by the spike). Not breaking: new. UAT: yes, through SPLED-008. Why: the author must not write test names by hand. Approved by the human (2026-11-24); the spike's concrete choice is written into Scope decisions.
- **A new Sphinx extension in the report build** (autodoc or sphinx-autoapi, settled by the spike). Breaking if it is a new dependency of the project's docs environment; the release notes name it. UAT: no. Why: Python docstrings need a Python-aware renderer. Approved by the human (2026-11-24); the spike's concrete choice is written into Scope decisions.

## Out of scope

Moving C extraction away from clanguru; source docs for Python code that is not a test registered with results.

## Acceptance criteria

- [x] The spike's choice (extension, placeholder, name form) is written into this item's Scope decisions with its reason. Check: this item.
- [x] `PytestCMakeGenerator` registers its test sources with its results, for a component, an integration component and a variant. Check: yanga's CMake element tests in `pypeline run`.
- [x] The report renders a registered `.py` test source with the chosen extension and a C or C++ source with `clanguru docs`; a need directive in a test function's docstring becomes a need on the component's Sources page. Check: a yanga report test in `pypeline run`.
- [x] The docs show how to write a pytest test spec and the `results` rule for pytest names. Check: the docs build in `pypeline run`.

## Plan

1. Spike on SPLedY's `light_controller` with the YANGA-013 test library: both extensions, a `.. test::` need in a docstring, the placeholder for the title, and a `results` rule that matches pytest's JUnit names. Write the choice and its reason into Scope decisions.
2. `PytestCMakeGenerator` registers its test sources (component, integration component, variant). Check: CMake element tests.
3. `ReportCMakeGenerator` renders each registered source by its suffix, `.py` with the chosen extension. Check: a report test.
4. Docs: the pytest test spec and the `results` rule in `docs/how-to/add-component-tests.md`. Check: docs build.
