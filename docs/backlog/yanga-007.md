---
status: Open
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
- Out of scope: a setting to choose the theme or to keep the flat layout, custom CSS for the report.

## Acceptance criteria

- [ ] In a component report and a variant report built from SPLed on the gtest platform, each coverage report shows the files as a folder tree in its sidebar
- [ ] The source links of YANGA-001 still lead to the coverage page of the file at the declaration's line
- [ ] A test fails if the resolver finds no file rows in a nested coverage report
- [ ] The usage documentation describes the tree view
- [ ] `pypeline run` is green
