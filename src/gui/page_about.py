from nicegui import ui

from main import VERSION


class AboutPage:
    def __init__(self) -> None:
        pass

    def show(self) -> None:
        with ui.grid(columns=1):
            ui.label("Meter-digitizer").classes("text-h4")
            ui.label(f"Version: {VERSION}").classes("text-h5")
            ui.image("web/static/watermeter.svg").classes("w-40")
