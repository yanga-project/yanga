# Hello Yanga

A C project built with [Yanga](https://github.com/yanga-project/yanga). It supports multiple product variants and target platforms.

## Prerequisites

- Python 3.11 or newer
- Git
- [pipx](https://pipx.pypa.io) to install Python tools (recommended)

Everything else is installed automatically by the build pipeline: the compiler toolchain, CMake and Ninja are fetched via [poks](https://github.com/cuinixam/poks) (see `poks.json`), and external source dependencies via west.

## Getting started

```bash
pipx install yanga
yanga run
```

`yanga run` lets you pick a variant and platform interactively, then runs the whole pipeline: it creates the project virtual environment (`.venv`), installs the build tools and dependencies, and builds.

Non-interactive examples:

```bash
# Build the German variant as a host executable
yanga run --variant GermanVariant --platform host_exe --build-type Debug

# Run the unit tests and generate the HTML report
yanga run --variant EnglishVariant --platform gtest --target report
```

Build outputs land in `.yanga/build/variants/<variant>/<platform>/`. The test report is generated at `.yanga/build/variants/<variant>/gtest/reports/index.html`.

## Project layout

| Path | Content |
| --- | --- |
| `src/` | Components (sources, tests, docs) and the variants configuration (`src/yanga.yaml`) |
| `platforms/` | Platform definitions and CMake toolchain files |
| `yanga.yaml` | The build pipeline |
| `poks.json` | Pinned build tools (compiler, CMake, Ninja) |
| `KConfig` | The feature model; variants select features via `config_*.txt` files |
| `docs/`, `index.md`, `conf.py` | Sphinx documentation and report configuration |

## Working in VS Code

Open the project folder in VS Code. CMake kits and variants are preconfigured in `.vscode/`. Alternatively use the dev container in `.devcontainer/`, which has all tools preinstalled.
