# How to Add Component Tests

This guide shows how to configure unit testing for your Yanga components using Google Test.

## Prerequisites

- A Yanga project with at least one component
- A test platform configured with `GTestCMakeGenerator` and `TestResultsCMakeGenerator`

## Steps

### 1. Configure a test platform

Add a platform with the `GTestCMakeGenerator`, followed by the `TestResultsCMakeGenerator` that makes the `test` and `coverage` targets:

```yaml
platforms:
  - name: gtest
    description: Build and run component tests
    generators:
      - step: GTestCMakeGenerator
        module: yanga.cmake.gtest
        config:
          mocking:
            enabled: true
            strict: false
            exclude_symbol_patterns:
              - "_*"
      - step: TestResultsCMakeGenerator
        module: yanga.cmake.test_results
```

### 2. Add test sources to your component

`testing` is a list with one block per test framework. The `GTestCMakeGenerator` builds only the block with `framework: gtest` and ignores the others:

```yaml
components:
  - name: my_component
    sources: ["src/my_component.c"]
    testing:
      - framework: gtest
        sources:
          - "test/test_my_component.cpp"
```

### 3. Configure mocking and add mockup sources (optional)

The block's `config` is read only by the generator of its framework. For gtest, `config.mocking` overrides the platform's mocking settings for this component.

`mockup_sources` are test-only helpers, for example a hand-written fake of a function from another component. They are compiled without coverage and linked into the test executable, and automock generates no mock for the functions they define.

```yaml
components:
  - name: my_component
    sources: ["src/my_component.c"]
    testing:
      - framework: gtest
        sources:
          - "test/test_my_component.cpp"
        mockup_sources:
          - "test/fake_clock.c"
        config:
          mocking:
            enabled: true
            strict: true
```

```{note}
Mockup sources must be C fakes. A C++ mockup that uses gmock or the standard library is not supported: automock would try to mock its C++ symbols too. A mockup fills functions the component does not define; it cannot replace the component's own code. A block with `mockup_sources` but no `sources` has no tests, and its mockups are ignored.
```

### 4. Run the tests

Build and run tests for your component:

```bash
yanga run --platform gtest --target my_component_test
```

`my_component_test` runs every test framework of the component. To run only the gtest block, use `my_component_gtest_test`.

Or run all tests:

```bash
yanga run --platform gtest
```

### 5. Test several components together (optional)

To test how components work together, create an integration component that lists them with `integrates` and select it on the test platform:

```yaml
components:
  - name: test_integrations_networking
    integrates: [tcp, udp]
    testing:
      - framework: gtest
        sources:
          - "test/test_networking_integration.cpp"
```

The integration component compiles the sources of `tcp` and `udp` again into its own test executable without selecting them. Automock then mocks only the calls that leave the group, and the coverage stays separate from the components' unit tests. Run it with `yanga run --platform gtest --target test_integrations_networking_test`.

### 6. Test the whole variant (optional)

A variant takes the same `testing` list as a component. Its `gtest` block builds one test executable, linked against the objects of all components the variant selects on the platform. Nothing is compiled a second time.

```yaml
variants:
  - name: EnglishVariant
    components: [greeter, counter]
    platforms:
      host_exe:
        components: [main]
    testing:
      - framework: gtest
        sources:
          - "variants/English/test_english.cc"
        mockup_sources:
          - "variants/English/fake_board.c"
        config:
          mocking:
            strict: true
```

- **Paths:** the sources are found next to the file that declares the variant, then in the project root.
- **Mocking:** automock mocks only what the selected components together leave undefined, such as platform adapters. Calls between the selected components are not mocked. Include `mockup_variant_test.h` in the test to use the mocks; `mockup_sources` and `config` work as for a component.
- **Integration components:** the variant test does not link an integration component, because its objects are second copies of the components it integrates.
- **`main`:** if a selected component defines `main()`, the linker takes it instead of the `main` of GoogleTest, and the executable runs the product, not the tests. Select such a component only on the platforms that build the product, as `main` above.
- **Results:** `yanga run --platform gtest --target test` builds and runs the variant test (the default target runs it too). The variant report shows its JUnit result (with `SphinxTestReportCMakeGenerator`) and its coverage on its own **Coverage** page. Every coverage page has this title; the chapter that includes it gives the level. The variant test also counts in the overall coverage; the merged coverage of all components holds only the component unit tests (see the report entry tags in the CMake reference).
- **Platforms:** only a platform with `GTestCMakeGenerator` builds the variant test; `variant_gtest_test` runs only it. A variant without a `gtest` block builds as before.

### 7. Test with pytest (optional)

To write the tests in Python, list the `PytestCMakeGenerator` on the platform, after the `GTestCMakeGenerator` and before the `TestResultsCMakeGenerator`. A component can have a `gtest` and a `pytest` block. pytest must be installed in the project's Python environment.

```yaml
platforms:
  - name: test
    generators:
      - step: GTestCMakeGenerator
        module: yanga.cmake.gtest
      - step: PytestCMakeGenerator
        module: yanga.cmake.pytest
      - step: TestResultsCMakeGenerator
        module: yanga.cmake.test_results
```

```yaml
components:
  - name: my_component
    sources: ["src/my_component.c"]
    testing:
      - framework: pytest
        sources:
          - "test/test_my_component.py"
```

yanga builds a shared test library from the component and generates the module `my_component_binding`. A call to a function the component does not define goes to a Python mock. `load()` resets every mock, so call it at the start of each test:

```python
from unittest.mock import Mock

import my_component_binding


def test_reads_the_clock() -> None:
    lib = my_component_binding.load()
    lib.mocks.clock_now = Mock(return_value=42)

    assert lib.my_component_run() == 42
    assert lib.mocks.unexpected_calls == []
```

A call to a function with no mock set returns zero and is listed in `lib.mocks.unexpected_calls`. A test checks the list if it wants to. `lib.<variable>.value` reads and writes a C variable.

Run only the pytest tests with `yanga run --platform test --target my_component_pytest_test`, or all frameworks of the component with `yanga run --platform test --target my_component_test`. A failing test does not fail the build; the result is in the JUnit file and the report. Integration components and variants take a `pytest` block in the same way. The variant runs with `variant_pytest_test`. See the [CMake reference](../reference/cmake.md#pytestcmakegenerator) for the generated files.

## See also

- [Software Product Line Reference](../reference/product.md) for component configuration
- [CMake Generators](../reference/cmake.md) for GTestCMakeGenerator and PytestCMakeGenerator options
