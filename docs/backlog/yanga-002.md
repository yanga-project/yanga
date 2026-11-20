---
status: Done (2026-11-20)
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

- [x] An integration component gets no analysis step for the sources of the components it integrates
- [x] A source file is analysed once in a variant, under the component that declares it
- [x] The docs of the clang-tidy generator say that integrated sources are analysed under their own component
- [x] `pypeline run` is green

## Plan

**Goal:** the clang-tidy generator analyses `Component.own_sources` (yanga-core 0.17.0, YCORE-001) instead of `sources`. **Spec:** this item.

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

The repository has no `docs/rubric.md`. Repository rules: `AGENTS.md` (stage everything before `pypeline run`; after a dependency change run `uv lock` and stage `uv.lock`).

### Review Focus

- An integration component that declares no production source of its own gets no analysis step and no `<component>_lint` target.
- An integration component with its own source is analysed for that source only.
- The integrated components, when selected, keep their own analysis steps.

### Task 0: yanga-core floor

`pyproject.toml`: `yanga-core>=0.17,<1`; `uv lock`; recreate the venv. Checked by `.venv/bin/python -c "from yanga_core.domain.components import Component; Component('x', __import__('pathlib').Path('.')).own_sources"`.

### Task 1.a (tester)

`tests/test_clang_tidy.py`: a new parametrized case of `test_generate_one_clang_tidy_step_per_source`, or one flat test next to it, built with `make_execution_context` from `tests/conftest.py`: components `tcp` (`tcp.cpp`), `udp` (`udp.cpp`) and an integration component `test_net` with `integrates: [tcp, udp]`, all selected. Expected: one `clang_tidy` step per file of `tcp` and `udp` (2 in total), no step for `test_net`, and `lint` plus the two component lint targets only. A second case where `test_net` also declares `glue.cpp`: 3 steps, one of them for `test_net`. Run `.venv/bin/python -m pytest tests/test_clang_tidy.py`: the new cases fail.

### Task 1.b (implementer)

`src/yanga/cmake/clang_tidy.py`, `generate`: iterate and skip on `component.own_sources` instead of `component.sources`; update the comment above the skip (containers and integration-only components have no own sources). `docs/reference/cmake.md`, `ClangTidyCMakeGenerator`: one bullet that an integration component is analysed only for its own sources; the files it integrates are analysed under their own component. No change to the files of 1.a.

### Gate

`git add -A`, then `pypeline run`.
