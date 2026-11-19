---
status: Open
priority: Medium
related: [YANGA-005]
---

# [YANGA-006] Coverage reports grouped by component kind

## Summary

As a developer of a product line, I want the variant report to show coverage per component, merged over the components, merged over the integration tests, and over all tests, so that the coverage of a unit test is not mixed with the coverage of a test that runs many components.

## Description

Today the variant "Coverage Report" is one gcovr merge of the tracefiles of all component tests. An integration component's test runs the sources of the components it integrates, so its counters raise their coverage in that merge. With YANGA-005 the variant test is a second kind of test that runs many components; it gets its own page there until this item places it.

The variant report should show:

- the coverage of each component under that component, as today;
- a merged report of the component unit tests;
- a merged report of the integration tests: integration components (containers) and the variant test;
- an overall report of all tests.

## Scope decisions

- **Each test keeps its own coverage data.** A merge combines tracefiles; no test's counters land in another test's files (YANGA-005 gives the variant test its own `.gcda` files).
- **Integration components are told apart from unit components** by where their sources lie: a component whose sources lie in another component's directory counts as an integration component.
- Out of scope: coverage thresholds, coverage per platform.

## Acceptance criteria

- [ ] Each component page shows only the coverage of that component's own test
- [ ] The variant report has a merged components page, a merged integration page and an overall page
- [ ] The variant test of YANGA-005 is in the integration and overall merges
- [ ] A variant without integration components or variant test shows no empty integration page
- [ ] The usage documentation describes the coverage pages
- [ ] `pypeline run` is green
