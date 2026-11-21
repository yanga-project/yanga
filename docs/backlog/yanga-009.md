---
status: Done (2026-11-22)
priority: Medium
blocked_by: [YCORE-004]
related: [YANGA-006]
---

# [YANGA-009] Variant report fixes found in the SPLedY report

## Summary

As a reader of a variant report, I want each component page to show only that component's findings, paths relative to the project root, test results expanded, test and production sources linked to the code host on CI, and the build targets page titled "Build Targets", so that the report reads the same locally and on CI and every link leads to the right place.

## Description

Found in the published SPLedY report (yanga 2.49.0):

- **Component clang-tidy page.** The component's static analysis report is written inside the component's build folder but registered under the same report path as the variant's, so the component page opens the variant page with every component's files. The component report is never copied into the variant report. Coverage avoids this with one folder per component.
- **Absolute paths.** The component coverage reports and the variant test coverage use the object directory as gcovr's root, so sources outside it show as absolute runner paths (`/home/runner/work/...`). The variant coverage report already uses the project root. The test report pages also show the JUnit file as an absolute path.
- **Collapsed test results.** sphinx-test-reports collapses results unless the directive says otherwise, and the generated test report page does not.
- **No code host links.** The source link resolver knows only `gcovr` and `vscode`. `gcovr` finds only files with coverage, so test sources fall back to plain text; a platform without coverage (Zephyr) has no strategy for CI at all. A code host strategy was left out of YANGA-001 because nothing handed over the repository URL; YCORE-004 detects it.
- **Title.** The build targets page is titled "Target Dependencies Documentation".

## Scope decisions

- **Component clang-tidy reports go into `clang_tidy/<component>`** of the variant report, copied the way the component coverage reports are.
- **gcovr's root is the project root** for the component coverage and the variant test coverage, as for the variant coverage.
- **Results expanded for every project**: the generated test report directive sets `:collapse: false`.
- **A `repository` strategy** links to `<repository URL>/blob/<commit>/<path>#L<line>`, with the URL and the commit from yanga-core (YCORE-004). It is meant for the `ci` profile: locally an unpushed commit gives a dead link. Without a URL it resolves nothing, so the next strategy or plain text applies.
- Out of scope: the coverage page grouping of YANGA-006, moving the generated report pages out of the build tree (their URLs show `.yanga/build/...`).

## Acceptance criteria

- [x] A component's static analysis page shows only that component's files, and the variant report holds a copy under `clang_tidy/<component>`
- [x] Component coverage and variant test coverage show source paths relative to the project root
- [x] The test report pages show the JUnit file relative to the project root
- [x] Test results are expanded when the page opens
- [x] With the `repository` strategy, a production source and a test source link to the code host at the build's commit and line; with no repository URL they fall back to the next strategy or plain text
- [x] The build targets page is titled "Build Targets"
- [x] The usage documentation describes the `repository` strategy
- [x] `pypeline run` is green
