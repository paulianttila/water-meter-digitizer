import logging
from fastapi import FastAPI
from nicegui import ui

from callbacks import Callbacks
from .page_config import ConfigPage
from .page_meter import MeterPage
from .menu import Menu
from .page_setup import SetupPage
from .page_about import AboutPage

logger = logging.getLogger(__name__)


_config = None
_callbacks = None


def init(fastapi_app: FastAPI, callbacks: Callbacks) -> None:
    global _config, _callbacks
    _callbacks = callbacks

    @ui.page("/")
    async def show():
        menu = Menu()
        meter_page = MeterPage(_callbacks)
        setup_page = SetupPage(_callbacks)
        config_page = ConfigPage(_callbacks)
        about_page = AboutPage()

        with ui.splitter(value=6, limits=(6, 6)).classes("w-full h-full") as splitter:
            with splitter.before:
                menu.show()
                with ui.tabs().props("vertical") as tabs:
                    main = ui.tab("Meter", icon="sym_s_speed")
                    setup = ui.tab("Setup", icon="settings")
                    config = ui.tab("Config", icon="sym_s_manufacturing")
                    about = ui.tab("About", icon="info")
            with splitter.after:
                with ui.tab_panels(tabs, value=main).classes("w-full h-full"):
                    with ui.tab_panel(main):
                        await meter_page.show()
                    with ui.tab_panel(setup):
                        await setup_page.show()
                    with ui.tab_panel(config):
                        config_page.show()
                    with ui.tab_panel(about):
                        about_page.show()

    ui.run_with(
        fastapi_app,
        mount_path="/gui",
        # There is nothing secret stored in the storage, so this should be safe
        storage_secret="x1Jusk9JbEjfmD4ykP1Y",  # nosec
    )
