# Platform Configuration

Yanga's platform configuration allows you to define target-specific build environments, toolchains, and dependencies. This ensures that your project can be built consistently across different hardware, operating systems, or custom environments.

## Basic Platform

A platform definition requires a `name`. You can also provide a `description` and specify a toolchain file for cross-compilation or environment-specific compiler settings using a `configs` entry with `id: toolchain`.

```yaml
platforms:
  - name: native
    description: Build for the host system.
    configs:
      - id: toolchain
        file: "toolchains/native.cmake"
```

## Extra CMake Files

A `configs` entry with `id: cmake` names a CMake file that is included at the end of the generated `variant.cmake`, after every component library and generated target exists. Use it for build logic that belongs to the platform rather than to yanga's generators, such as sources selected by the target framework's own configuration. The file is looked up like the toolchain file: next to the declaring `yanga.yaml`, then in the project root, then under `platforms/`. Several entries are included in the order yanga collects configs (project, variant, platform, variant-platform).

```yaml
platforms:
  - name: zephyr_esp32h2
    configs:
      - id: cmake
        file: "platforms/zephyr/app.cmake"   # target_sources_ifdef(CONFIG_LED_STRIP app ...)
```

## Build Types

You can restrict the build types (e.g., `Debug`, `Release`) that are valid for a specific platform. This is useful if a platform only supports a subset of build configurations.

```yaml
platforms:
  - name: embedded_target
    configs:
      - id: toolchain
        file: "toolchains/arm-gcc.cmake"
    build_types:
      - Debug
      - Release
```

## CMake Generators

Each platform can have a unique pipeline of `generators`. These are steps that generate different parts of the CMake build system, such as executables, libraries, or test harnesses.

```yaml
platforms:
  - name: windows_test
    description: Build and run tests on Windows
    generators:
      - step: GTestCMakeGenerator
        module: yanga.cmake.gtest
      - step: TestResultsCMakeGenerator
        module: yanga.cmake.test_results
```

See the [CMake Generators](#cmake-generators) documentation for more details on available generators and their configurations.

## Platform-Specific Dependencies

Platforms can define their own dependencies, which are essential for setting up the build environment. Yanga uses `west` to manage Git repository dependencies and `poks` to manage tools and packages on all platforms. On Windows, `scoop` is also supported.

### West Manifest

For platforms that require external Git-based dependencies, you can include a `config` with `id: west`. This allows you to specify repositories, remotes, and revisions, and `yanga` will ensure they are cloned and updated correctly.

```yaml
platforms:
  - name: my_platform_with_deps
    configs:
      - id: west
        content:
          remotes:
            - name: my-remote
              url-base: https://github.com/my-org
          projects:
            - name: my-library
              remote: my-remote
              revision: v2.1.0
              path: vendor/my-library
```

### Scoop Manifest

For Windows-based platforms, you can use a `config` with `id: scoop` to ensure the necessary development tools are available.

```yaml
platforms:
  - name: windows_dev
    configs:
      - id: scoop
        content:
          apps:
            - name: git
            - name: ninja
```
