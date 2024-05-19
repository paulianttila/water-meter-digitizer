import dataclasses
import json

from nicegui import ui

from callbacks import Callbacks


class MeterPage:
    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks

    async def show(self):

        async def do_fetch():
            self.spinner.visible = True
            value_container.clear()
            try:
                await fecth_data()
            except Exception as e:
                ui.notify(
                    f"Error occured: {e}",
                    position="bottom",
                    close_button="OK",
                    type="negative",
                    multi_line=True,
                    icon="error",
                    timeout=0,
                )
            self.spinner.visible = False

        async def fecth_data() -> None:
            result = self.callbacks.get_meter_data(saveimages=True)
            text_size = "text-xs"
            with value_container:
                with ui.grid(columns=2):
                    for meter in result.meters:
                        ui.label(f"{meter.name}:").classes(
                            f"{text_size} text-uppercase"
                        )
                        ui.label(f"{meter.value} {meter.unit}").classes(text_size)
                ui.separator()
                with ui.row().classes("w-full"):
                    base64img = self.callbacks.get_image_as_base64_str("final")
                    ui.image(f"data:image/jpeg;base64,{base64img}").classes(
                        "max-w-screen-sm"
                    )

                    count = len(result.digital_results) + len(result.analog_results)
                    with ui.grid(columns=count):
                        for image, value in result.digital_results.items():
                            with ui.card():
                                ui.label(f"{image}").classes(text_size)
                                base64img = self.callbacks.get_image_as_base64_str(
                                    image
                                )
                                ui.image(f"data:image/jpeg;base64,{base64img}")
                                with ui.card_section():
                                    ui.label(f"{value}").classes(text_size)
                        for image, value in result.analog_results.items():
                            with ui.card():
                                ui.label(f"{image}").classes(text_size)
                                base64img = self.callbacks.get_image_as_base64_str(
                                    image
                                )
                                ui.image(f"data:image/jpeg;base64,{base64img}")
                                with ui.card_section():
                                    ui.label(f"{value}").classes(text_size)

            raw_container.clear()
            with raw_container:
                result.pictures = None
                ui.code(
                    json.dumps(dataclasses.asdict(result), indent=4), language="json"
                )

        ui.label("Meter values").classes("text-h4")
        with ui.row().classes("w-full"):
            ui.button("", icon="refresh", on_click=do_fetch).tooltip("Refresh")
            self.spinner = ui.spinner("dots", size="lg", color="blue").props("center")
            self.spinner.visible = False
        with ui.tabs().classes("w-full").props("align left") as tabs:
            values = ui.tab("Values")
            raw = ui.tab("Raw data")
        with ui.tab_panels(tabs, value=values).classes("w-full h-full"):
            with ui.tab_panel(values):
                value_container = ui.row()
            with ui.tab_panel(raw):
                raw_container = ui.row()
        await do_fetch()
