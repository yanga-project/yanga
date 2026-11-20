---
status: Done (2026-11-20)
priority: Low
related: [YANGA-001, YANGA-007]
---

# [YANGA-008] gcovr resolver detects the line anchor format

## Summary

As a developer of a product line, I want the gcovr source link resolver to use the line anchor that the coverage page really has, so that a source link still opens the right line when gcovr's theme changes how it marks lines.

## Description

The gcovr strategy of the source link resolver (YANGA-001) appends a fixed line anchor to the coverage page it finds. Since YANGA-007 that anchor is `#L<line>`, because the boost theme marks a line as `id="L42"`. The github theme, used before, marks it as `id="l42"`. HTML ids are case-sensitive, so a fixed anchor that does not match the theme opens the right page at its top, without an error. That happened during YANGA-007: every link opened its file page, but none scrolled to its line.

The resolver already reads every file page of a coverage report to find its path. The page also holds the anchor of each line, so the resolver can read which form the page uses instead of assuming one.

## Scope decisions

- **The anchor comes from the linked page.** For a link to line N, the resolver uses `L<N>` if the page has `id="L<N>"`, and `l<N>` if it has `id="l<N>"`.
- **Only line-number ids count.** The letter must be followed by digits only: boost pages also have ids such as `id="lightController"` for functions.
- **A line the page does not have.** If the page has neither id, the link still goes to the page, without an anchor, and the build logs a warning naming the file and the line.
- Out of scope: reading the path from the index rows of gcovr's details mode, a setting to choose the theme.

## Acceptance criteria

- [x] A link to a page with `id="L42"` ends in `#L42`
- [x] A link to a page with `id="l42"` ends in `#l42`
- [x] A function id such as `id="lightController"` is not taken for a line anchor
- [x] A link to a line the page does not have goes to the page without an anchor, and a warning names the file and the line
- [x] The usage documentation of the gcovr strategy says that the anchor follows the page
- [x] `pypeline run` is green

## Plan

1. **Branch.** A worktree in `~/dev/tmp/yanga-008` on `feat/yanga-008-anchor-format` from `main`. The item, its status changes and the code go into one commit on that branch. The item has no `autonomy:` key, so nothing is pushed.
2. **Resolver.** While the gcovr strategy reads each file page for its breadcrumb path, it also collects the page's line ids (`id="[lL]\d+"`). For the page it picked, it appends `#L<line>` or `#l<line>`, whichever id the page has; with neither, it returns the page without an anchor and logs a warning. Matching and tree choice stay as they are.
3. **Tests.** In the resolver tests, the test page helper writes line ids. One parametrized test covers `L` and `l`; one test puts a function id on the page and checks it is not taken; one test checks the missing line (no anchor, warning). The existing tests keep their `#L42` expectations.
4. **Docs.** The `gcovr` bullet in the CMake reference says that the anchor follows the page.
5. **Gate.** `git add -A`, then `pypeline run`, green.

No SPLed run: with the boost theme the output is the same `#L<line>` as today, and the tests cover both forms.
