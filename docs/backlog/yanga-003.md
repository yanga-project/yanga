---
status: Open
priority: Medium
blocked_by: [YCORE-001]
---

# [YANGA-003] Tool-neutral findings model for the static analysis report

## Summary

The static analysis report groups findings per component and names the external project a component comes from, so that each component's developer sees the findings they must fix, and findings in external code can go upstream as fix requests.

## Description

The clang-tidy report command converts the clang-tidy console output with the cppcheck report model. That model is specific to one tool and has no place for the external project. A second analysis tool would need its own model again. With YCORE-001 the resolved component carries its external project. This is the second yanga part of a change across yanga-core and yanga; the design is in the planning vault's epic SB-005.

## Scope decisions

- **One findings model for all tools.** clang-tidy is the first tool that writes it; the cppcheck generator moves to it only when it is enabled again, which is not part of this item.
- **No file format yet.** The model is used in memory to write the Markdown report. A file format (SARIF, the Static Analysis Results Interchange Format, is the candidate) is picked when a second tool comes.
- **Grouping.** Findings are grouped per component. Product and platform components are not split, because the analysis runs on one platform only.
- **External project.** External code is analysed like any other product code. A component from an external project shows the project's name in its report section.
- **Parse failures.** They stay their own kind, listed apart from findings, as today.
- **Failure policy.** Findings never fail the build, as today.
- Out of scope: SARIF output, a generic static analysis config, cppcheck.

## Acceptance criteria

- [ ] The clang-tidy report is written from the tool-neutral findings model, not from the cppcheck model
- [ ] The variant report groups findings per component
- [ ] A component from an external project names that project in its report section
- [ ] Parse failures are listed apart from findings
- [ ] The component and variant report look as before for a component that is not external
- [ ] `pypeline run` is green
