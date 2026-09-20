import asyncio
import contextlib
import logging
import random
import string
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from nicegui import ui

from callbacks import Callbacks
from main import VERSION

from .page_about import AboutPage
from .page_api_console import ApiConsolePage
from .page_config import ConfigPage
from .page_help import HelpPage
from .page_meter import MeterPage
from .page_previous_values import PreviousValuesPage
from .page_services import ServicesPage
from .page_setup import SetupPage

logger = logging.getLogger(__name__)

_callbacks: Callbacks

CSS_DIR = Path(__file__).parent.parent / "web" / "static" / "css"
JS_DIR = Path(__file__).parent.parent / "web" / "static" / "js"

FAVICON_HTML = (
    f'<link rel="icon" type="image/svg+xml" href="/static/favicon.svg?v={VERSION}">\n'
    f'<link rel="icon" type="image/x-icon" href="/static/favicon.ico?v={VERSION}">\n'
    f'<link rel="apple-touch-icon" href="/static/apple-touch-icon.png?v={VERSION}">\n'
    f'<link rel="mask-icon" href="/static/favicon.svg?v={VERSION}" color="#3b82f6">'
)

FONT_HTML = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link href="https://fonts.googleapis.com/css2?'
    "family=Inter:wght@400;500;600;700&"
    'family=Outfit:wght@600;700;800&display=swap" rel="stylesheet">'
)


def _build_head_html() -> str:
    """Build combined head HTML from static CSS/JS files."""
    parts = [FAVICON_HTML, FONT_HTML]
    if CSS_DIR.is_dir():
        for css_file in sorted(CSS_DIR.glob("*.css")):
            parts.append(f"<style>\n{css_file.read_text(encoding='utf-8')}\n</style>")
    if JS_DIR.is_dir():
        for js_file in sorted(JS_DIR.glob("*.js")):
            parts.append(f"<script>\n{js_file.read_text(encoding='utf-8')}\n</script>")
    return "\n".join(parts)


GLOBAL_CSS = _build_head_html()


def init(fastapi_app: FastAPI, callbacks: Callbacks) -> None:
    global _callbacks
    _callbacks = callbacks

    @ui.page(
        "/",
        title="Water Meter Digitizer",
        favicon=f"/static/favicon.svg?v={VERSION}",
    )
    async def show() -> None:
        ui.dark_mode(True)
        ui.add_head_html(GLOBAL_CSS)
        meter_page = MeterPage(callbacks=_callbacks)
        services_page = ServicesPage(callbacks=_callbacks)
        setup_page = SetupPage(callbacks=_callbacks)
        config_page = ConfigPage(callbacks=_callbacks)
        previous_values_page = PreviousValuesPage(callbacks=_callbacks)
        api_console_page = ApiConsolePage(callbacks=_callbacks)
        help_page = HelpPage(callbacks=_callbacks)
        about_page = AboutPage(callbacks=_callbacks)

        tabs: ui.tabs | None = None
        services: ui.tab | None = None

        def navigate_to_services() -> None:
            if tabs is not None and services is not None:
                tabs.set_value(services)

        # Top Navigation Bar
        with ui.row().classes(
            "w-full items-center justify-between px-4 py-2 border-b "
            "border-white/10 bg-slate-950/80 backdrop-blur-md shrink-0 h-14"
        ):
            with ui.row().classes("items-center gap-3"):
                with ui.element("div").classes(
                    "w-9 h-9 rounded-lg flex items-center justify-center "
                    "bg-gradient-to-tr from-blue-600 to-cyan-400 "
                    "shadow-md shadow-blue-500/20"
                ):
                    ui.icon("water_drop", color="white").classes("text-xl")
                with ui.column().classes("gap-0"):
                    ui.label("Water Meter Digitizer").classes(
                        "font-['Outfit'] font-bold text-lg text-white leading-tight"
                    )
                    ui.label("Interactive Web UI & Setup Wizard").classes(
                        "text-xs text-gray-400 leading-tight"
                    )

            with ui.row().classes("items-center gap-2"):
                with (
                    ui.element("div")
                    .classes("gui-badge-status")
                    .props('id="gui-status-badge"')
                    .tooltip("Click to view Services & Diagnostics")
                    .on("click", navigate_to_services)
                ):
                    ui.element("span").classes("status-pulse")
                    ui.label("Online").props('id="gui-status-text"').classes(
                        "text-xs font-semibold"
                    )

                with ui.element("div").classes(
                    "px-2.5 py-1 rounded-full bg-white/5 border border-white/10 "
                    "text-gray-400 text-xs font-semibold"
                ):
                    ui.label(f"v{VERSION}")

        client_config_version = _callbacks.get_config_version()

        with ui.splitter(value=7, limits=(6, 8)).classes(
            "w-full flex-1 min-h-0"
        ) as splitter:
            with (
                splitter.before,
                ui.tabs().props("vertical").classes("w-full") as tabs,
            ):
                main = ui.tab("Meter", icon="speed")
                services = ui.tab("Services", icon="hub")
                setup = ui.tab("Setup", icon="settings")
                config = ui.tab("Config", icon="build")
                baselines = ui.tab("Baselines", icon="tune")
                api_console = ui.tab("API Console", icon="terminal")
                help_tab = ui.tab("Help", icon="help_outline")
                about = ui.tab("About", icon="info")
            with (
                splitter.after,
                ui.column().classes(
                    "w-full h-full p-0 overflow-hidden flex flex-col relative"
                ),
            ):
                with (
                    ui.row()
                    .classes(
                        "w-full px-4 py-2.5 bg-amber-500/15 border-b border-amber-500/30 "
                        "backdrop-blur-md items-center justify-between text-amber-200 text-xs shrink-0 z-50 transition-all"
                    )
                    .props('id="reload-warning-banner"') as reload_banner
                ):
                    reload_banner.visible = False
                    with ui.row().classes("items-center gap-2 flex-1 min-w-0"):
                        ui.icon("warning", color="amber").classes("text-lg shrink-0")
                        ui.label(
                            "Configuration has been hot-reloaded into runtime. Refresh page to update interface views and definitions."
                        ).classes("font-medium text-amber-100 truncate")
                    with ui.row().classes("items-center gap-2 shrink-0"):
                        ui.button(
                            "Refresh Page",
                            icon="refresh",
                            on_click=lambda: ui.run_javascript(
                                "window.location.reload()"
                            ),
                        ).props(
                            "dense unelevated size=sm color=amber text-color=dark"
                        ).classes(
                            "font-bold"
                        )
                        ui.button(
                            icon="close",
                            on_click=lambda: reload_banner.set_visibility(False),
                        ).props(
                            "dense flat round size=sm text-color=amber-200 aria-label='Dismiss reload warning'"
                        ).tooltip(
                            "Dismiss warning"
                        )

                def check_config_reload() -> None:
                    with contextlib.suppress(Exception):
                        if _callbacks.get_config_version() > client_config_version:
                            reload_banner.visible = True

                ui.timer(2.0, check_config_reload)

                tab_defs = [
                    (
                        "meter",
                        main,
                        meter_page.show,
                        "w-full h-full p-0 overflow-y-auto",
                    ),
                    (
                        "services",
                        services,
                        services_page.show,
                        "w-full h-full p-0 overflow-y-auto",
                    ),
                    (
                        "setup",
                        setup,
                        setup_page.show,
                        "w-full h-full p-0 overflow-hidden flex flex-col min-h-0",
                    ),
                    (
                        "config",
                        config,
                        config_page.show,
                        "w-full h-full p-0 overflow-hidden flex flex-col min-h-0",
                    ),
                    (
                        "baselines",
                        baselines,
                        previous_values_page.show,
                        "w-full h-full p-0 overflow-y-auto",
                    ),
                    (
                        "api_console",
                        api_console,
                        api_console_page.show,
                        "w-full h-full p-0 overflow-y-auto flex flex-col",
                    ),
                    (
                        "help",
                        help_tab,
                        help_page.show,
                        "w-full h-full p-0 overflow-y-auto",
                    ),
                    (
                        "about",
                        about,
                        about_page.show,
                        "w-full h-full p-0 overflow-y-auto",
                    ),
                ]

                panels: dict[str, tuple[ui.tab_panel, Any]] = {}
                with ui.tab_panels(tabs, value=main).classes(
                    "w-full flex-1 p-4 overflow-hidden min-h-0"
                ):
                    for tab_id, tab_obj, show_fn, css_cls in tab_defs:
                        panel = ui.tab_panel(tab_obj).classes(css_cls)
                        panels[tab_id] = (panel, show_fn)

                loaded_tabs: set[str] = set()

                async def load_tab(tab_ref: Any) -> None:
                    target_id = None
                    if isinstance(tab_ref, str):
                        target_id = tab_ref.lower().replace(" ", "_")
                    else:
                        for tid, tobj, _, _ in tab_defs:
                            if tab_ref is tobj:
                                target_id = tid
                                break
                    if not target_id:
                        target_id = "meter"

                    if target_id in loaded_tabs:
                        return
                    loaded_tabs.add(target_id)

                    if target_id in panels:
                        panel, show_fn = panels[target_id]
                        with panel:
                            res = show_fn()
                            if asyncio.iscoroutine(res):
                                await res

                # Initial render: load default active tab (Meter)
                await load_tab(main)

                async def on_tab_change(e: Any) -> None:
                    val = getattr(e, "value", e)
                    await load_tab(val)

                tabs.on_value_change(on_tab_change)

    # Nothing special is stored in the cookie, so it's fine to use random secret
    secret = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=20)  # nosec
    )

    ui.run_with(
        fastapi_app,
        mount_path="",
        storage_secret=secret,
    )
