---
status: Open
priority: Medium
blocked_by: [YCORE-001]
---

# [YANGA-002] clang-tidy analyses only a component's own sources

## Summary

Each source file is analysed once, under the component that declares it, so that its findings reach the developer responsible for that component and the static analysis report does not list the same finding twice.

## Description

The clang-tidy generator runs one analysis step per source in a component's `sources`. An integration component (`integrates:`) also has the sources of the components it integrates in `sources`, so their files are analysed again under the integration component. On SPLed's `gtest` platform this repeats the findings of `spled`, `rte`, `brightness_controller` and `light_application` under `test_integrations_spled`. With YCORE-001 the resolved component records which sources it declares itself. This is the first yanga part of a change across yanga-core and yanga; the design is in the planning vault's epic SB-005.

## Scope decisions

- **Own sources only.** The developer of a component fixes its files, so integration components are not analysed for the files they integrate. The generator analyses the sources a component declares itself. A component that declares no production source gets no analysis step and no component report section.
- **Header filter.** It still uses the component's include directories, integrated ones included: they only decide which header warnings are shown.
- Out of scope: the findings model and report layout (YANGA-003), rerunning the analysis when a header changes.

## Acceptance criteria

- [ ] An integration component gets no analysis step for the sources of the components it integrates
- [ ] A source file is analysed once in a variant, under the component that declares it
- [ ] The docs of the clang-tidy generator say that integrated sources are analysed under their own component
- [ ] `pypeline run` is green
