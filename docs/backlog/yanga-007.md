---
status: Done (2026-11-20)
priority: Medium
related: [YANGA-001, YANGA-006]
---

# [YANGA-007] Coverage reports browsable as a file tree

## Summary

As a developer of a product line, I want the coverage reports to show the files as a folder tree, with the common path shown once, so that I can find a file by browsing its folders instead of scanning one long list of full paths.

## Description

The component and variant coverage reports are written by gcovr in its details mode: one page with a flat list of every file, each shown with its full path. In a variant with many components the list is long and the paths repeat the same folders.

gcovr 8.7 added the `boost.green` and `boost.blue` HTML themes. Together with gcovr's nested mode (`--html-nested`), they show a sidebar with the files as a folder tree: folders open and close, folders with a single child are merged into one row, and a switch shows the flat list again. In details mode the boost themes show no tree. This was checked with gcovr 8.8 on the Disco variant of SPLed on the gtest platform.

In nested mode the entry page of a report lists only the top-level folders; the files are listed on one page per folder. The source link resolver of YANGA-001 reads the file rows only from the entry page of each component coverage report. With nested mode alone, it would find no files, and every source link would become plain text without an error.

spl-core makes the same change on its branch `feat/coverage-tree-view`.

## Scope decisions

- **Nested mode with the `boost.blue` theme** for the component and the variant coverage reports. The entry page stays `index.html`, so the links from the report pages do not change.
- **gcovr floor `>=8.7`**, the first release with the boost themes.
- **The resolver reads every page of a coverage report**, not only the entry page, and keeps its matching rules from YANGA-001 (path-end match, same page name is one file, the tree of the source's component wins).
- **The file path comes from the page of the file.** In nested mode a file row shows only the file name (`light_controller.c`), so the rows no longer carry the path. Each file page names its path in the breadcrumb, as the title of the current entry: `<span class="current" title="light_controller/src/light_controller.c">`. This is the same shortened path the details mode showed in its rows. The resolver takes the path from there and the page name from the file name. A folder page has the same entry with a path that ends in `/`, so it never matches a source path. Checked with gcovr 8.8 on the Disco variant of SPLed.
- **Line anchors are `#L<line>`.** The boost theme marks a line as `id="L129"`, where the github theme used `l129`; the resolver writes the capital `L`.
- Out of scope: a setting to choose the theme or to keep the flat layout, custom CSS for the report.

## Acceptance criteria

- [x] In a component report and a variant report built from SPLed on the gtest platform, each coverage report shows the files as a folder tree in its sidebar
- [x] The source links of YANGA-001 still lead to the coverage page of the file at the declaration's line
- [x] A test fails if the resolver finds no file rows in a nested coverage report
- [x] The usage documentation describes the tree view
- [x] `pypeline run` is green

## Plan

1. **Branch.** A worktree in `~/dev/tmp/yanga-007` on `feat/yanga-007-coverage-tree` from `main`. The item has no `autonomy:` key, so nothing is pushed; the branch waits for your review.
2. **gcovr calls.** In the gtest CMake generator, the three gcovr HTML runs (component coverage, variant test coverage, merged variant coverage) use `--html-nested --html-theme boost.blue` instead of `--html --html-details`. The comments that name `--html-details` name the nested mode. Checked by the existing CMake generator tests, updated to the new flags.
3. **gcovr floor.** `gcovr>=8.7,<9` in `pyproject.toml`, then `uv lock`, as yanga's AGENTS.md says.
4. **Resolver.** `_gcovr_strategy` reads every `coverage/<tree>/*.html`, takes the path from the breadcrumb entry and the page name from the file name, and skips pages whose path ends in `/`. The matching rules stay as they are. The test helper writes file pages with that breadcrumb instead of rows in `index.html`; one new test checks that a folder page is not taken for a file. Checked by `tests/test_source_links_command.py`.
5. **Docs.** One paragraph on the tree view where the coverage pages are described in the usage docs.
6. **Gate.** `git add -A`, then `pypeline run`, green.
7. **SPLed.** Install the branch editable in spledy, build the Disco variant report on gtest, and check in the HTML: the sidebar holds the folder tree (criterion 1), and a declaration in a source docs page links to its coverage page with `#L<line>` (criterion 2). spledy's own files stay as they are.
