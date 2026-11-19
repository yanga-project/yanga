# AGENTS.md - Development Guide for AI Coding Agents

## Project Overview

A C project built with the [Yanga](https://github.com/yanga-project/yanga) build system. It manages multiple product **variants** (compositions of components with a feature selection) built for multiple **platforms** (host executable, GoogleTest).

## Architecture

- **Components** (`src/`) are reusable C modules declared in `src/yanga.yaml` with sources, tests (one `testing` block per framework, e.g. `framework: gtest`) and docs (`docs_sources`).
- **Variants** (`src/yanga.yaml`) combine components and optionally select features via a `feature_selection:` block (KConfig `config_*.txt`).
- **Platforms** (`platforms/`) define build targets, CMake generators and toolchain files.
- **Feature model** (`KConfig`) declares the available features. `KConfigGen` turns the variant's selection into generated headers.

Data flow: variant config (KConfig) -> Yanga -> CMake/Ninja -> executables and test reports.

## Commands

There is no separate bootstrap step. `yanga run` executes the pipeline defined in `yanga.yaml`, including environment setup (`.venv`, build tools via poks, west dependencies):

```bash
# Build a variant for a platform
yanga run --variant GermanVariant --platform host_exe --build-type Debug --not-interactive

# Run unit tests and generate the HTML report
yanga run --variant EnglishVariant --platform gtest --target report --not-interactive
```

Build outputs: `.yanga/build/variants/<variant>/<platform>/`.

## Conventions and Pitfalls

- Never edit generated files (`.yanga/`); Yanga regenerates the CMake build system when configs change.
- New components must be declared in `src/yanga.yaml` and added to the relevant variants' `components` list.
- Build tools are pinned in `poks.json`; do not assume system-wide compilers.
- Feature selections use `CONFIG_<FEATURE>=y` syntax in `config_*.txt` files.
