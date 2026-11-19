---
status: Ready
priority: Medium
blocked_by: [YCORE-002]
---

# [YANGA-004] gtest generator reads gtest blocks and builds mockup sources

## Summary

As a component developer, I want the gtest platform to build only my `gtest` testing block, with its mocking settings and its test-only helper sources, so that the same component can carry tests for other frameworks and my helpers neither count for coverage nor clash with generated mocks.

## Description

With YCORE-002 a component declares one testing block per framework. The gtest generator today takes every test source of a component, reads mocking from the component's testing config, and has no place for test-only helper code: in the production sources it counts for coverage, and in the test sources automock generates mocks for the symbols it defines, which then clash. This is the first yanga part of a change across yanga-core and yanga; the design is in the planning vault's epic SB-006.

## Scope decisions

- **Only `gtest` blocks.** The gtest generator ignores blocks of any other framework. A component without a `gtest` block is only compiled, as a component without tests is today.
- **Mocking from the block's `config`.** The block's `config.mocking` is merged with the platform's generator config, as the component's mocking is today.
- **Mockup sources.** They are compiled without coverage, linked into the component's test executable, and automock does not generate mocks for the symbols they define.
- **Report.** The component report lists the test sources of the `gtest` block. The gtest generator puts the sources it built on the `TestResultFile` it registers, and the report lists those, so the report generator stays free of framework names.
- **Mocking leak fixed.** Each component's mocking is merged into a new object; one component's mocking no longer carries over to the components generated after it. It goes into the changelog as a fix.
- **Mockup sources are C fakes.** A C++ mockup that uses gmock or the standard library is not supported; the usage docs say so.
- **Mockups alone are no tests.** A `gtest` block with `mockup_sources` but no `sources` is not testable, and its mockups are ignored.
- Out of scope: generators for other frameworks, the variant test (YANGA-005).

## Acceptance criteria

- [ ] A component with a `gtest` block and a block of another framework builds and runs only the `gtest` tests on the gtest platform
- [ ] `mocking` in the block's `config` is applied as the component mocking is today
- [ ] A function defined in a mockup source and called by the production code is linked from the mockup source, with no generated mock for it
- [ ] Mockup sources do not appear in the component's coverage
- [ ] The kickstart templates use the block form, and a project made from them builds and reports as before
- [ ] The usage documentation shows a component with a `gtest` block, mockup sources and `config`
- [ ] `pypeline run` is green

## Dependencies and risks

- **YCORE-002 sets the data this item reads.** `Component.testing` is the list of resolved blocks (`framework`, `sources` and `mockup_sources` under the component root, `config` as a plain dict); `Component.test_sources` lists the sources of all blocks; `Component.is_testable(framework=None)` is a method, no longer a property; `MockingConfig` stays in yanga-core, and the gtest generator reads the block's `config["mocking"]` into it. yanga then needs a yanga-core floor bump and a relock.
- **The old forms are dropped in yanga-core.** `testing: {sources, mocking}` fails to load and a leftover `test_sources` is ignored. yanga has no fallback either: its kickstart templates and docs move to the block form. This is a breaking change for projects; yanga is in alpha, so it needs no major version.
- **Shared generator config is changed in place today.** `_determine_component_generator_config` assigns the merged mocking into the generator's own config object, so the mocking of one component is still set for every component generated after it. This item rewrites that function to read the block `config` and fixes the leak.
- **Mockup objects in the partial link.** Their own undefined symbols become mock candidates too. That is right for a C fake that calls into another component. A C++ mockup that uses gtest or the standard library adds C++ symbols that no productive source declares, and clanguru in strict mode fails on symbols it cannot find. Hence mockups are C fakes only.
- **A mockup that also defines a productive symbol** makes the partial link fail with a duplicate symbol error. Mockups fill symbols the component does not define; they do not replace its code.
- **No end-to-end test runs the gtest platform.** `test_yanga_mini` builds only `host_exe`, so the evidence for linking and coverage is a manual build of a `yanga init` project on the gtest platform.

## Plan

1. **yanga-core floor.** Raise the yanga-core floor in `pyproject.toml` to the release with YCORE-002, with `uv lock`. Check: `component.is_testable` and `component.testing.mocking` are the only call sites that break, and the next tasks replace them.
2. **Select the gtest block.** In the gtest generator, a component is testable when `component.is_testable("gtest")`; the test executable takes that block's sources only. The container's subcomponent test targets use the same check, so a container never depends on a test target that was not generated. Touches `src/yanga/cmake/gtest.py`, `tests/test_cmake_gtest.py`. Check: a parametrized test with a component that has a `gtest` and a `tessy` block (executable sources are only the gtest ones) and one with only a `tessy` block (compiled only, no test, mockup or coverage target).
3. **Mocking from the block `config`.** Read the block's `config["mocking"]` into `MockingConfig` and merge it over the platform mocking with `merge_configs` into a new object, leaving the generator config untouched. The function takes a block, not a component, so YANGA-005 can call it for the variant's block. Touches `src/yanga/cmake/gtest.py`, `tests/test_cmake_gtest.py`. Check: the existing override test passes on a block, and a second component without mocking gets the platform mocking, not the first component's.
4. **Build the mockup sources.** For a testable component with `mockup_sources`, add an object library `<component>_mockups`, built by a function that takes the block's `mockup_sources` and a target name, so YANGA-005 can reuse it for the variant's block, compiled with `-ggdb` and without `--coverage`, with the same include directories as the `_PC` library. The partial link takes its objects next to the `_PC` objects (`$<TARGET_OBJECTS:...>` of both, and it depends on both), so clanguru, which mocks the undefined symbols of the partial object, does not mock what the mockups define. The test executable links the mockup library. With automock off, the library is only linked. Touches `src/yanga/cmake/gtest.py`, `tests/test_cmake_gtest.py`. Check: unit tests on the generated elements (library without `--coverage`, partial link command and depends, executable libraries), parametrized over automock on and off.
5. **Report the gtest test sources.** `TestResultFile` gets the test sources; the gtest generator fills them with the `gtest` block's sources, and the component report lists the sources of the component's registered test results instead of `component.test_sources`. Touches `src/yanga/cmake/sphinx_test_report.py`, `src/yanga/cmake/gtest.py`, `src/yanga/cmake/reports.py`, `tests/test_cmake_reports.py`. Check: a component with a `gtest` and a `tessy` block lists only the gtest sources.
6. **Usage docs.** Show a component with a `gtest` block, `mockup_sources` and `config.mocking` in `docs/how-to/add-component-tests.md`, with the note that mockups are C fakes, and move the mocking override in `docs/reference/product.md` and `docs/reference/cmake.md` to the block form. Move the kickstart templates (`src/yanga/kickstart/templates/`, the `testing:` of `mini/src/yanga.yaml` and any other) to the block form. Check: `pypeline run --step Docs --single` builds.
7. **Manual evidence on the gtest platform.** In a scratch `yanga init` project, give `greeter` a `gtest` block with a mockup source that defines a function the production code calls, and a block of another framework, then build the gtest platform. Check: the executable runs only the gtest tests, `mockup_greeter.h` has no mock for that function, the coverage report lists no mockup file, and a project made from the migrated templates builds and reports as before.
8. **Gate.** `git add -A`, then `pypeline run`. Check: green.
