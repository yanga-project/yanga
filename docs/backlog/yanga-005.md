---
status: Done (2026-11-19)
priority: Medium
blocked_by: [YCORE-002, YCORE-003, YANGA-004]
related: [YANGA-006]
---

# [YANGA-005] Variant test target for gtest blocks

## Summary

As a developer of a product line, I want to write gtest tests for a whole variant, so that I test what the variant ships without declaring an extra integration component in every variant.

## Description

With YCORE-002 a variant can declare testing blocks. Today the only test of more than one component is an integration component, which compiles the sources of the components it integrates a second time and must be selected in every variant that needs it. This is the second yanga part of a change across yanga-core and yanga; the design is in the planning vault's epic SB-006.

## Scope decisions

- **One variant test executable for the variant's gtest block.** Its sources and mockup sources are linked against the object libraries of all selected components; nothing is compiled a second time.
- **Mocking.** As for a component, automock fills only what the selected components leave undefined, such as platform adapters. Mocks between components inside the variant are out of scope.
- **Results.** The variant test's coverage and JUnit result are registered for the variant report, as a component's are for the component report.
- **Only on a platform whose generator handles the framework.** A variant without a `gtest` block builds exactly as today.
- Out of scope: test sources per platform on a variant, other frameworks, replacing the integration component.

## Acceptance criteria

- [x] A variant with a `gtest` block gets a test target that builds and runs its tests against all selected components
- [x] The variant report shows the variant test's results and coverage
- [x] A variant without `testing` builds and reports exactly as before
- [x] The usage documentation shows a variant with a `gtest` block
- [x] `pypeline run` is green

## Findings

What the code does today (yanga v2.46.0, yanga-core v0.13.1) and what that means for the variant test.

- **Linking the object libraries works.** Each component has an object library `<component>_PC_lib` with its production sources (an interface library when it has no sources; a container has none). A variant test executable can link all of them, as the component test links its own. The include directories are already those of all selected components, so the test sources see every header.
- **The component mockups must not be linked.** The mockup of a component is generated from its own objects only, so it defines every function the component calls in another component. Two of them define the same symbols, and each defines symbols that the real objects define too. The variant test gets one mockup of its own: clanguru on a partial link of all component objects, so only what the whole variant leaves undefined is mocked. A variant that leaves nothing undefined must still get valid (empty) mockup files.
- **Coverage data is shared.** The objects are compiled with `--coverage`, so each object writes its counters to one `.gcda` file next to it, whichever executable runs it. The component test and the variant test run the same objects, so each one's counters land in the other's coverage. Both test targets are in `ALL`, and ninja does not order them, so the component coverage would change from build to build. The variant test runs with `GCOV_PREFIX`, so its `.gcda` files go to its own directory, and the `.gcno` files are copied there for gcovr. A second compile is not needed.
- **`main()` hides the tests.** If a selected component defines `main()` (in SPLed the `main` component does), the linker takes it and does not pull `main` from `gtest_main`. The executable then runs the product, not the tests, with no link error. So `main` belongs to a platform component, not to a variant component: the `main` of the PC differs from the `main` of the MCU. yanga-core supports this today (a platform has its own `components`, and a variant can add components per platform), so the gtest platform selects no `main` and the variant test needs no config for it. SPLed moves its `main` component into its MCU platform before the epic check.
- **JUnit result.** `TestResultFile` with a variant-scope target works with the report config as it is: `GenerateReportConfig` puts entries without a component name into `variant_data`, and the variant page lists their test results and HTML content. `SphinxTestReportCMakeGenerator` takes the page name and report ID from the component name, which is empty for a variant: it must use the variant name.
- **Coverage in the report.** The variant "Coverage Report" is a gcovr merge of the component tracefiles that `gcovr_config_variant` finds in the report config. A variant-scope tracefile is not picked up there. The variant test's coverage gets its own page, "Variant Test Coverage", and the merged "Coverage Report" stays the merge of the component tests, so a variant without testing reports exactly as before. YANGA-006 later groups the coverage pages (components, integration tests, all) and places the variant test there.
- **Target names.** A variant-scope `UserRequest` target name has no prefix: `UserRequest(VARIANT, TEST)` is `test`, `UserRequest(VARIANT, MOCKUP)` is `mockup`. `coverage` is already the merged variant coverage. CMake reserves `test` when testing is enabled (policy CMP0037), and googletest may enable it in its own directory.
- **Dependencies.** YCORE-002 for the variant's blocks: `ExecutionContext.variant_testing` holds the variant's resolved blocks, with paths found next to the variant's file, then in the project root, and empty when the variant has no `testing`. YCORE-002 also refuses a second block of the same framework in one list, so a variant has at most one `gtest` block. YANGA-004 reads a block's `config.mocking` and builds `mockup_sources`; the variant test needs the same two things for its block, so YANGA-005 comes after YANGA-004.
- **yanga-core floor.** The yanga-core release with YCORE-002 drops the old `testing` forms and breaks the current gtest generator (`is_testable` becomes a method, `testing.mocking` is gone). YANGA-004 raises the floor and adapts those call sites; YANGA-005 builds on that state.
- **No real build in the tests.** yanga's tests only check the generated CMake; no test builds a gtest platform. The risks above (duplicate symbols, `.gcda` sharing, `main`) only show in a real build. They are checked by hand on a scratch project (tasks 1 and 8), with SPLed as the epic's check; no automated end-to-end test is added, because it needs a googletest install and is slow.

## Plan

1. **Spike the link and the coverage split.** In a scratch project from `yanga init` with a gtest platform and two components (one calls a platform function) and a `main` component on another platform only, link one variant test against all object libraries by hand. Check: no duplicate symbols with the variant mockup, the `gtest_main` entry point runs (the `main` component is not linked), and the variant run writes its `.gcda` files away from the component ones (`GCOV_PREFIX`) while gcovr still reads them. Also check whether `test` is free as a target name next to googletest. Touches nothing in the repo; the result decides tasks 3 and 5.
2. **Read the variant's gtest block.** In `gtest.py`, take the `gtest` block from `execution_context.variant_testing`; the variant has a test only when that block has `sources` (mockups alone are no tests, as in YANGA-004). Read its `config["mocking"]` with the function YANGA-004 writes for a block, so the generator config is not changed. Checked by a unit test in `tests/test_cmake_gtest.py`, parametrized over no `testing`, a block of another framework, and a `gtest` block with only `mockup_sources`: each generates exactly the same elements as before.
3. **Variant test executable and run target.** In `gtest.py`, add the executable with the block's sources, linked to every non-container component's object library, to its own mockup, and to a mockup sources library built with YANGA-004's function (no `--coverage`), output in its own build directory; a run target that writes its JUnit file; the test target in `ALL`. Name: the executable `<variant>_variant_test` in `<build>/variant_test/`, the target `test` (or `variant_test` if task 1 finds `test` taken). Checked by unit tests on the generated elements.
4. **Variant mockup.** In `gtest.py`, run the existing `CMakeMockupCreator` steps on a partial link of all component objects and the variant's mockup sources objects (as YANGA-004 does for a component, so nothing the mockup sources define is mocked), into the variant test directory, with the variant's mocking config. Checked by a unit test: the clanguru command lists every component's sources and the variant test links no component mockup.
5. **Variant test coverage.** In `gtest.py` (and `gcovr.py` if needed), run gcovr on the variant test's own `.gcda` files as task 1 decided, with all component sources as filter, and register the HTML as its own "Variant Test Coverage" page in the variant report; the merged "Coverage Report" is unchanged. Checked by unit tests on the commands and the registered `ReportRelevantFiles`, and in the scratch project: a component's coverage is the same with and without the variant test.
6. **JUnit page for the variant.** Register a `TestResultFile` with the variant test target and, as YANGA-004 adds, the block's test sources. In `sphinx_test_report.py`, name the page and the report ID after the variant when the target has no component. Checked in `tests/test_cmake_sphinx_test_report.py`.
7. **Usage docs.** Add a variant section to `docs/how-to/add-component-tests.md`: the `gtest` block on a variant, what is mocked, where the results appear. Checked by the Docs step of `pypeline run`.
8. **Real build.** Build and report the scratch project from task 1 with the finished generator: the variant test runs, its results and coverage are in the variant report, and the component coverage is unchanged. Then `pypeline run` green.
