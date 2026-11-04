import queue
import threading
import time
import tkinter
from collections.abc import Callable
from enum import auto
from pathlib import Path

import customtkinter
from py_app_dev.core.exceptions import UserNotificationException
from py_app_dev.core.logging import logger
from py_app_dev.core.subprocess import SubprocessExecutor
from py_app_dev.mvp.event_manager import EventID, EventManager
from py_app_dev.mvp.presenter import Presenter
from py_app_dev.mvp.view import View
from yanga_core.commands.info_schema import InfoProject, build_info_project
from yanga_core.commands.run import RunCommand, RunCommandConfig
from yanga_core.domain.execution_context import UserRequestTarget
from yanga_core.domain.project_slurper import YangaProjectSlurper
from yanga_core.ini import YangaIni

from .icons import Icons

OPTION_MENU_WIDTH = 200


class _Tooltip:
    """Minimal hover tooltip — shows full text when CTkOptionMenu truncates a long selection."""

    def __init__(self, widget: customtkinter.CTkBaseClass) -> None:
        self.widget = widget
        self.text = ""
        self._tip: customtkinter.CTkToplevel | None = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def set_text(self, text: str) -> None:
        self.text = text
        if self._tip is not None:
            self._hide()
            self._show()

    def _show(self, _event: object = None) -> None:
        if self._tip is not None or not self.text:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        tip = customtkinter.CTkToplevel(self.widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")
        label = customtkinter.CTkLabel(tip, text=self.text, fg_color="gray20", text_color="white", corner_radius=4)
        label.pack(padx=6, pady=2)
        self._tip = tip

    def _hide(self, _event: object = None) -> None:
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None


class _LabeledOptionMenu:
    """
    Label + CTkOptionMenu pair with consistent fixed sizing and an optional hover tooltip.

    Menus are placed two-per-row (label above, dropdown below). `grid(row)` returns the
    next free row so callers can chain placements without tracking indices manually.
    """

    def __init__(
        self,
        parent: customtkinter.CTkBaseClass,
        label_text: str,
        command: Callable[[str], None] | None = None,
        with_tooltip: bool = False,
    ) -> None:
        self._label = customtkinter.CTkLabel(parent, text=label_text, anchor="w")
        self._menu = customtkinter.CTkOptionMenu(
            parent,
            command=self._on_select,
            width=OPTION_MENU_WIDTH,
            dynamic_resizing=False,
        )
        self._user_command = command
        self._tooltip: _Tooltip | None = _Tooltip(self._menu) if with_tooltip else None

    def grid(self, row: int) -> int:
        self._label.grid(row=row, column=0, sticky="nsew", padx=10, pady=5)
        self._menu.grid(row=row + 1, column=0, sticky="nsew", padx=10, pady=5)
        return row + 2

    def _on_select(self, value: str) -> None:
        if self._tooltip is not None:
            self._tooltip.set_text(value)
        if self._user_command is not None:
            self._user_command(value)

    def set_values(self, values: list[str]) -> None:
        self._menu.configure(values=values, state="normal")

    def set_current(self, value: str) -> None:
        self._menu.set(value)
        if self._tooltip is not None:
            self._tooltip.set_text(value)

    def disable(self) -> None:
        self._menu.configure(values=[], state="disabled")
        self._menu.set("")
        if self._tooltip is not None:
            self._tooltip.set_text("")

    def get(self) -> str:
        return self._menu.get()


class YangaEvent(EventID):
    BUILD_EVENT = auto()
    COMPONENT_BUILD_EVENT = auto()
    COMPONENT_CLEAN_EVENT = auto()
    REFRESH_EVENT = auto()
    VARIANT_SELECTED_EVENT = auto()
    CLEAN_VARIANT_EVENT = auto()
    PLATFORM_SELECTED_EVENT = auto()
    BUILD_TYPE_SELECTED_EVENT = auto()
    VARIANT_BUILD_TARGET_SELECTED_EVENT = auto()
    COMPONENT_BUILD_TARGET_SELECTED_EVENT = auto()
    OPEN_IN_VSCODE = auto()


class YangaView(View):
    def __init__(self, event_manager: EventManager) -> None:
        self.event_manager = event_manager
        self.root = customtkinter.CTk()

    @property
    def selected_variant(self) -> str:
        return self.variant_menu.get()

    @property
    def selected_component(self) -> str:
        return self.component_menu.get()

    @property
    def selected_build_type(self) -> str | None:
        return self.build_type_menu.get()

    @property
    def selected_variant_build_target(self) -> str | None:
        return self.variant_build_target_menu.get()

    @property
    def selected_component_build_target(self) -> str | None:
        return self.component_build_target_menu.get()

    @property
    def selected_pristine(self) -> bool:
        return bool(self.pristine_var.get())

    def init_gui(self) -> None:
        customtkinter.set_default_color_theme("green")
        self.root.title("YANGA")
        self.root.geometry(f"{240}x{750}")
        # Hold a reference to the PhotoImage; otherwise it can be garbage-collected
        # before Tk gets to draw it, leaving the default Tk/Python icon.
        self._app_icon = Icons.YANGA_PNG.tk_photo
        self.root.iconphoto(True, self._app_icon)

        # Event triggers must exist before menu commands reference them.
        self.build_trigger = self.event_manager.create_event_trigger(YangaEvent.BUILD_EVENT)
        self.clean_variant_trigger = self.event_manager.create_event_trigger(YangaEvent.CLEAN_VARIANT_EVENT)
        self.component_build_trigger = self.event_manager.create_event_trigger(YangaEvent.COMPONENT_BUILD_EVENT)
        self.component_clean_trigger = self.event_manager.create_event_trigger(YangaEvent.COMPONENT_CLEAN_EVENT)
        self.refresh_trigger = self.event_manager.create_event_trigger(YangaEvent.REFRESH_EVENT)
        self.variant_selected_trigger = self.event_manager.create_event_trigger(YangaEvent.VARIANT_SELECTED_EVENT)
        self.platform_selected_trigger = self.event_manager.create_event_trigger(YangaEvent.PLATFORM_SELECTED_EVENT)
        self.build_type_selected_trigger = self.event_manager.create_event_trigger(YangaEvent.BUILD_TYPE_SELECTED_EVENT)
        self.variant_build_target_selected_trigger = self.event_manager.create_event_trigger(YangaEvent.VARIANT_BUILD_TARGET_SELECTED_EVENT)
        self.component_build_target_selected_trigger = self.event_manager.create_event_trigger(YangaEvent.COMPONENT_BUILD_TARGET_SELECTED_EVENT)
        self.open_in_vscode_trigger = self.event_manager.create_event_trigger(YangaEvent.OPEN_IN_VSCODE)

        self._create_platforms_frame(self.root, 0)
        self._create_variants_frame(self.root, 1)
        self._create_components_frame(self.root, 2)

        self.root.bind("<F5>", self._refresh_button_pressed)

    def _refresh_button_pressed(self, event=None) -> None:  # type: ignore
        self.refresh_trigger()

    def _build_button_pressed(self) -> None:
        self.build_trigger(self.selected_variant, self.selected_build_type, self.selected_variant_build_target, self.selected_pristine)

    def _component_build_button_pressed(self) -> None:
        self.component_build_trigger(self.selected_variant, self.selected_component, self.selected_build_type, self.selected_component_build_target, self.selected_pristine)

    def _component_clean_button_pressed(self) -> None:
        self.component_clean_trigger(self.selected_variant, self.selected_component, self.selected_build_type)

    def _clean_variant_button_pressed(self) -> None:
        self.clean_variant_trigger(self.selected_variant)

    def _open_in_vscode_button_pressed(self) -> None:
        self.open_in_vscode_trigger()

    def mainloop(self) -> None:
        self.root.mainloop()

    @staticmethod
    def _make_frame(root: customtkinter.CTk, position: int) -> customtkinter.CTkFrame:
        frame = customtkinter.CTkFrame(root)
        frame.grid(row=position, column=0, sticky="nsew", padx=10, pady=10)
        return frame

    @staticmethod
    def _grid_button(button: customtkinter.CTkButton, row: int) -> int:
        button.grid(row=row, column=0, sticky="nsew", padx=10, pady=5)
        return row + 1

    def _create_platforms_frame(self, root: customtkinter.CTk, position: int) -> customtkinter.CTkFrame:
        frame = self._make_frame(root, position)
        self.platform_menu = _LabeledOptionMenu(frame, "Platforms", command=self.platform_selected_trigger, with_tooltip=True)
        self.build_type_menu = _LabeledOptionMenu(frame, "Build Type", command=self.build_type_selected_trigger, with_tooltip=True)
        row = self.platform_menu.grid(row=0)
        self.build_type_menu.grid(row=row)
        return frame

    def _create_variants_frame(self, root: customtkinter.CTk, position: int) -> customtkinter.CTkFrame:
        frame = self._make_frame(root, position)
        self.variant_menu = _LabeledOptionMenu(frame, "Variants", command=self.variant_selected_trigger, with_tooltip=True)
        self.variant_build_target_menu = _LabeledOptionMenu(frame, "Build Target", command=self.variant_build_target_selected_trigger, with_tooltip=True)
        row = self.variant_menu.grid(row=0)
        row = self.variant_build_target_menu.grid(row=row)
        self.build_button = customtkinter.CTkButton(frame, text="Build", command=self._build_button_pressed)
        row = self._grid_button(self.build_button, row)
        self.clean_button = customtkinter.CTkButton(frame, text="Clean", command=self._clean_variant_button_pressed)
        row = self._grid_button(self.clean_button, row)
        self.pristine_var = tkinter.BooleanVar(value=False)
        self.pristine_checkbox = customtkinter.CTkCheckBox(frame, text="Pristine (wipe before Build)", variable=self.pristine_var)
        self.pristine_checkbox.grid(row=row, column=0, sticky="nsew", padx=10, pady=5)
        row += 1
        self.open_in_vscode_button = customtkinter.CTkButton(frame, text="Open in VSCode", command=self._open_in_vscode_button_pressed)
        self._grid_button(self.open_in_vscode_button, row)
        return frame

    def _create_components_frame(self, root: customtkinter.CTk, position: int) -> customtkinter.CTkFrame:
        frame = self._make_frame(root, position)
        self.component_menu = _LabeledOptionMenu(frame, "Components", with_tooltip=True)
        self.component_build_target_menu = _LabeledOptionMenu(frame, "Build Target", command=self.component_build_target_selected_trigger, with_tooltip=True)
        row = self.component_menu.grid(row=0)
        row = self.component_build_target_menu.grid(row=row)
        self.component_build_button = customtkinter.CTkButton(frame, text="Build", command=self._component_build_button_pressed)
        row = self._grid_button(self.component_build_button, row)
        self.component_clean_button = customtkinter.CTkButton(frame, text="Clean", command=self._component_clean_button_pressed)
        self._grid_button(self.component_clean_button, row)
        return frame

    # --- Presenter-facing API: each method delegates to the matching menu helper. ---

    def update_platforms(self, platforms: list[str]) -> None:
        self.platform_menu.set_values(platforms)

    def update_current_platform(self, platform: str) -> None:
        self.platform_menu.set_current(platform)

    def update_build_types(self, build_types: list[str]) -> None:
        self.build_type_menu.set_values(build_types)

    def update_current_build_type(self, build_type: str) -> None:
        self.build_type_menu.set_current(build_type)

    def disabled_build_types(self) -> None:
        self.build_type_menu.disable()

    def update_variants(self, variants: list[str]) -> None:
        self.variant_menu.set_values(variants)

    def update_current_variant(self, variant: str) -> None:
        self.variant_menu.set_current(variant)

    def update_variant_build_targets(self, build_targets: list[str]) -> None:
        self.variant_build_target_menu.set_values(build_targets)

    def update_current_variant_build_target(self, build_target: str) -> None:
        self.variant_build_target_menu.set_current(build_target)

    def disabled_variant_build_targets(self) -> None:
        self.variant_build_target_menu.disable()

    def update_components(self, components: list[str]) -> None:
        self.component_menu.set_values(components)

    def update_current_component(self, component: str) -> None:
        self.component_menu.set_current(component)

    def update_component_build_targets(self, build_targets: list[str]) -> None:
        self.component_build_target_menu.set_values(build_targets)

    def update_current_component_build_target(self, build_target: str) -> None:
        self.component_build_target_menu.set_current(build_target)

    def disabled_component_build_targets(self) -> None:
        self.component_build_target_menu.disable()

    def enable_variant_commands(self) -> None:
        self.build_button.configure(state="normal")
        self.clean_button.configure(state="normal")

    def disable_variant_commands(self) -> None:
        self.build_button.configure(state="disabled")
        self.clean_button.configure(state="disabled")

    def enable_component_commands(self) -> None:
        self.component_build_button.configure(state="normal")
        self.component_clean_button.configure(state="normal")

    def disable_component_commands(self) -> None:
        self.component_build_button.configure(state="disabled")
        self.component_clean_button.configure(state="disabled")


class YangaPresenter(Presenter):
    def __init__(self, view: YangaView, event_manager: EventManager, project_dir: Path) -> None:
        self.logger = logger.bind()
        self.view = view
        self.event_manager = event_manager
        self.project_dir = project_dir
        self.project_slurper: YangaProjectSlurper | None = None
        self.info: InfoProject | None = None
        self._load_project_state()
        self.event_manager.subscribe(YangaEvent.BUILD_EVENT, self._build_trigger)
        self.event_manager.subscribe(YangaEvent.COMPONENT_BUILD_EVENT, self._component_build_trigger)
        self.event_manager.subscribe(YangaEvent.COMPONENT_CLEAN_EVENT, self._component_clean_trigger)
        self.event_manager.subscribe(YangaEvent.REFRESH_EVENT, self._refresh_trigger)
        self.event_manager.subscribe(YangaEvent.VARIANT_SELECTED_EVENT, self._variant_selected_trigger)
        self.event_manager.subscribe(YangaEvent.PLATFORM_SELECTED_EVENT, self._platform_selected_trigger)
        self.event_manager.subscribe(YangaEvent.BUILD_TYPE_SELECTED_EVENT, self._build_type_selected_trigger)
        self.event_manager.subscribe(YangaEvent.VARIANT_BUILD_TARGET_SELECTED_EVENT, self._variant_build_target_selected_trigger)
        self.event_manager.subscribe(YangaEvent.COMPONENT_BUILD_TARGET_SELECTED_EVENT, self._component_build_target_selected_trigger)
        self.event_manager.subscribe(YangaEvent.CLEAN_VARIANT_EVENT, self._clean_variant_trigger)
        self.event_manager.subscribe(YangaEvent.OPEN_IN_VSCODE, self._open_in_vscode_trigger)
        self.command_running_flag = False
        self.running_command_config: RunCommandConfig | None = None
        self.selected_platform: str | None = None
        self.selected_variant: str | None = None
        self.selected_component: str | None = None
        self.selected_variant_build_target: str | None = None
        self.selected_component_build_target: str | None = None
        # Worker → UI handshake. Worker pushes a sentinel on completion; the UI thread polls and reacts.
        # Avoids touching Tk from the worker thread (customtkinter on macOS is unreliable about that).
        self._command_done_queue: queue.Queue[bool] = queue.Queue()

    def run(self) -> None:
        self.view.init_gui()
        self._update_view_data()
        self.view.root.after(100, self._poll_command_done)
        self.view.mainloop()

    def _poll_command_done(self) -> None:
        try:
            while True:
                self._command_done_queue.get_nowait()
                self._on_command_finished()
        except queue.Empty:
            pass
        self.view.root.after(100, self._poll_command_done)

    def _build_trigger(self, variant_name: str, build_type: str | None = None, build_target: str | None = None, pristine: bool = False) -> None:
        target = build_target if build_target else str(UserRequestTarget.BUILD)
        self.run_command(self._make_config(target=target, variant_name=variant_name, build_type=build_type, pristine=pristine))

    def _component_build_trigger(self, variant_name: str, component_name: str, build_type: str | None = None, build_target: str | None = None, pristine: bool = False) -> None:
        target = build_target if build_target else str(UserRequestTarget.BUILD)
        self.run_command(self._make_config(target=target, variant_name=variant_name, component_name=component_name, build_type=build_type, pristine=pristine))

    def _component_clean_trigger(self, variant_name: str, component_name: str, build_type: str | None = None) -> None:
        self.run_command(self._make_config(target=str(UserRequestTarget.CLEAN), variant_name=variant_name, component_name=component_name, build_type=build_type))

    def _refresh_trigger(self) -> None:
        self._load_project_state()
        self._update_view_data()

    def _variant_selected_trigger(self, variant_name: str) -> None:
        self.logger.info(f"Variant selected: {variant_name}")
        self.selected_variant = variant_name
        self._update_components()

    def _platform_selected_trigger(self, platform_name: str) -> None:
        self.logger.info(f"Platform selected: {platform_name}")
        self.selected_platform = platform_name
        self._update_build_types()
        self._update_variant_build_targets()
        self._update_component_build_targets()
        self._update_components()

    def _variant_build_target_selected_trigger(self, build_target_name: str) -> None:
        self.logger.info(f"Variant build target selected: {build_target_name}")
        self.selected_variant_build_target = build_target_name

    def _component_build_target_selected_trigger(self, build_target_name: str) -> None:
        self.logger.info(f"Component build target selected: {build_target_name}")
        self.selected_component_build_target = build_target_name

    def _build_type_selected_trigger(self, build_type_name: str) -> None:
        self.logger.info(f"Build type selected: {build_type_name}")

    def _clean_variant_trigger(self, variant_name: str) -> None:
        self.run_command(self._make_config(target=str(UserRequestTarget.CLEAN), variant_name=variant_name))

    def _open_in_vscode_trigger(self) -> None:
        if not self.project_slurper:
            self.logger.warning("Project is not loaded")
            return
        self.logger.info("Opening project in VSCode")
        try:
            SubprocessExecutor(["code", self.project_dir.as_posix()], shell=True).execute()  # noqa: S604
        except UserNotificationException as e:
            self.logger.error(e)

    def _update_view_data(self) -> None:
        self._update_platforms()
        self._update_build_types()
        self._update_variant_build_targets()
        self._update_component_build_targets()
        self._update_variants()
        self._update_components()

    def _update_platforms(self) -> None:
        platforms: list[str] = []
        if self.info:
            platforms = [p.name for p in self.info.platforms]
        if platforms:
            platforms.sort()
            self.selected_platform = platforms[0]
        else:
            platforms = ["No platforms found"]
            self.selected_platform = None
        self.view.update_platforms(platforms)
        self.view.update_current_platform(platforms[0])

    def _update_build_types(self) -> None:
        build_types: list[str] = []
        platform = self.info.find_platform(self.selected_platform) if self.info else None
        if platform:
            build_types = list(platform.build_types)
        if build_types:
            build_types.sort()
            self.view.update_build_types(build_types)
            self.view.update_current_build_type(build_types[0])
        else:
            self.view.disabled_build_types()

    def _update_variant_build_targets(self) -> None:
        build_targets: list[str] = []
        platform = self.info.find_platform(self.selected_platform) if self.info else None
        if platform:
            build_targets = list(platform.build_targets.variant_targets)
        if build_targets:
            build_targets.sort()
            self.view.update_variant_build_targets(build_targets)
            self.view.update_current_variant_build_target(build_targets[0])
            self.selected_variant_build_target = build_targets[0]
        else:
            self.view.disabled_variant_build_targets()
            self.selected_variant_build_target = None

    def _update_component_build_targets(self) -> None:
        build_targets: list[str] = []
        platform = self.info.find_platform(self.selected_platform) if self.info else None
        if platform:
            build_targets = list(platform.build_targets.component_targets)
        if build_targets:
            build_targets.sort()
            self.view.update_component_build_targets(build_targets)
            self.view.update_current_component_build_target(build_targets[0])
            self.selected_component_build_target = build_targets[0]
        else:
            self.view.disabled_component_build_targets()
            self.selected_component_build_target = None

    def _update_variants(self) -> None:
        variants: list[str] = []
        if self.info:
            variants = [v.name for v in self.info.variants]
        if variants:
            variants.sort()
            self.selected_variant = variants[0]
        else:
            variants = ["No variants found"]
            self.selected_variant = None
        self.view.update_variants(variants)
        self.view.update_current_variant(variants[0])
        if self.selected_variant:
            self.view.enable_variant_commands()
        else:
            self.view.disable_variant_commands()

    def _update_components(self) -> None:
        components: list[str] = []
        if self.info and self.selected_variant:
            components = self.info.get_effective_variant_components(self.selected_variant, self.selected_platform)
        if components:
            components.sort()
            self.selected_component = components[0]
        else:
            components = ["No components found"]
            self.selected_component = None
        self.view.update_components(components)
        self.view.update_current_component(components[0])
        if self.selected_component:
            self.view.enable_component_commands()
        else:
            self.view.disable_component_commands()

    def run_command(self, config: RunCommandConfig) -> None:
        # Immediate, UI-thread feedback so the user sees their click landed before the slow project-reload starts.
        scope_extras = f", component={config.component_name}" if config.component_name else ""
        pristine_extra = ", pristine" if config.pristine else ""
        self.logger.log("START", f"Received command: target={config.target} variant={config.variant_name}{scope_extras}{pristine_extra}")
        if self.command_running_flag:
            self.logger.warning(f"Command '{self.running_command_config}' still running. Skip starting new command.")
            return
        if not self.selected_variant:
            self.logger.warning("No variant selected.")
            return
        self.command_running_flag = True
        self.running_command_config = config
        self.view.disable_variant_commands()
        self.view.disable_component_commands()

        def worker() -> None:
            start = time.time()
            try:
                RunCommand().do_run(config)
            except UserNotificationException as e:
                self.logger.error(e)
            except Exception as e:
                self.logger.exception(e)
            finally:
                self.logger.log("STOP", f"Finished executing command in {time.time() - start:.2f}s")
                self._command_done_queue.put(True)

        threading.Thread(target=worker, name=f"yanga-command-{config.target}", daemon=True).start()

    def _make_config(self, *, target: str, variant_name: str | None, component_name: str | None = None, build_type: str | None = None, pristine: bool = False) -> RunCommandConfig:
        return RunCommandConfig(
            project_dir=self.project_dir,
            platform=self.selected_platform,
            variant_name=variant_name,
            component_name=component_name,
            target=target,
            build_type=build_type,
            not_interactive=True,
            pristine=pristine,
        )

    def _on_command_finished(self) -> None:
        """Called on the UI thread after the worker pushes its completion sentinel."""
        self.command_running_flag = False
        self.running_user_request = None
        if self.selected_variant:
            self.view.enable_variant_commands()
        if self.selected_component:
            self.view.enable_component_commands()

    def _load_project_state(self) -> None:
        """Reload slurper and InfoProject for the dropdowns. Used by __init__ and the F5 refresh path; UI-thread only."""
        self.project_slurper = None
        self.info = None
        try:
            ini = YangaIni.from_toml_or_ini(self.project_dir / "yanga.ini", self.project_dir / "pyproject.toml")
            slurper = RunCommand.create_project_slurper(self.project_dir)
            slurper.print_project_info()
            self.project_slurper = slurper
            self.info = build_info_project(self.project_dir, slurper, ini)
        except UserNotificationException as e:
            self.logger.error(e)


class YangaGui:
    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.logger = logger.bind()

    def run(self) -> None:
        try:
            event_manager = EventManager()
            view = YangaView(event_manager)
            presenter = YangaPresenter(view, event_manager, self.project_dir)
            presenter.run()
        except UserNotificationException as e:
            self.logger.error(e)
