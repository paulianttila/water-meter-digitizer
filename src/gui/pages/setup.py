import base64
import logging
import time
from hashlib import sha256

from nicegui import events, ui

import utils.image as ImageUtils
from callbacks import Callbacks
from configuration import Config
from gui.components import open_config_history_dialog, open_confirm_dialog
from gui.pages.base import BasePage
from gui.wizard.config_manager import WizardConfigManager, resolve_model_path
from gui.wizard.navigator import (
    NAME_ADJUST,
    NAME_DOWNLOAD_IMAGE,
    NAME_DRAW_ANALOG_ROIS,
    NAME_DRAW_DIGITAL_ROIS,
    NAME_DRAW_REFS,
    NAME_FINAL,
    NAME_INITIAL_ROTATE,
    NAME_METERS,
    NAME_SERVICES,
    WizardNavigator,
    steps_order,
)
from gui.wizard.steps import (
    AdjustStep,
    DownloadImageStep,
    DrawAnalogRoisStep,
    DrawDigitalRoisStep,
    DrawRefsStep,
    FinalStep,
    InitialRotateStep,
    MeterStep,
    ServicesStep,
)

logger = logging.getLogger(__name__)

# Re-export constants for backward compatibility
__all__ = [
    "NAME_ADJUST",
    "NAME_DOWNLOAD_IMAGE",
    "NAME_DRAW_ANALOG_ROIS",
    "NAME_DRAW_DIGITAL_ROIS",
    "NAME_DRAW_REFS",
    "NAME_FINAL",
    "NAME_INITIAL_ROTATE",
    "NAME_METERS",
    "NAME_SERVICES",
    "SetupPage",
    "resolve_model_path",
    "steps_order",
]

svg_grid = """
<defs>
    <pattern id="smallGrid" width="8" height="8" patternUnits="userSpaceOnUse">
        <path d="M 8 0 L 0 0 0 8" fill="none" stroke="gray" stroke-width="0.5"/>
    </pattern>
    <pattern id="grid" width="80" height="80" patternUnits="userSpaceOnUse">
        <rect width="80" height="80" fill="url(#smallGrid)"/>
        <path d="M 80 0 L 0 0 0 80" fill="none" stroke="gray" stroke-width="1"/>
    </pattern>
</defs>
"""


class SetupPage(BasePage):
    def __init__(self, callbacks: Callbacks) -> None:
        super().__init__(callbacks)

        self.config_manager = WizardConfigManager(self.callbacks)
        self.navigator = WizardNavigator(self.callbacks)

        self.interactive_image: ui.interactive_image
        self.image_details: ui.label
        self.mouse_position: ui.label
        self.selected_position: ui.label
        self.spinner: ui.spinner

        self.download_image_step: DownloadImageStep
        self.initial_rotate_step: InitialRotateStep
        self.draw_refs_step: DrawRefsStep
        self.adjust_step: AdjustStep
        self.draw_digital_rois_step: DrawDigitalRoisStep
        self.draw_analog_rois_step: DrawAnalogRoisStep
        self.meters_step: MeterStep
        self.services_step: ServicesStep
        self.final_step: FinalStep
        self.stepper: ui.stepper
        self.wizard_prev_btn: ui.button
        self.wizard_step_badge: ui.label
        self.wizard_next_btn: ui.button
        self.comparison_container: ui.element
        self.comparison_image: ui.image

        self.config: Config
        self.image: str = ""  # base64 str
        self.processed_image: str = ""
        self.refs = ""
        self.digital_rois = ""
        self.analog_rois = ""

    @property
    def previous_step(self) -> str:
        return self.navigator.previous_step

    @previous_step.setter
    def previous_step(self, value: str) -> None:
        self.navigator.previous_step = value

    @property
    def refs_enabled_in_image(self) -> bool:
        return self.navigator.refs_enabled_in_image

    @refs_enabled_in_image.setter
    def refs_enabled_in_image(self, value: bool) -> None:
        self.navigator.refs_enabled_in_image = value

    @property
    def digital_rois_enabled_in_image(self) -> bool:
        return self.navigator.digital_rois_enabled_in_image

    @digital_rois_enabled_in_image.setter
    def digital_rois_enabled_in_image(self, value: bool) -> None:
        self.navigator.digital_rois_enabled_in_image = value

    @property
    def analog_rois_enabled_in_image(self) -> bool:
        return self.navigator.analog_rois_enabled_in_image

    @analog_rois_enabled_in_image.setter
    def analog_rois_enabled_in_image(self, value: bool) -> None:
        self.navigator.analog_rois_enabled_in_image = value

    async def show(self) -> None:

        def update_svg(draw: str = "") -> None:
            self.interactive_image.content = f"""
                {svg_grid}
                <rect width="100%" height="100%" fill="url(#grid)" />
                {self.refs if self.refs_enabled_in_image else ""}
                {self.digital_rois if self.digital_rois_enabled_in_image else ""}
                {self.analog_rois if self.analog_rois_enabled_in_image else ""}
                {draw if draw is not None else ""}
                """

        def set_image(base64_str: str) -> None:
            if not base64_str or base64_str == self.image:
                return
            self.image = base64_str
            print_image_hash("set_image", base64_str)
            w, h = ImageUtils.image_size(
                ImageUtils.convert_base64_str_to_image(base64_str)
            )
            self.image_details.text = f"Size: {w}x{h}"
            self.interactive_image.set_source(f"data:image/png;base64,{base64_str}")
            self.interactive_image.update()
            update_svg()

        last_mouse_pos_update = 0.0

        def mouse_handler(e: events.MouseEventArguments) -> None:
            nonlocal last_mouse_pos_update
            if e.type == "mousemove":
                now = time.monotonic()
                if now - last_mouse_pos_update >= 0.040:
                    last_mouse_pos_update = now
                    self.mouse_position.text = f"X: {e.image_x:.0f}, Y: {e.image_y:.0f}"
            elif e.type == "mousedown":
                self.selected_position.text = f"X: {e.image_x:.0f}, Y: {e.image_y:.0f}"

            if stepper.value == NAME_DRAW_REFS:
                self.draw_refs_step.mouse_event(e)
            elif stepper.value == NAME_DRAW_DIGITAL_ROIS:
                self.draw_digital_rois_step.mouse_event(e)
            elif stepper.value == NAME_DRAW_ANALOG_ROIS:
                self.draw_analog_rois_step.mouse_event(e)

        def print_image_hash(text: str, image: str) -> None:
            if image is None or image == "":
                logger.debug(f"{text}, hash: empty")
            else:
                data = image.encode("utf-8")
                logger.debug(f"{text}, hash: {sha256(data).hexdigest()}")

        def set_refs_to_svg_func(refs: str) -> None:
            self.refs = refs
            update_svg()

        def set_digital_rois_to_svg_func(rois: str) -> None:
            self.digital_rois = rois
            update_svg()

        def set_analog_rois_to_svg_func(rois: str) -> None:
            self.analog_rois = rois
            update_svg()

        def show_temp_draw_in_svg_func(draw: str) -> None:
            update_svg(draw)

        def gather_config() -> Config:
            self.config = self.config_manager.gather_config(
                download_image_step=self.download_image_step,
                initial_rotate_step=self.initial_rotate_step,
                draw_refs_step=self.draw_refs_step,
                adjust_step=self.adjust_step,
                draw_digital_rois_step=self.draw_digital_rois_step,
                draw_analog_rois_step=self.draw_analog_rois_step,
                meters_step=self.meters_step,
                services_step=self.services_step,
            )
            return self.config

        def save_refs() -> None:
            self.config_manager.save_refs(
                draw_refs_step=self.draw_refs_step,
                initial_rotate_step=self.initial_rotate_step,
                fallback_image_b64=self.image,
            )

        def set_comparison_image(base64_str: str = "") -> None:
            if (
                not hasattr(self, "comparison_container")
                or self.comparison_container is None
            ):
                return
            if base64_str:
                self.comparison_image.set_source(f"data:image/jpeg;base64,{base64_str}")
                self.comparison_container.set_visibility(True)

                if (
                    hasattr(self, "main_image_header")
                    and self.main_image_header is not None
                ):
                    self.main_image_header.set_visibility(True)
                    self.main_image_label.text = "Original Image"
                    self.main_image_tag.text = "ORIGINAL"
            else:
                self.comparison_container.set_visibility(False)
                if (
                    hasattr(self, "main_image_header")
                    and self.main_image_header is not None
                ):
                    if (
                        hasattr(self, "stepper")
                        and getattr(self.stepper, "value", "") == NAME_ADJUST
                    ):
                        self.main_image_header.set_visibility(True)
                        self.main_image_label.text = "Adjusted Image Preview"
                        self.main_image_tag.text = "ADJUSTED"
                    else:
                        self.main_image_header.set_visibility(False)

        def handle_stepper_change(step: str) -> None:
            self.navigator.handle_stepper_change(
                step=step,
                download_image_step=self.download_image_step,
                initial_rotate_step=self.initial_rotate_step,
                draw_refs_step=self.draw_refs_step,
                adjust_step=self.adjust_step,
                draw_digital_rois_step=self.draw_digital_rois_step,
                draw_analog_rois_step=self.draw_analog_rois_step,
                meters_step=self.meters_step,
                services_step=self.services_step,
                final_step=self.final_step,
                set_image_fn=set_image,
                set_comparison_image_fn=set_comparison_image,
                update_svg_fn=update_svg,
                gather_config_fn=gather_config,
                wizard_prev_btn=getattr(self, "wizard_prev_btn", None),
                wizard_step_badge=getattr(self, "wizard_step_badge", None),
                wizard_next_btn=getattr(self, "wizard_next_btn", None),
                fallback_image=self.image,
            )

        def update_wizard_nav(current_step: str) -> None:
            self.navigator.update_wizard_nav(
                current_step=current_step,
                wizard_prev_btn=getattr(self, "wizard_prev_btn", None),
                wizard_step_badge=getattr(self, "wizard_step_badge", None),
                wizard_next_btn=getattr(self, "wizard_next_btn", None),
            )

        async def on_wizard_next() -> None:
            self.stepper.next()

        def show_offline_placeholder(
            message: str = "Camera Offline",
            subtext: str = "Check camera URL and click Download to retry",
            is_error: bool = True,
        ) -> None:
            stroke_color = "#ef4444" if is_error else "#6366f1"
            circle_color = "#334155" if is_error else "#1e1b4b"
            strike_line = (
                '<line x1="280" y1="160" x2="360" y2="220" '
                'stroke="#ef4444" stroke-width="3" stroke-linecap="round"/>'
                if is_error
                else ""
            )
            svg = (
                '<svg width="640" height="480" viewBox="0 0 640 480" '
                'xmlns="http://www.w3.org/2000/svg">'
                '<rect width="100%" height="100%" fill="#1e293b"/>'
                f'<circle cx="320" cy="190" r="48" fill="{circle_color}"/>'
                '<path d="M 296 214 L 344 166 M 304 174 L 320 174 L 326 166 '
                "L 338 166 L 344 174 L 352 174 C 356 174 360 178 360 182 "
                "L 360 206 C 360 210 356 214 352 214 L 288 214 C 284 214 "
                '280 210 280 206 L 280 182 C 280 178 284 174 288 174 Z" '
                f'stroke="{stroke_color}" stroke-width="3" fill="none" '
                'stroke-linecap="round" stroke-linejoin="round"/>'
                f"{strike_line}"
                f'<text x="320" y="275" text-anchor="middle" fill="#f8fafc" '
                'font-family="system-ui, -apple-system, sans-serif" '
                f'font-size="20" font-weight="600">{message}</text>'
                f'<text x="320" y="305" text-anchor="middle" fill="#94a3b8" '
                'font-family="system-ui, -apple-system, sans-serif" '
                f'font-size="13">{subtext}</text>'
                "</svg>"
            )
            b64_svg = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
            self.interactive_image.set_source(f"data:image/svg+xml;base64,{b64_svg}")
            self.interactive_image.content = ""
            if hasattr(self, "image_details") and self.image_details is not None:
                self.image_details.text = f"Size: 640x480 ({message})"

        def on_download_error(err_msg: str = "") -> None:
            show_offline_placeholder(
                message="Camera Offline / Unreachable",
                subtext="Check camera URL and click Download to retry",
                is_error=True,
            )

        async def start_clean_config(create_backup: bool = True) -> None:
            try:
                if create_backup:
                    try:
                        curr_cfg = self.callbacks.get_config()
                        curr_cfg.create_backup(
                            ini_file=f"{curr_cfg.config_dir}/config.ini",
                            tag="Pre-Clean Reset",
                        )
                    except Exception as b_err:
                        logger.warning(
                            f"Could not create pre-clean safety backup: {b_err}"
                        )

                curr_cfg = self.callbacks.get_config()
                clean_config = Config.create_clean_default(
                    config_dir=curr_cfg.config_dir,
                    data_dir=curr_cfg.data_dir,
                )

                self.download_image_step.load_from_config(clean_config.image_source)
                self.initial_rotate_step.load_from_config(clean_config.alignment)
                self.draw_refs_step.load_from_config(clean_config.alignment.ref_images)
                self.adjust_step.load_from_config(clean_config)
                self.draw_digital_rois_step.load_from_config(
                    clean_config.digital_readout
                )
                self.draw_analog_rois_step.load_from_config(clean_config.analog_readout)
                self.meters_step.load_from_config(clean_config.meter_configs)
                self.services_step.load_from_config(clean_config)

                # Reset all step image state
                self.image = ""
                self.processed_image = ""
                self.download_image_step.image = ""
                self.initial_rotate_step.image = ""
                self.initial_rotate_step.org_image = ""
                self.draw_refs_step.image = ""
                self.adjust_step.image = ""
                self.adjust_step.org_image = ""
                self.adjust_step.ref_images = []
                self.draw_digital_rois_step.image = ""
                self.draw_analog_rois_step.image = ""
                self.meters_step.image = ""
                self.services_step.image = ""
                self.final_step.image = ""

                # Reset ROI svg strings and visibility
                self.refs = ""
                self.digital_rois = ""
                self.analog_rois = ""
                self.refs_enabled_in_image = False
                self.digital_rois_enabled_in_image = False
                self.analog_rois_enabled_in_image = False

                self.previous_step = NAME_DOWNLOAD_IMAGE
                self.interactive_image.content = ""
                show_offline_placeholder(
                    message="Ready for New Setup",
                    subtext="Enter camera URL and click Download to start",
                    is_error=False,
                )
                if (
                    hasattr(self, "comparison_container")
                    and self.comparison_container is not None
                ):
                    self.comparison_container.set_visibility(False)

                if hasattr(self, "stepper") and self.stepper is not None:
                    self.stepper.value = NAME_DOWNLOAD_IMAGE
                    update_wizard_nav(NAME_DOWNLOAD_IMAGE)

                ui.notify("Wizard reset to clean configuration", type="positive")
            except Exception as e:
                logger.error(f"Failed to reset wizard to clean config: {e}")
                ui.notify(f"Clean reset failed: {e}", type="negative")

        def open_clean_config_dialog() -> None:
            open_confirm_dialog(
                title="Start Clean Configuration?",
                subtitle="Reset all steps to blank defaults",
                message=(
                    "All drawn reference markers, digital/analog ROIs, custom meters, "
                    "and image adjustments will be cleared. You can start calibrating "
                    "your meter from scratch."
                ),
                confirm_label="Start Clean",
                confirm_icon="cleaning_services",
                color_scheme="rose",
                icon="cleaning_services",
                checkbox_label="Create safety backup before clearing",
                checkbox_default=True,
                on_confirm=lambda create_backup: start_clean_config(
                    create_backup=create_backup
                ),
            )

        async def reset_from_config_file() -> None:
            try:
                config_str = self.callbacks.load_config_file()
                fresh_config = Config()
                fresh_config.load_from_string(config_str)

                for img in fresh_config.alignment.ref_images:
                    if img.w == 0 or img.h == 0:
                        img.w, img.h = ImageUtils.image_size_from_file(img.file_name)

                self.download_image_step.load_from_config(fresh_config.image_source)
                self.initial_rotate_step.load_from_config(fresh_config.alignment)
                self.draw_refs_step.load_from_config(fresh_config.alignment.ref_images)
                self.adjust_step.load_from_config(fresh_config)
                self.draw_digital_rois_step.load_from_config(
                    fresh_config.digital_readout
                )
                self.draw_analog_rois_step.load_from_config(fresh_config.analog_readout)
                self.meters_step.load_from_config(fresh_config.meter_configs)
                self.services_step.load_from_config(fresh_config)

                self.previous_step = NAME_DOWNLOAD_IMAGE
                if hasattr(self, "stepper") and self.stepper is not None:
                    self.stepper.value = NAME_DOWNLOAD_IMAGE

                if fresh_config.image_source.url:
                    await self.download_image_step.download()

                ui.notify("Wizard reset from config file", type="positive")
            except Exception as e:
                logger.error(f"Failed to reset wizard: {e}")
                ui.notify(f"Reset failed: {e}", type="negative")

        def open_reset_dialog() -> None:
            open_confirm_dialog(
                title="Reset Configuration Wizard?",
                subtitle="Discard unsaved changes",
                message=(
                    "All wizard fields, ROIs, and adjustment parameters will be "
                    "reloaded from the current config file on disk."
                ),
                confirm_label="Reset to File",
                confirm_icon="restart_alt",
                color_scheme="amber",
                icon="restart_alt",
                on_confirm=reset_from_config_file,
            )

        def open_restore_backup_dialog() -> None:
            async def on_restore(target_name: str, target_time: str) -> None:
                try:
                    self.callbacks.restore_config_backup(target_name)
                    await reset_from_config_file()
                    ui.notify(
                        f"Wizard restored from backup {target_time}",
                        type="positive",
                    )
                except Exception as err:
                    ui.notify(f"Restore failed: {err}", type="negative")

            open_config_history_dialog(
                callbacks=self.callbacks,
                title="Restore Wizard from Backup",
                subtitle="Select a saved snapshot to load into the wizard",
                show_snapshot_creator=False,
                on_restore=on_restore,
                allow_diff=False,
                allow_delete=False,
                max_width="max-w-xl",
            )

        with ui.row().classes(
            "w-full justify-between items-center mb-2 px-4 py-2 bg-slate-900/60 "
            "border border-white/10 rounded-xl shadow-md backdrop-blur-md shrink-0"
        ):
            with ui.row().classes("items-center gap-3"):
                ui.icon("auto_fix_high", size="md").classes("text-indigo-400")
                with ui.column().classes("gap-0"):
                    ui.label("Configuration Wizard").classes(
                        "text-lg font-bold text-slate-100 leading-tight"
                    )
                    ui.label("Interactive Calibration & Deployment Pipeline").classes(
                        "text-xs text-slate-400"
                    )
                self.spinner = ui.spinner("dots", size="md", color="indigo")
                self.spinner.visible = False
            with ui.row().classes("items-center gap-2"):
                ui.button(
                    "Start Clean",
                    icon="cleaning_services",
                    on_click=open_clean_config_dialog,
                ).props("outline dense").classes(
                    "border-white/20 text-slate-300 hover:bg-white/10 text-xs "
                    "font-medium px-3 py-1"
                ).tooltip(
                    "Clear all ROIs and settings to start a new setup from scratch"
                )

                ui.button(
                    "Restore Backup",
                    icon="history",
                    on_click=open_restore_backup_dialog,
                ).props("outline dense").classes(
                    "border-white/20 text-slate-300 hover:bg-white/10 text-xs "
                    "font-medium px-3 py-1"
                ).tooltip(
                    "Select and restore a previous configuration backup"
                )

                ui.button(
                    "Reset to File",
                    icon="restart_alt",
                    on_click=open_reset_dialog,
                ).props("outline dense").classes(
                    "border-white/20 text-slate-300 hover:bg-white/10 text-xs "
                    "font-medium px-3 py-1"
                ).tooltip(
                    "Reload all wizard values from saved config file"
                )

                ui.label("9-Step Setup").classes(
                    "text-xs font-semibold text-indigo-300 bg-indigo-950/70 "
                    "border border-indigo-500/30 px-3 py-1 rounded-full shadow-inner"
                )

        self.download_image_step = DownloadImageStep(
            name=NAME_DOWNLOAD_IMAGE,
            set_image_callback=set_image,
            on_error_callback=on_download_error,
            spinner=self.spinner,
        )
        self.initial_rotate_step = InitialRotateStep(
            name=NAME_INITIAL_ROTATE,
            set_image_callback=set_image,
            spinner=self.spinner,
        )
        self.draw_refs_step = DrawRefsStep(
            name=NAME_DRAW_REFS,
            name_template="Ref",
            set_image_callback=set_image,
            set_rois_to_svg_func=set_refs_to_svg_func,
            show_temp_draw_in_svg_func=show_temp_draw_in_svg_func,
            spinner=self.spinner,
        )
        self.adjust_step = AdjustStep(
            name=NAME_ADJUST,
            set_image_callback=set_image,
            set_comparison_callback=set_comparison_image,
            spinner=self.spinner,
        )
        self.draw_digital_rois_step = DrawDigitalRoisStep(
            name=NAME_DRAW_DIGITAL_ROIS,
            name_template="Digital",
            set_image_callback=set_image,
            set_rois_to_svg_func=set_digital_rois_to_svg_func,
            show_temp_draw_in_svg_func=show_temp_draw_in_svg_func,
            digital_models_dir=self.callbacks.get_config().digital_models_dir,
            spinner=self.spinner,
        )
        self.draw_analog_rois_step = DrawAnalogRoisStep(
            name=NAME_DRAW_ANALOG_ROIS,
            name_template="Analog",
            set_image_callback=set_image,
            set_rois_to_svg_func=set_analog_rois_to_svg_func,
            show_temp_draw_in_svg_func=show_temp_draw_in_svg_func,
            analog_models_dir=self.callbacks.get_config().analog_models_dir,
            spinner=self.spinner,
        )
        self.meters_step = MeterStep(
            name=NAME_METERS,
            set_image_callback=set_image,
            get_digit_names_func=lambda: WizardConfigManager.get_digit_names(
                self.draw_digital_rois_step, self.draw_analog_rois_step
            ),
            spinner=self.spinner,
        )
        self.services_step = ServicesStep(
            name=NAME_SERVICES,
            set_image_callback=set_image,
            spinner=self.spinner,
        )
        self.final_step = FinalStep(
            name=NAME_FINAL,
            callbacks=self.callbacks,
            set_image_callback=set_image,
            save_refs_func=save_refs,
            spinner=self.spinner,
        )

        with (
            ui.splitter(value=42, limits=(20, 80))
            .classes("w-full flex-1 min-h-0")
            .props(
                'separator-class="bg-white/10 hover:bg-indigo-500/70 '
                'transition-all duration-200 cursor-col-resize" '
                'separator-style="width: 2px; margin: 0 8px;"'
            ) as splitter
        ):
            with (
                splitter.add_slot("separator"),
                ui.element("div")
                .classes(
                    "w-2.5 h-8 -ml-[4px] rounded-full bg-slate-800/90 border "
                    "border-white/20 flex flex-col items-center justify-center "
                    "gap-0.5 hover:bg-indigo-600 hover:border-indigo-400 "
                    "transition-all duration-150 shadow-md cursor-col-resize"
                )
                .tooltip("Resize panels"),
            ):
                ui.element("div").classes("w-1 h-1 rounded-full bg-slate-400/80")
                ui.element("div").classes("w-1 h-1 rounded-full bg-slate-400/80")
                ui.element("div").classes("w-1 h-1 rounded-full bg-slate-400/80")
            with (
                splitter.before,
                ui.column().classes(
                    "w-full h-full rounded-xl bg-slate-950/80 p-2.5 "
                    "border border-white/10 shadow-2xl backdrop-blur-md "
                    "gap-2.5 overflow-y-auto overflow-x-hidden min-w-0 no-wrap"
                ),
            ):
                # Original Image Card
                with ui.card().classes(
                    "w-full p-2 bg-slate-900/60 border border-white/10 "
                    "rounded-xl shadow-md flex flex-col gap-2 shrink-0 min-w-0"
                ):
                    with ui.row().classes(
                        "w-full min-w-0 shrink-0 justify-between items-center px-1"
                    ) as self.main_image_header:
                        with ui.row().classes("items-center gap-1.5 min-w-0"):
                            self.main_image_icon = ui.icon("image", size="xs").classes(
                                "text-indigo-400 shrink-0"
                            )
                            self.main_image_label = ui.label("Original Image").classes(
                                "text-xs font-semibold text-slate-300 truncate"
                            )
                        self.main_image_tag = ui.label("ORIGINAL").classes(
                            "text-[10px] font-mono font-bold text-cyan-400 "
                            "px-2 py-0.5 rounded-md bg-cyan-950/60 "
                            "border border-cyan-500/30 shrink-0"
                        )

                    self.interactive_image = ui.interactive_image(
                        size=(640, 480),
                        on_mouse=mouse_handler,
                        events=["mousedown", "mouseup", "mousemove"],
                        cross=True,
                    ).classes(
                        "w-full max-w-full min-w-0 shrink-0 rounded-lg "
                        "bg-slate-950 shadow-inner interactive-image-canvas"
                    )
                    with ui.row().classes(
                        "w-full min-w-0 shrink-0 justify-between items-center "
                        "px-2.5 py-1 rounded-lg bg-slate-950/80 border "
                        "border-white/5 text-xs text-slate-400 gap-2"
                    ):
                        self.image_details = ui.label("").classes(
                            "font-mono text-cyan-400 font-semibold truncate"
                        )
                        with (
                            ui.element("div")
                            .props('id="roi-move-indicator"')
                            .classes(
                                "items-center gap-1 px-2 py-0.5 rounded bg-amber-500/20 "
                                "border border-amber-500/40 text-[10px] font-mono font-bold "
                                "text-amber-300 animate-pulse shrink-0"
                            )
                        ):
                            ui.icon("open_with", size="12px").classes("text-amber-400")
                            ui.label("MOVE MODE")
                        self.mouse_position = ui.label("").classes(
                            "font-mono text-slate-400 truncate"
                        )
                        self.selected_position = ui.label("").classes(
                            "font-mono text-emerald-400 font-bold truncate"
                        )
                    show_offline_placeholder(
                        "No Image Loaded",
                        "Enter camera URL and click Download to start",
                    )

                # Adjusted Image Preview Card (under the status bar)
                with ui.card().classes(
                    "w-full p-2 bg-slate-900/60 border border-white/10 "
                    "rounded-xl shadow-md flex flex-col gap-2 shrink-0 min-w-0"
                ) as self.comparison_container:
                    with ui.row().classes(
                        "w-full min-w-0 shrink-0 items-center justify-between px-1"
                    ):
                        with ui.row().classes("items-center gap-1.5 min-w-0"):
                            ui.icon("auto_fix_high", size="xs").classes(
                                "text-emerald-400 shrink-0"
                            )
                            ui.label("Adjusted Image").classes(
                                "text-xs font-semibold text-slate-300 truncate"
                            )
                        ui.label("ADJUSTED").classes(
                            "text-[10px] font-mono font-bold text-emerald-400 "
                            "px-2 py-0.5 rounded-md bg-emerald-950/60 "
                            "border border-emerald-500/30 shrink-0"
                        )

                    self.comparison_image = (
                        ui.image("")
                        .props('fit=contain no-spinner ratio="1.3333"')
                        .classes(
                            "w-full max-w-full min-w-0 shrink-0 aspect-[4/3] "
                            "min-h-[120px] rounded-lg bg-slate-950 shadow-inner"
                        )
                    )
                self.comparison_container.set_visibility(False)

            with (
                splitter.after,
                ui.element("div").classes(
                    "w-full h-full flex flex-col justify-between min-h-0 overflow-hidden pr-1"
                ),
            ):
                with (
                    ui.element("div").classes(
                        "w-full flex-1 min-h-0 overflow-y-auto pr-1"
                    ),
                    ui.stepper(on_value_change=lambda x: handle_stepper_change(x.value))
                    .props("vertical")
                    .classes(
                        "w-full rounded-2xl shadow-xl bg-slate-900/40 "
                        "border border-white/5"
                    ) as stepper,
                ):
                    self.stepper = stepper
                    await self.download_image_step.show(stepper, first_step=True)
                    await self.initial_rotate_step.show(stepper)
                    await self.draw_refs_step.show(stepper)
                    await self.adjust_step.show(stepper)
                    await self.draw_digital_rois_step.show(stepper)
                    await self.draw_analog_rois_step.show(stepper)
                    await self.meters_step.show(stepper)
                    await self.services_step.show(stepper)
                    await self.final_step.show(stepper, last_step=True)

                # Persistent Docked Bottom Navigation Bar
                with ui.row().classes(
                    "w-full justify-between items-center px-4 py-2 mt-1.5 "
                    "bg-slate-900/90 border border-white/10 rounded-xl "
                    "shadow-2xl backdrop-blur-md shrink-0"
                ):
                    with ui.row().classes("items-center gap-2"):
                        self.wizard_prev_btn = (
                            ui.button(
                                "Back",
                                icon="arrow_back",
                                on_click=lambda: self.stepper.previous(),
                            )
                            .props("flat no-caps color=grey text-color=white")
                            .classes(
                                "px-3.5 py-1.5 rounded-lg text-sm font-medium "
                                "hover:bg-white/10 transition-colors"
                            )
                        )
                        self.wizard_prev_btn.visible = False

                        self.wizard_step_badge = ui.label(
                            f"Step 1 of {len(steps_order)}: {steps_order[0]}"
                        ).classes(
                            "text-xs font-semibold text-slate-300 font-mono "
                            "bg-slate-950/70 border border-white/10 px-2.5 "
                            "py-1 rounded-lg shadow-inner"
                        )

                    self.wizard_next_btn = (
                        ui.button(
                            "Continue",
                            on_click=on_wizard_next,
                        )
                        .props("unelevated no-caps icon-right=arrow_forward")
                        .classes(
                            "px-4 py-1.5 rounded-lg text-sm font-semibold "
                            "bg-blue-600 hover:bg-blue-500 "
                            "text-white shadow-md shadow-blue-950/40 "
                            "transition-colors"
                        )
                    )

        update_wizard_nav(self.stepper.value or steps_order[0])

        for img in self.callbacks.get_config().alignment.ref_images:
            if img.w == 0 or img.h == 0:
                img.w, img.h = ImageUtils.image_size_from_file(img.file_name)

        # After stepper UI is created:
        config = self.callbacks.get_config()

        self.download_image_step.load_from_config(config.image_source)
        self.initial_rotate_step.load_from_config(config.alignment)
        self.draw_refs_step.load_from_config(config.alignment.ref_images)
        self.adjust_step.load_from_config(config)
        self.draw_digital_rois_step.load_from_config(config.digital_readout)
        self.draw_analog_rois_step.load_from_config(config.analog_readout)
        self.meters_step.load_from_config(config.meter_configs)
        self.services_step.load_from_config(config)

        # Automatically fetch the initial image if URL is configured
        if config.image_source.url:
            await self.download_image_step.download()
