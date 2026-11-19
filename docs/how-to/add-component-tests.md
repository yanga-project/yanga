# How to Add Component Tests

This guide shows how to configure unit testing for your Yanga components using Google Test.

## Prerequisites

- A Yanga project with at least one component
- A test platform configured with `GTestCMakeGenerator`

## Steps

### 1. Configure a test platform

Add a platform with the `GTestCMakeGenerator`:

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

## See also

- [Software Product Line Reference](../reference/product.md) for component configuration
- [CMake Generators](../reference/cmake.md) for GTestCMakeGenerator options
