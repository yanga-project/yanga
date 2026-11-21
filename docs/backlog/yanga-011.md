---
status: Done (2026-11-22)
priority: Medium
blocked_by: [YCORE-005]
related: [YANGA-006, YANGA-009]
---

# [YANGA-011] Generators tag their report entries and build the merged reports

## Summary

As the owner of a product line report, I want every report entry from yanga's generators tagged with its level, kind and component, and the merged results built per container and over all components and all containers, so that my template can place each result where I want it and every result kind has the same levels.

## Description

yanga's generators register report entries without saying what they are beyond a file type. Coverage has two variant-level pages ("Coverage Report", the merge of all component tests, and "Variant Test Coverage", the variant test) that a reader cannot tell apart. Tests and static analysis have no merged pages per container or over all containers. YANGA-006 asked for this split for coverage only; this item replaces it with one model for all kinds, using the tags of YCORE-005.

## Scope decisions

- **Every generator tags its entries** from the vocabulary of YCORE-005: level (`component`, `container`, `variant`, `overall`, `merged`), kind (`docs`, `sources`, `test`, `coverage`, `static-analysis`, `configuration`) and the component name on its own entries. Build targets and object dependencies stay untagged.
- **Results per level, for tests, coverage and static analysis where they exist**: per component; per container (a container's subcomponents together, and an integration component's own test); all components merged; all containers merged; the variant test; everything merged.
- **Coverage never mixes unit and integration counters** in a component or all-components page; integration tests count only at container, all-containers and overall levels (YANGA-006's first decision).
- **A level with nothing in it registers no entry** (no empty page).
- **Kickstart template** (2026-11-22, from the review of the built SPLedY report): the variant report of a project made with `yanga init` uses chapters by tags (components, containers, feature configuration, reports, untagged last), so that pages with the same title do not repeat at its top level.
- Out of scope: project templates (SPLED-006), a `platform` tag (needs the selection origin, which yanga-core does not keep).

## Acceptance criteria

- [x] Every report entry of the gtest, clang-tidy, test report, docs and feature generators carries its level, kind and, for component entries, the component name
- [x] Test results, coverage and static analysis exist per component, per container, merged over all components, merged over all containers, for the variant test where there is one, and merged over everything; static analysis only where it has sources
- [x] A component page and the all-components page show only unit test coverage
- [x] A variant without containers or without a variant test registers no entry for that level
- [x] The usage documentation lists the tags each generator sets
- [x] `pypeline run` is green
