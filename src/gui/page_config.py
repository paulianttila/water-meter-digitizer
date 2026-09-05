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
                ui.notify("Configuration saved to file", type="positive")
            self.txt = editor.value
            check_buttons()

        def load_config() -> None:
            self.txt = self.callbacks.load_config_file()
            editor.value = self.txt
            check_buttons()
            ui.notify("Configuration reloaded from disk", type="info")

        def show_config() -> None:
            try:
                config = Config()
                config.load_from_string(editor.value)
                j = config.model_dump_json(indent=4)
                with (
                    ui.dialog() as dialog,
                    ui.card().classes(
                        "w-full max-w-4xl p-6 bg-slate-900 "
                        "border border-white/10 rounded-xl"
                    ),
                ):
                    with ui.row().classes("w-full justify-between items-center mb-4"):
                        ui.label("Parsed Configuration (JSON)").classes(
                            "text-h5 font-['Outfit']"
                        )
                        ui.button(icon="close", on_click=dialog.close).props(
                            "flat round dense"
                        )
                    ui.code(j, language="json").classes(
                        "w-full max-h-[70vh] overflow-auto rounded-lg "
                        "bg-slate-950 p-4 border border-white/5"
                    )
                dialog.open()
            except Exception as e:
                ui.notify(f"Syntax error: {e}", type="negative")

        def use_config() -> None:
            self.callbacks.use_config()
            self.new_config_saved = False
            check_buttons()
            ui.notify("Configuration hot-reloaded into runtime", type="positive")

        def syntax_check() -> bool:
            try:
                config = Config()
                config.load_from_string(editor.value)
                ui.notify("Syntax is valid", type="positive")
                check_buttons()
                return True
            except Exception as e:
                ui.notify(f"Syntax error: {e}", type="negative")
                button_save.disable()
                return False

        with ui.row().classes("w-full justify-between items-center mb-3"):
            ui.label("Configuration Editor").classes("text-h4")
            ui.label("config.ini").classes(
                "font-mono text-xs text-cyan-400 bg-cyan-500/10 "
                "border border-cyan-500/30 px-3 py-1 rounded-full"
            )

        with ui.row().classes(
            "w-full items-center justify-between gap-3 mb-3 p-3 "
            "rounded-xl bg-slate-900/60 border border-white/10"
        ):
            with ui.row().classes("items-center gap-2"):
                ui.button("Reload", icon="refresh", on_click=load_config).props(
                    "outline color=grey-4"
                ).tooltip("Reload from disk")
                ui.button("Validate", icon="verified", on_click=syntax_check).props(
                    "outline color=cyan"
                ).tooltip("Validate INI syntax")
                button_save = (
                    ui.button("Save", icon="save", on_click=save_config)
                    .props("unelevated color=primary")
                    .tooltip("Save changes to disk")
                )
                button_use_config = (
                    ui.button(
                        "Apply Runtime",
                        icon="sym_s_reopen_window",
                        on_click=use_config,
                    )
                    .props("outline color=emerald")
                    .tooltip("Hot-apply saved config into memory")
                )

            ui.button("Inspect JSON", icon="preview", on_click=show_config).props(
                "flat color=grey-4"
            ).tooltip("Inspect parsed configuration schema")

        with ui.element("div").classes(
            "w-full rounded-xl bg-slate-950 p-3 border border-white/10"
        ):
            editor = (
                ui.textarea(
                    value=self.callbacks.load_config_file(), on_change=check_buttons
                )
                .classes("w-full h-full font-mono text-sm")
                .props("autoResize rows=28 borderless")
            )

        check_buttons()
