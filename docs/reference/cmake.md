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

**Extending:** when another build system owns the executable (Zephyr, for example), subclass this generator and list the subclass under `generators:`. Three methods are meant to be overridden. `executable_target_name` returns the target the component libraries are linked into and the variant `build` target depends on. `create_executable_elements(component_library_targets)` returns the CMake elements that create that target, by default an `add_executable`; an override can instead link the libraries into a target the other build system created. `component_link_libraries` is a tuple of `LinkLibrary` entries linked into every component library that has sources, which is how a subclass hands the libraries the other build system's interface target and its compiler flags; `create_component_elements(component)` returns one component's library and targets for anything beyond that. A container component gets no library and is not linked; `create_container_elements(container)` returns its `compile` and `build` targets, which depend on its subcomponents' targets. Object libraries linked into a static library are archived into it, so no further link edges are needed. A target not created by `add_executable` is not listed as an executable by `yanga info`.

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

This generator facilitates unit testing using the Google Test framework. For each testable component, it builds a separate test executable. It also includes a powerful auto-mocking feature that uses [clanguru](https://github.com/cuinixam/clanguru) to generate mocks for dependencies, isolating the component under test.

**Use Case:** Running unit tests and generating coverage reports for individual components.

A container component compiles nothing itself; its `test` and `build` targets run the tests of its subcomponents. An integration component needs no special handling: it is a component whose sources include those of the components it integrates.

**Configuration:**

```yaml
platforms:
  - name: test_platform
    generators:
      - step: GTestCMakeGenerator
        module: yanga.cmake.gtest
        config:
          # Enable/disable auto-mocking for all components.
          # This can be overridden in each component's 'testing' section.
          mocking:
            enabled: true
            strict: false # If true, clanguru parsing errors are fatal.
            exclude_symbol_patterns: ["_*"] # Symbols to exclude from mocking.
```

## `CppCheckCMakeGenerator`

This generator integrates `cppcheck`, a static analysis tool for C/C++ code. It creates targets to run `cppcheck` on a per-component basis and for the entire variant. The results are generated as XML and then converted to Markdown for inclusion in reports.

**Use Case:** Performing static code analysis to find bugs and improve code quality.

**Configuration:**

This generator is typically added as a step without specific configuration.

```yaml
platforms:
  - name: analysis_platform
    generators:
      - step: CppCheckCMakeGenerator
        module: yanga.cmake.cppcheck
```

## `SphinxTestReportCMakeGenerator`

This generator renders the GoogleTest results for the reports. For every component JUnit report that `GTestCMakeGenerator` registers, it writes a `<component>_test_report.rst` page with a [sphinx-test-reports](https://sphinx-test-reports.readthedocs.io) `test-report` directive and registers it as the component test result. The page then shows as **Test Report** in the component chapter, next to the coverage report. The project must load the `sphinx_test_reports` extension in its `conf.py`.

**Use Case:** Showing test results in the component and variant reports, and linking them to test specifications with sphinx-needs.

**Configuration:**

This generator is added as a step without configuration, after `GTestCMakeGenerator` and before `ReportCMakeGenerator`.

```yaml
platforms:
  - name: gtest
    generators:
      - step: GTestCMakeGenerator
        module: yanga.cmake.gtest
      - step: SphinxTestReportCMakeGenerator
        module: yanga.cmake.sphinx_test_report
      - step: ReportCMakeGenerator
        module: yanga.cmake.reports
```

## `ReportCMakeGenerator`

This generator orchestrates the creation of comprehensive HTML reports for both individual components and the entire variant. It uses Sphinx to collect and render various artifacts generated by other steps, such as:

* User-provided documentation (e.g., Markdown files).
* Source code documentation (component sources or generated by the auto-mocker).
* Static analysis reports (from `CppCheckCMakeGenerator`).
* Coverage reports (from `GTestCMakeGenerator`) and test reports (from `SphinxTestReportCMakeGenerator`).

**Use Case:** Generating detailed documentation and quality assurance reports.

**Configuration:**

This generator is typically added as a step without specific configuration.

```yaml
platforms:
  - name: report_platform
    generators:
      # It is recommended to run this generator after all other generators
      # that produce reports (e.g., GTest, CppCheck).
      - step: ReportCMakeGenerator
        module: yanga.cmake.reports
```

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
