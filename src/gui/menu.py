from nicegui import app, ui


class Menu:
    def __init__(self) -> None:
        pass

    def set_dark_mode(self):
        app.storage.user["dark_mode"] = True

    def set_light_mode(self):
        app.storage.user["dark_mode"] = False

    def show(self):
        ui.dark_mode().bind_value(app.storage.user, "dark_mode")
        with ui.button(icon="menu").classes("w-4/5"):
            with ui.menu():
                ui.menu_item("Dark mode", on_click=self.set_dark_mode)
                ui.menu_item("Light mode", on_click=self.set_light_mode)
