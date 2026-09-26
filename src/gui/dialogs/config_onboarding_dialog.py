"""Dialog presented when config.ini is missing, offering choice of setup mode."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from nicegui import ui

from gui.theme import (
    CARD_SELECTABLE_ACTIVE,
    CARD_SELECTABLE_ACTIVE_MODIFIERS,
    CARD_SELECTABLE_INACTIVE,
    CARD_SELECTABLE_INACTIVE_MODIFIERS,
    DIALOG_CARD,
    DIALOG_HEADER_ROW,
    HEADING_SECTION,
)

if TYPE_CHECKING:
    from callbacks import Callbacks

logger = logging.getLogger(__name__)


def show_config_onboarding_dialog(
    callbacks: Callbacks,
    tabs: Any | None = None,
    setup_tab: Any | None = None,
    load_tab_fn: Any | None = None,
) -> None:
    """Displays onboarding modal allowing user to choose between demo config or fresh meter setup."""
    target_file = callbacks.get_target_config_file() or "config/config.ini"

    with (
        ui.dialog().props("persistent backdrop-filter='blur(8px)'") as dialog,
        ui.card().classes(DIALOG_CARD + " max-w-xl"),
    ):
        with (
            ui.row().classes(DIALOG_HEADER_ROW),
            ui.row().classes("items-center gap-2"),
        ):
            ui.icon("settings_suggest", size="sm").classes("text-indigo-400")
            ui.label("Configuration Setup").classes(HEADING_SECTION)

        ui.label(
            f"The configuration file '{target_file}' was not found. "
            "How would you like to set up this meter instance?"
        ).classes("text-sm text-slate-300")

        selected_mode = {"value": "wizard"}

        # Choice 1: Start Setup Wizard (Recommended)
        with (
            ui.card().classes(CARD_SELECTABLE_ACTIVE) as wizard_card,
            ui.row().classes("items-center justify-between w-full no-wrap"),
        ):
            with ui.row().classes("items-center gap-3"):
                ui.icon("auto_fix_high", size="md").classes("text-indigo-400 shrink-0")
                with ui.column().classes("gap-0.5"):
                    with ui.row().classes("items-center gap-2"):
                        wizard_title = ui.label("Create New Configuration").classes(
                            "font-semibold text-white"
                        )
                        ui.badge("Recommended", color="indigo").props("rounded outline")
                    ui.label(
                        "Select your water meter model (mechanical dials, drums) "
                        "and calibrate ROIs step-by-step using the Setup Wizard."
                    ).classes("text-xs text-slate-400")
            wizard_radio = ui.icon("radio_button_checked", size="sm").classes(
                "text-indigo-400 shrink-0 text-xl"
            )

        # Choice 2: Copy Default Demo Configuration
        with (
            ui.card().classes(CARD_SELECTABLE_INACTIVE) as demo_card,
            ui.row().classes("items-center justify-between w-full no-wrap"),
        ):
            with ui.row().classes("items-center gap-3"):
                ui.icon("content_copy", size="md").classes("text-cyan-400 shrink-0")
                with ui.column().classes("gap-0.5"):
                    demo_title = ui.label("Copy Default Demo Configuration").classes(
                        "font-semibold text-slate-300"
                    )
                    ui.label(
                        "Copy the built-in reference configuration, demo images, and sample markers. "
                        "Best for quickly exploring the digitizer."
                    ).classes("text-xs text-slate-400")
            demo_radio = ui.icon("radio_button_unchecked", size="sm").classes(
                "text-slate-500 shrink-0 text-xl"
            )

        def select_mode(mode: str) -> None:
            selected_mode["value"] = mode
            if mode == "wizard":
                wizard_card.classes(
                    remove=CARD_SELECTABLE_INACTIVE_MODIFIERS,
                    add=CARD_SELECTABLE_ACTIVE_MODIFIERS,
                )
                wizard_radio.name = "radio_button_checked"
                wizard_radio.classes(replace="text-indigo-400 shrink-0 text-xl")
                wizard_title.classes(replace="font-semibold text-white")

                demo_card.classes(
                    remove=CARD_SELECTABLE_ACTIVE_MODIFIERS,
                    add=CARD_SELECTABLE_INACTIVE_MODIFIERS,
                )
                demo_radio.name = "radio_button_unchecked"
                demo_radio.classes(replace="text-slate-500 shrink-0 text-xl")
                demo_title.classes(replace="font-semibold text-slate-300")
            else:
                demo_card.classes(
                    remove=CARD_SELECTABLE_INACTIVE_MODIFIERS,
                    add=CARD_SELECTABLE_ACTIVE_MODIFIERS,
                )
                demo_radio.name = "radio_button_checked"
                demo_radio.classes(replace="text-indigo-400 shrink-0 text-xl")
                demo_title.classes(replace="font-semibold text-white")

                wizard_card.classes(
                    remove=CARD_SELECTABLE_ACTIVE_MODIFIERS,
                    add=CARD_SELECTABLE_INACTIVE_MODIFIERS,
                )
                wizard_radio.name = "radio_button_unchecked"
                wizard_radio.classes(replace="text-slate-500 shrink-0 text-xl")
                wizard_title.classes(replace="font-semibold text-slate-300")

        wizard_card.on("click", lambda: select_mode("wizard"))
        demo_card.on("click", lambda: select_mode("demo"))

        with ui.row().classes(
            "w-full justify-end items-center gap-2 pt-3 border-t border-white/10"
        ):

            async def apply_choice() -> None:
                dialog.close()
                if selected_mode["value"] == "wizard":
                    success = callbacks.init_profile_for_wizard()
                    if success:
                        ui.notify(
                            "Created profile baseline. Starting Setup Wizard...",
                            type="positive",
                        )
                        callbacks.use_config()
                        if tabs and setup_tab:
                            tabs.set_value(setup_tab)
                            if load_tab_fn:
                                await load_tab_fn(setup_tab)
                    else:
                        ui.notify(
                            "Failed to initialize profile directory", type="negative"
                        )
                else:
                    success = callbacks.copy_default_config()
                    if success:
                        ui.notify("Copied default demo configuration.", type="positive")
                        callbacks.use_config()
                        ui.run_javascript("window.location.reload()")
                    else:
                        ui.notify(
                            "Failed to copy default configuration", type="negative"
                        )

            ui.button("Continue", on_click=apply_choice).props(
                "unelevated color=primary icon-right=arrow_forward"
            ).classes("px-5 py-2 font-semibold")

    dialog.open()
