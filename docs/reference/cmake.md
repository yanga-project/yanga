(cmake-generators)=

# CMake Generators

Yanga uses a modular system of CMake Generators to create the build files for a project. Each generator is a Python class responsible for producing a specific set of CMake commands and targets. They are configured per platform in the `yanga.yaml` file, allowing for different build pipelines for different targets (e.g., one for building an executable, another for running tests).

Below is an overview of the main CMake generators available in Yanga.

## `CreateExecutableCMakeGenerator`

This generator is responsible for creating a single executable for a specific variant. It compiles all components of the variant as object libraries and then links them together into one executable file.

**Use Case:** Building the final application for a product variant.

**Configuration:**

```yaml
platforms:
  - name: my_executable_platform
    generators:
      - step: CreateExecutableCMakeGenerator
        module: yanga.cmake.create_executable
        config:
          # If true, all include directories are added globally.
          # If false, includes are handled on a per-component basis.
          use_global_includes: true
```

**Extending:** when another build system owns the executable (Zephyr, for example), subclass this generator and list the subclass under `generators:`. Three methods are meant to be overridden. `executable_target_name` returns the linked executable, the target the variant `build` target depends on. `create_executable_elements(component_library_targets)` returns the CMake elements that create that target, by default an `add_executable`; an override can instead link the libraries into a target the other build system created. `component_link_libraries` is a tuple of `LinkLibrary` entries linked into every component library that has sources, which is how a subclass hands the libraries the other build system's interface target and its compiler flags; `create_component_elements(component)` returns one component's library and targets for anything beyond that. A container component gets no library and is not linked; `create_container_elements(container)` returns its `compile` and `build` targets, which depend on its subcomponents' targets. Object libraries linked into a static library are archived into it, so no further link edges are needed. A target not created by `add_executable` is not listed as an executable by `yanga info`.

## `CreateSharedLibraryCMakeGenerator`

Links the variant's component libraries into a shared library instead of an executable, for a host that loads the variant at runtime, a Python GUI through `ctypes` for example. The file is named like the executable would be, `Disco.so`, `Disco.dylib` or `Disco.dll` for variant `Disco`, without the `lib` prefix, so a loader finds it by variant name on every OS; on Windows all symbols are exported. Everything else, component libraries, include handling and the `build`/`compile` targets, is inherited from `CreateExecutableCMakeGenerator`, and so is its configuration.

**Use Case:** Driving a variant from another program instead of running it.

**Configuration:**

```yaml
platforms:
  - name: my_shared_library_platform
    generators:
      - step: CreateSharedLibraryCMakeGenerator
        module: yanga.cmake.create_shared_library
        config:
          use_global_includes: false
```

The objects linked into a shared library must be position independent; set `CMAKE_POSITION_INDEPENDENT_CODE ON` in the platform's toolchain file.

## `GTestCMakeGenerator`

This generator facilitates unit testing using the Google Test framework. For each component with a `gtest` testing block, it builds a separate test executable from that block's `sources` and `mockup_sources`; blocks of other frameworks are ignored. It also includes a powerful auto-mocking feature that uses [clanguru](https://github.com/cuinixam/clanguru) to generate mocks for dependencies, isolating the component under test.

**Use Case:** Running unit tests and generating coverage reports for individual components.

It builds the test executable, runs it as `<name>_gtest_test` (`variant_gtest_test` for the variant test), and registers the JUnit file and a gcovr tracefile. The phony `<name>_test`, the coverage reports and the merged levels come from `TestResultsCMakeGenerator` (below), which a platform that tests must list after it.

A container component compiles nothing itself. An integration component is a component whose sources include those of the components it integrates; it builds like any component, and all its results are container level results (see [Report entry tags](#report-entry-tags)).

**Configuration:**

```yaml
platforms:
  - name: test_platform
    generators:
      - step: GTestCMakeGenerator
        module: yanga.cmake.gtest
        config:
          # Enable/disable auto-mocking for all components.
          # This can be overridden in the 'config.mocking' of each component's gtest testing block.
          mocking:
            enabled: true
            strict: false # If true, clanguru parsing errors are fatal.
            exclude_symbol_patterns: ["_*"] # Symbols to exclude from mocking.
```

## `TestResultsCMakeGenerator`

This generator collects what the test generators registered, so one place makes the targets and the coverage for every test framework. The test generators only build, run and register: a JUnit file and a gcovr tracefile per entry.

**Use Case:** Running all the tests of a component with one target and getting one coverage report, whatever frameworks test it.

A platform that tests must list this generator after the test generators (`GTestCMakeGenerator`) and before `SphinxTestReportCMakeGenerator` and `ReportCMakeGenerator`. Add this line to the platform:

```yaml
      - step: TestResultsCMakeGenerator
        module: yanga.cmake.test_results
```

It creates these targets:

* `<name>_test`: runs every framework of the component, in the order of its `testing` list. `<name>_build` runs the same builds. A container runs the tests of its subcomponents.
* `test`: runs every framework of the variant test.
* `<name>_coverage` and `variant_test_coverage`: the coverage report of the component or the variant test, merged over its frameworks.

The coverage reports are gcovr HTML reports in nested mode with the `boost.blue` theme: a sidebar shows the files as a folder tree under their common path, and a switch shows them as a flat list. The entry page of each report is `index.html`.

Besides the coverage of each component and of the variant test, the generator merges the coverage per level. It reads only the gcovr JSON tracefiles, so unit and integration counters never mix in a component page or in the all components page.

* `coverage`: all unit components, in `coverage/index.html` of the variant reports directory.
* `<container>_coverage`: the subcomponents of the container, in the container report. `overall_coverage` copies it to `coverage/<container>` of the variant reports directory.
* `all_containers_coverage`: the subcomponents of every container and every integration component, in `all_containers_coverage/index.html`.
* `overall_coverage`: every component test and the variant test, in `overall_coverage/index.html`.

Each coverage entry is a markdown page named **Coverage**, with one section per coverage tool. The `gcovr` section links the gcovr HTML report. The HTML is not registered as report content itself, so the report lists Coverage once. The chapter that includes the page gives the level. A level without any tracefile gets no target and no report entry. The report entries carry tags, see [Report entry tags](#report-entry-tags).

**Configuration:**

```yaml
platforms:
  - name: gtest
    generators:
      - step: GTestCMakeGenerator
        module: yanga.cmake.gtest
      - step: TestResultsCMakeGenerator
        module: yanga.cmake.test_results
      - step: SphinxTestReportCMakeGenerator
        module: yanga.cmake.sphinx_test_report
      - step: ReportCMakeGenerator
        module: yanga.cmake.reports
```

## `CppCheckCMakeGenerator`

This generator integrates `cppcheck`, a static analysis tool for C/C++ code. It creates targets to run `cppcheck` on a per-component basis and for the entire variant. The results are generated as XML and then converted to Markdown for inclusion in reports. `cppcheck` reports per component only; the merged container and variant static analysis levels come from `ClangTidyCMakeGenerator`.

**Use Case:** Performing static code analysis to find bugs and improve code quality.

**Configuration:**

This generator is typically added as a step without specific configuration. It tags each component report as static analysis, see [Report entry tags](#report-entry-tags).

```yaml
platforms:
  - name: analysis_platform
    generators:
      - step: CppCheckCMakeGenerator
        module: yanga.cmake.cppcheck
```

## `SphinxTestReportCMakeGenerator`

This generator renders the test results for the reports. For every JUnit report that a test generator registers, it writes one `<component>_test_report.rst` page per entry (`<variant>_test_report.rst` for the variant test) and registers it as the test result. The page heading is **Test Results**, the same on every test page; the chapter that includes it gives the level. The page has one section per framework, in the order of the `testing` list. Each section has a [sphinx-test-reports](https://sphinx-test-reports.readthedocs.io) `test-report` directive (JUnit file relative to the project root, results expanded). The project must load the `sphinx_test_reports` extension in its `conf.py`.

sphinx-test-reports derives the need IDs from the directive's `:id:`. The id of gtest is `TR_<NAME>`; the id of another framework is `TR_<NAME>__<FRAMEWORK>`. Non-word characters become `_` and the id is upper case. The gtest ids do not change when another framework joins the page.

It also writes merged pages. For each component of its level, a page has a section with the component's name and a subsection per framework, each with a `test-report` block. The ids hold the page and the test (`TR_<PAGE>__<NAME>` for gtest, `TR_<PAGE>__<NAME>__<FRAMEWORK>` for another framework, where `<PAGE>` is the container name, `ALL_COMPONENTS`, `ALL_CONTAINERS` or `OVERALL`). One JUnit file on several pages then makes distinct needs, and the double underscore keeps a merged id apart from a test page id.

* `<container>_test_report.rst`: the tests of the container's subcomponents, in the container report.
* `all_components_test_report.rst` (target `all_components_test`): the tests of all unit components.
* `all_containers_test_report.rst` (target `all_containers_test`): the tests of the components inside containers and of the integration components.
* `overall_test_report.rst` (target `overall_test`): every test, the variant test included.

A level without any JUnit file gets no page and no target. The report entries carry tags, see [Report entry tags](#report-entry-tags).

**Use Case:** Showing test results in the component and variant reports, and linking them to test specifications with sphinx-needs.

**Configuration:**

This generator is added as a step without configuration, after `TestResultsCMakeGenerator` and before `ReportCMakeGenerator`.

```yaml
platforms:
  - name: gtest
    generators:
      - step: GTestCMakeGenerator
        module: yanga.cmake.gtest
      - step: TestResultsCMakeGenerator
        module: yanga.cmake.test_results
      - step: SphinxTestReportCMakeGenerator
        module: yanga.cmake.sphinx_test_report
      - step: ReportCMakeGenerator
        module: yanga.cmake.reports
```

## `ClangTidyCMakeGenerator`

This generator integrates `clang-tidy`, which ships with the clang toolchain and runs the Clang Static Analyzer checks by default. It creates the same `lint` and `<component>_lint` targets as `CppCheckCMakeGenerator`, so use one or the other. Add it to one platform only, ideally the test platform, so every source file is analysed once.

* The platform may build with gcc. The generator rewrites the variant `compile_commands.json` for clang and keeps only the flags clang needs to parse (`-I`, `-D`, `-U`, `-isystem`, `-include`, `-std=` and similar), so gcc-only flags such as `-fcondition-coverage` do not stop clang-tidy.
* clang-tidy runs once per production source file, so a rebuild analyses only the files that changed. Test sources are not analysed. A change to the `.clang-tidy` file in the project root reruns all files; nested `.clang-tidy` files are not tracked.
* An integration component is analysed only for the sources it declares itself. The files it integrates are analysed under their own component.
* Warnings in headers are reported only for headers below the component include directories, so toolchain headers stay out of the report.
* `lint` writes an HTML report to `clang_tidy/index.html` in the variant reports directory, `<component>_lint` to `clang_tidy/<component>/index.html` in the component reports directory. The variant and component reports link it. `lint` reports the findings of all components that are neither containers nor integration components. `overall_lint` reports every finding to `overall_clang_tidy/index.html` in the variant reports directory and copies each component report to `clang_tidy/<component>` in the variant reports directory. It looks like the coverage report (gcovr's boost theme: its style and script come from the installed gcovr, the page frame is a copy without the Boost logo, the Nested/Flat switch and the gcovr footer): the entry page shows the folders and files with findings as a tree, with the number of findings per severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `STYLE`) on each folder and file. Folders with a single folder inside are one row. Each file has a page that lists its findings with line, check, severity and message. Paths are relative to the project root; a file outside the project root keeps its absolute path. A finding in a header that several source files include is listed once.
* The severity of a check comes from the severity table of [CodeChecker](https://github.com/Ericsson/codechecker) 6.29.3 (Apache-2.0 WITH LLVM-exception), which yanga ships. A check that is not in the table gets `MEDIUM`.
* Next to the HTML, `clang_tidy_report.sarif` holds every finding and parse failure in SARIF 2.1.0, so other tools (for example a code scanning service or a findings database) can read them. Each result has the check as `ruleId`, the file and line, the message, the `level` (`warning` for a finding, `error` for a parse failure) and the severity as the `severity` property. A file inside the project is a relative URI with the `uriBaseId` `PROJECTROOT`, which `originalUriBaseIds` maps to the project root; a file outside it is a `file://` URI.
* Files that clang cannot parse are listed in their own **Parse failures** section on the entry page. Findings and parse failures never fail the build.
* `<container>_lint` reports the findings of the container's subcomponents to `clang_tidy/<container>` in the container reports directory, and `overall_lint` copies it into the variant reports directory. `all_containers_lint` reports the findings of all containers and integration components to `all_containers_clang_tidy` in the variant reports directory. Every static analysis page is named **Static Analysis**; the chapter that includes it gives the level. A container without analysed sources gets no report. The report entries carry tags, see [Report entry tags](#report-entry-tags).

**Use Case:** Static code analysis without installing a separate tool next to clang.

**Configuration:**

This generator has no configuration. To choose the checks, add a `.clang-tidy` file to the project; clang-tidy picks it up from the source tree. Use its `ExtraArgs` to analyse code in its shipped form when the test platform changes it with a macro, for example:

```yaml
ExtraArgs: ['-USPLE_TESTABLE_STATIC', '-DSPLE_TESTABLE_STATIC=static']
```

```yaml
platforms:
  - name: gtest
    generators:
      - step: ClangTidyCMakeGenerator
        module: yanga.cmake.clang_tidy
```

## `ReportCMakeGenerator`

This generator orchestrates the creation of comprehensive HTML reports for both individual components and the entire variant. It uses Sphinx to collect and render various artifacts generated by other steps, such as:

* User-provided documentation (e.g., Markdown files).
* Source code documentation (component sources or generated by the auto-mocker).
* Static analysis reports (from `CppCheckCMakeGenerator` or `ClangTidyCMakeGenerator`).
* Coverage reports (from `TestResultsCMakeGenerator`) and test reports (from `SphinxTestReportCMakeGenerator`).

It tags the docs and sources pages, see [Report entry tags](#report-entry-tags). It registers the variant report (`<variant build dir>/reports/index.html`) as a `PublishedFile` for the SPL overview, so a `WritePublishManifest` at the end of the build links it when the `report` target ran.

**Use Case:** Generating detailed documentation and quality assurance reports.

**Configuration:**

The generator needs no configuration. Add `source_links` to link the source docs to the coverage lines.

```yaml
platforms:
  - name: report_platform
    generators:
      # It is recommended to run this generator after all other generators
      # that produce reports (e.g., GTest, CppCheck).
      - step: ReportCMakeGenerator
        module: yanga.cmake.reports
        config:
          source_links: true
          resolvers:
            default: [gcovr]
            local: [gcovr, vscode]
            ci: [repository, gcovr]
```

* `source_links` (default `false`): calls `clanguru docs` with `--source-links` and `--project-root`, so the source docs contain `source:` links. The clanguru version must support `--source-links`. With `false`, the generated CMake does not change.
* `resolvers`: named profiles with an ordered list of strategies each. `default` is required. `local` and `ci` are optional. For each link the first strategy that finds a target wins.
* Without `resolvers`, no resolver runs and the links stay unresolved.

Strategies:

* `gcovr`: links to the line in the file's page of the component coverage report (`coverage/<component>/`), relative to the page. It finds the file by the path that each file page shows in its breadcrumb. The line anchor follows the page: `#L<line>` or `#l<line>`, whichever id the page has for that line (gcovr's boost and github themes differ); a line without an id links to the page and logs a warning. A file can be listed in several component trees, for example by an integration test component; pages with the same name are the same file, and the tree of the component in the source path wins. If matching pages have different names, it logs a warning and the link becomes plain text.
* `vscode`: links to `vscode://file/<absolute path>:<line>`. It works only on the machine that built the report, so use it in a `local` profile.
* `repository`: links to `<repository URL>/blob/<commit>/<path>#L<line>`. The URL is the HTTPS form of the checkout's `origin` remote and the commit is the checked out one. yanga-core detects both. Use it in the `ci` profile: locally an unpushed commit gives a dead link. Without a URL or a commit, and for a source outside the project root, it resolves nothing, so the next strategy or plain text applies.

The profile is `ci` when the `CIContext` from the `CheckCIContext` step of pypeline-semantic-release says `is_ci`. Otherwise it is `local`, also when there is no `CIContext`. A profile that is not configured falls back to `default`.

The links are resolved after `fix_html_links`. A link that no strategy resolves shows as plain text. The `conf.py` of the project must add `source` to `myst_url_schemes`.

## Report entry tags

Each report entry that a generator registers carries tags. A report template uses them to place each result where it wants it. Build targets and object dependencies have no tags.

A tag says one of three things:

* The level: `component`, `container`, `variant`, `overall`, or `merged` for a page that merges a level.
* The kind: `docs`, `sources`, `test`, `coverage` or `static-analysis`; yanga-core's `KConfigGen` tags the feature configuration `[variant, configuration]`.
* The component name, on the entries of one component or container.

The levels:

* A unit component is neither a container nor an integration component. Its results are `component` results.
* An integration component (one with `integrates`) tests a group of components, like a container. All its results (docs, sources, test, coverage and static analysis) are `container` results.
* A container has `container` results, merged over its subcomponents, down to the components that are not containers.

The tags of each generator:

* `ReportCMakeGenerator`: docs page `[<level>, <name>, docs]`, sources page `[<level>, <name>, sources]`.
* `SphinxTestReportCMakeGenerator`: test page `[<level>, <name>, test]`, variant test page `[variant, test]`, container page `[container, <name>, test]`, all components `[component, merged, test]`, all containers `[container, merged, test]`, overall `[overall, test]`. Each also carries the frameworks of its page, for example `gtest`.
* `TestResultsCMakeGenerator`: component coverage `[<level>, <name>, coverage]`, variant test `[variant, coverage]`, container `[container, <name>, coverage]`, all components `[component, merged, coverage]`, all containers `[container, merged, coverage]`, overall `[overall, coverage]`. Each also carries `gcovr` and the frameworks whose tracefiles it merges, for example `gtest`.
* `ClangTidyCMakeGenerator`: component `[<level>, <name>, static-analysis]`, container `[container, <name>, static-analysis]`, all containers `[container, merged, static-analysis]`, all components (`lint`) `[component, merged, static-analysis]`, overall (`overall_lint`) `[overall, static-analysis]`.
* `CppCheckCMakeGenerator`: component `[<level>, <name>, static-analysis]`. A component without sources, a container for example, gets no report.

The level of a component's own entries is `container` for a container or an integration component, else `component`. A level with nothing in it registers no entry, so there is no empty page.

In `index.md`, `report_data.files(...)` gives the toctree lines of the entries that carry all the given tags. For example, a coverage chapter with the merged pages:

````md
```{toctree}
:caption: Coverage
:maxdepth: 1

{% for file in report_data.files("merged", "coverage") %}
{{ file }}
{% endfor %}
{% for file in report_data.files("overall", "coverage") %}
{{ file }}
{% endfor %}
```
````

The project that `yanga init` creates lays out its variant report this way: a Components chapter and a Containers chapter with the entries of each component and container, the feature configuration, a Reports chapter with All components, All containers, Variant and Overall, and the untagged entries last (`index.md`, `docs/components.md`, `docs/containers.md`, `docs/reports.md`).

## Auto-emitted targets

Some targets are emitted by Yanga unconditionally — they do not need to be configured per platform in `yanga.yaml`.

### `<component>_clean`

For every component in the variant, Yanga emits a custom target that removes the component's outputs without touching the rest of the variant:

```bash
cmake --build <variant_build_dir> --target <component>_clean
```

The target carries no `DEPENDS`, so invoking it never triggers a build. It removes:

1. **The per-component output namespace** — `${CMAKE_BUILD_DIR}/<component>/`. This is where generators (gtest, cppcheck, reports, ...) write artifacts produced by tools cmake/ninja does not track (gcovr, sphinx-build, `cmake -E copy_directory`, ...).
2. **CMake-derived outputs of tagged targets** — for every `add_library` / `add_executable` whose generator passed `component_name=<component>`, the target removes the intermediate dir `${CMAKE_BUILD_DIR}/CMakeFiles/<target>.dir/` (object files, depfiles, link inputs) and, for executables, the runtime artifact `$<TARGET_FILE:<target>>`.

If you write a custom CMake generator that emits per-component `add_library` or `add_executable`, pass `component_name=component.name` so its outputs are picked up. Anything written outside both the per-component dir and a tagged cmake target's own outputs is invisible to this target.

Variant-level `add_library` / `add_executable` outputs (e.g. the variant executable `${PROJECT_NAME}`) are owned by the buildsystem's own `clean` target, not by `<component>_clean`.

For a full wipe of the variant build directory (e.g. configure is broken after a variant rename or schema change) use `yanga run --pristine`, which removes the build dir from outside cmake before re-invoking the pipeline.
