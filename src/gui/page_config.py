import dataclasses
import json
from nicegui import ui

from callbacks import Callbacks
from configuration import Config


class ConfigPage:
    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks
        self.txt = self.callbacks.load_config_file()
        self.new_config_saved = False

    def show(self):
        def check_buttons() -> None:
            button_save.enabled = editor.value != self.txt
            button_use_config.enabled = self.new_config_saved

        def save_config() -> None:
            if syntax_check() is True:
                self.callbacks.save_config_file(editor.value)
                self.new_config_saved = True
                ui.notify("Config saved", type="positive")
            self.txt = editor.value
            check_buttons()

        def load_config() -> None:
            self.txt = self.callbacks.load_config_file()
            editor.value = self.txt
            check_buttons()

        def show_config() -> None:
            try:
                config = Config()
                config.load_from_string(editor.value)
                j = json.dumps(dataclasses.asdict(config), indent=4)
                with ui.dialog().classes("w-full w-screen") as dialog:
                    with ui.card().classes("bg-gray w-screen"):
                        ui.label("Config in JSON format:")
                        ui.code(j, language="json").classes("w-full")
                dialog.open()
            except Exception as e:
                ui.notify(f"Syntax error: {e}", type="negative")

        def use_config() -> None:
            self.callbacks.use_config()
            self.new_config_saved = False
            check_buttons()
            ui.notify("Config taken in use", type="positive")

        def syntax_check() -> bool:
            try:
                config = Config()
                config.load_from_string(editor.value)
                ui.notify("Syntax is correct", type="positive")
                check_buttons()
                return True
            except Exception as e:
                ui.notify(f"Syntax error: {e}", type="negative")
                button_save.disable()
                return False

        ui.label("Config").classes("text-h4")
        with ui.splitter(horizontal=True).classes("w-full") as splitter:
            with splitter.before:
                with ui.row():
                    ui.button(icon="refresh", on_click=load_config).tooltip(
                        "Reload config from file"
                    )
                    ui.button(icon="verified", on_click=syntax_check).tooltip(
                        "Check syntax"
                    )
                    button_save = ui.button(icon="save", on_click=save_config).tooltip(
                        "Save config to file"
                    )
                    button_use_config = ui.button(
                        icon="sym_s_reopen_window",
                        on_click=use_config,
                    ).tooltip("Take config in use")

                    ui.button(icon="preview", on_click=show_config).tooltip(
                        "Show parsed config"
                    )
                ui.separator()
            with splitter.after:
                editor = (
                    ui.textarea(
                        value=self.callbacks.load_config_file(), on_change=check_buttons
                    )
                    .classes("w-full h-full font-mono")
                    .props("autoResize rows=50")
                )
        check_buttons()
