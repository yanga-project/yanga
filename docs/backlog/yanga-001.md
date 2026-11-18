---
status: In Progress
priority: Medium
blocked_by: [CLG-016]
---

# [YANGA-001] Resolve source links in the reports

## Summary

As the author of a yanga SPL on the gtest platform, I want the `source:` links that clanguru writes into the source docs to point at the declaration's line in the coverage report, so that I can go from a function's documentation to its coverage in one click.

## Description

With CLG-016, `clanguru docs --source-links` writes a `[<path>:<line>](source:<path>#<line>)` link into every declaration section. yanga builds the component and variant reports and knows where the coverage report lands, so it is the place that turns those links into real URLs. Today yanga neither asks clanguru for the links nor resolves them. This is the middle part of a change across clanguru, yanga and SPLed; the design and the checks against a built SPLed report are in the planning vault's epic SB-004.

## Scope decisions

- **Switch.** `ReportCMakeGenerator`'s `config:` gets a bool `source_links` (default false, so existing projects do not change). With it on, yanga passes `--source-links` and `--project-root` to `clanguru docs` for production and test sources.
- **Resolver.** A yanga command, run right after `fix_html_links` in the component and variant report commands, finds every `source:` link in the finished HTML and replaces it with the URL its strategy returns, relative to the page's depth. A link it cannot resolve becomes plain text.
- **Profiles.** `ReportCMakeGenerator`'s `config:` gets `resolvers`, a typed dataclass, the same way `GTestCMakeGenerator` takes its `mocking:` config: a dict of named profiles. `default` is required; `local` and `ci` are optional and replace `default` where they apply. Each value is an ordered list of strategies; for each link the first strategy that finds a target wins, and none means plain text. The structure must make more strategies and profiles easy to add.
- **`switch` and `resolvers` are independent.** With `source_links` on and no `resolvers`, no resolver runs and the links stay unresolved in the report, which shows the missing config.
- **Strategy `gcovr`.** Reads the file rows of every component coverage tree (`coverage/<component>/index.html`) in the report, never the variant tree. It takes the row whose shown name the source path ends with, on a path component boundary, and appends `#l<line>`. More than one matching row gives a warning and plain text.
- **Strategy `vscode`.** Writes `vscode://file/<absolute path>:<line>`. It only works on the machine that built the report, so it fits a `local` profile.
- **CI or local.** The report generator reads the `CIContext` that pypeline-semantic-release's `CheckCIContext` step puts into the data registry: the profile is `ci` when it says `is_ci`, `local` otherwise, also when there is no `CIContext`. A profile that is not configured falls back to `default`. pypeline-semantic-release becomes a regular dependency.
- Out of scope: a code host strategy for `ci`, yanga's kickstart template, folding `fix_html_links`' `#http://` marker into the resolver.

## Acceptance criteria

- [ ] With `source_links` off, the report commands write the same CMake as before
- [ ] With `source_links` on, `clanguru docs` is called with `--source-links` and `--project-root` for production and test sources
- [ ] Under a profile `[gcovr]`, a `source:` link to a covered file becomes a relative link to its coverage page with `#l<line>`
- [ ] A link no strategy resolves becomes plain text
- [ ] Two coverage rows that both match a source path give a warning, and the link becomes plain text
- [ ] Under a profile `[gcovr, vscode]`, a link to a file gcovr does not cover becomes `vscode://file/<absolute path>:<line>`
- [ ] The profile is `ci` with a `CIContext` that says `is_ci`, `local` otherwise, and a missing profile falls back to `default`
- [ ] The source links option and the resolver profiles are documented in yanga's docs
- [ ] `pypeline run` is green
