import os
import sys
from pathlib import Path

import typer
from py_app_dev.core.exceptions import UserNotificationException
from py_app_dev.core.logging import logger, setup_logger, time_it
from yanga_core.commands.features import FeaturesCommand, FeaturesCommandConfig
from yanga_core.commands.info import InfoCommand, InfoCommandConfig
from yanga_core.commands.run import RunCommand, RunCommandConfig

from yanga import __version__

from .kickstart.create import KickstartProject
from .yide import IDEProjectGenerator

package_name = "yanga"

app = typer.Typer(name=package_name, help="YANGA command line interface.", no_args_is_help=True, add_completion=False)


def make_absolute_path(path_value: str | Path) -> Path:
    return Path(os.path.abspath(path_value))


project_dir_option = typer.Option(Path.cwd(), callback=make_absolute_path, help="The project directory")
output_option = typer.Option(None, help="Write the JSON to this file instead of stdout.")


@app.callback(invoke_without_command=True)
def version(
    version: bool = typer.Option(None, "--version", "-v", is_eager=True, help="Show version and exit."),
) -> None:
    if version:
        typer.echo(f"{package_name} {__version__}")
        raise typer.Exit()


@app.command(help="Initialize a new YANGA project in the specified directory.")
@time_it("init")
def init(
    project_dir: Path = project_dir_option,
    force: bool = typer.Option(False, help="Force the initialization of the project even if the directory is not empty."),
    sources: bool = typer.Option(True, help="Copy the example SPL sources."),
) -> None:
    KickstartProject(project_dir, force, sources).run()


@app.command(help="Run the build pipeline for a specific variant and component.")
@time_it("run")
def run(
    project_dir: Path = project_dir_option,
    platform: str | None = typer.Option(
        None,
        help="Platform for which to build (see the available platforms in the configuration).",
    ),
    variant: str | None = typer.Option(
        None,
        help="SPL variant name. If none is provided, it will prompt to select one.",
    ),
    component: str | None = typer.Option(
        None,
        help="Restrict the scope to one specific component.",
    ),
    target: str | None = typer.Option(
        None,
        help="Define a specific target to execute.",
    ),
    build_type: str | None = typer.Option(
        None,
        help="Build type to use (e.g., 'Debug', 'Release').",
    ),
    step: str | None = typer.Option(
        None,
        help="Name of the step to run (as written in the pipeline config).",
    ),
    single: bool = typer.Option(
        False,
        help="If provided, only the provided step will run, without running all previous steps in the pipeline.",
    ),
    print: bool = typer.Option(
        False,
        help="Print the pipeline steps.",
    ),
    force_run: bool = typer.Option(
        False,
        help="Force the execution of a step even if it is not dirty.",
    ),
    not_interactive: bool = typer.Option(
        False,
        help="Run in non-interactive mode (no prompts).",
    ),
    pristine: bool = typer.Option(
        False,
        help="Recursively delete the variant build directory before running. Works even if cmake configure is currently broken (e.g. variant rename, schema change).",
    ),
) -> None:
    RunCommand().do_run(
        RunCommandConfig(
            project_dir,
            platform,
            variant,
            component,
            target,
            build_type,
            step,
            single,
            print,
            force_run,
            not_interactive,
            pristine,
        )
    )


@app.command(help="Emit the parsed project model as JSON for GUI / IDE clients.")
@time_it("info")
def info(
    project_dir: Path = project_dir_option,
    output: Path | None = output_option,
) -> None:
    InfoCommand().do_run(InfoCommandConfig(project_dir, output))


def _check_tkinter_available() -> None:
    """Check if tkinter is available, raise UserNotificationException if not."""
    try:
        import tkinter  # noqa: F401
    except ImportError as e:
        raise UserNotificationException(
            "GUI functionality requires tkinter, which is not available in this environment.\n"
            "This is expected in headless environments like Docker containers or dev containers.\n"
            "Please use CLI commands instead (e.g., 'yanga run', 'yanga features')."
        ) from e


@app.command(help="Launch the YANGA GUI to build variants and components.")
@time_it("gui")
def gui(
    project_dir: Path = project_dir_option,
) -> None:
    _check_tkinter_available()
    from .gui import YangaGui

    YangaGui(project_dir).run()


@app.command(help="View the product features of all variants, or edit the selection of a variant and/or a platform.")
@time_it("features")
def features(
    project_dir: Path = project_dir_option,
    variant: str | None = typer.Option(
        None,
        help="Variant whose selection to edit. Alone it edits the product selection; with --platform, the variant's selection for that platform.",
    ),
    platform: str | None = typer.Option(
        None,
        help="Platform whose feature model to open. Without --variant and --platform, all variants' product selections are shown.",
    ),
    gui: bool = typer.Option(
        True,
        help="Use the GUI editor; pass --no-gui for the terminal editor. The view of all variants is GUI only.",
    ),
) -> None:
    if gui:
        _check_tkinter_available()
    FeaturesCommand().do_run(FeaturesCommandConfig(project_dir, variant_name=variant, platform=platform, gui=gui))


@app.command(help="Generate the VS Code project files.")
@time_it("ide")
def ide(
    project_dir: Path = project_dir_option,
) -> None:
    IDEProjectGenerator(project_dir).run()


def main() -> int:
    try:
        setup_logger()
        app()
        return 0
    except UserNotificationException as e:
        logger.error(f"{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
