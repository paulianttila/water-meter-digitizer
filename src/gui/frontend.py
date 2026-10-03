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
from gui.pages import (
    AboutPage,
    ApiConsolePage,
    BasePage,
    ConfigPage,
    HelpPage,
    MeterPage,
    PreviousValuesPage,
    ServicesPage,
    SetupPage,
)
from gui.theme import (
    NAV_PILLAR_PANEL,
    NAV_PILLAR_PANEL_FLUSH,
    NAV_PILLAR_PANEL_SCROLL,
    NAV_PILLAR_PANEL_SCROLL_FLUSH,
    NAV_SUBTAB_PANELS,
    TABS_BAR_HORIZONTAL,
    TABS_BAR_VERTICAL,
    TABS_PROPS_HORIZONTAL,
    TABS_PROPS_VERTICAL,
)
from version import __version__ as VERSION

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
    async def show(tab: str | None = None) -> None:
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

        pages: list[BasePage] = [
            meter_page,
            services_page,
            setup_page,
            config_page,
            previous_values_page,
            api_console_page,
            help_page,
            about_page,
        ]

        def _cleanup_client() -> None:
            for page in pages:
                with contextlib.suppress(Exception):
                    page.dispose()

        with contextlib.suppress(Exception):
            if hasattr(ui.context, "client") and ui.context.client is not None:
                ui.context.client.on_disconnect(_cleanup_client)

        tabs: ui.tabs | None = None
        settings_subtabs: ui.tabs | None = None
        system_subtabs: ui.tabs | None = None

        tab_dashboard: ui.tab | None = None
        tab_settings: ui.tab | None = None
        tab_studio: ui.tab | None = None
        tab_system: ui.tab | None = None

        subtab_wizard: ui.tab | None = None
        subtab_config: ui.tab | None = None
        subtab_baselines: ui.tab | None = None

        subtab_services: ui.tab | None = None
        subtab_help: ui.tab | None = None
        subtab_about: ui.tab | None = None

        loaded_views: set[str] = set()
        view_mounts: dict[str, tuple[Any, Any]] = {}

        async def load_view(view_id: str) -> None:
            view_key = view_id.lower().replace(" ", "_")
            alias_map = {
                "meter": "dashboard",
                "wizard": "setup",
                "editor": "config",
                "previous_values": "baselines",
                "api_console": "studio",
                "mock_camera": "studio",
                "docs": "help",
            }
            view_key = alias_map.get(view_key, view_key)

            if view_key in loaded_views:
                return
            loaded_views.add(view_key)

            if view_key in view_mounts:
                container, show_fn = view_mounts[view_key]
                with container:
                    res = show_fn()
                    if asyncio.iscoroutine(res):
                        await res

        async def navigate_to(target: str, subtab_name: str | None = None) -> None:
            if tabs is None:
                return
            target_key = target.lower().replace(" ", "_")

            if "meter" in target_key or "dash" in target_key:
                tabs.set_value(tab_dashboard)
                await load_view("dashboard")
            elif any(
                k in target_key
                for k in (
                    "setting",
                    "setup",
                    "config",
                    "baseline",
                    "wizard",
                    "editor",
                )
            ):
                tabs.set_value(tab_settings)
                sub_target = (subtab_name or target_key).lower()
                if "config" in sub_target or "editor" in sub_target:
                    if settings_subtabs and subtab_config:
                        settings_subtabs.set_value(subtab_config)
                    await load_view("config")
                elif "baseline" in sub_target or "previous" in sub_target:
                    if settings_subtabs and subtab_baselines:
                        settings_subtabs.set_value(subtab_baselines)
                    await load_view("baselines")
                else:
                    if settings_subtabs and subtab_wizard:
                        settings_subtabs.set_value(subtab_wizard)
                    await load_view("setup")
            elif any(k in target_key for k in ("studio", "api", "mock", "rest")):
                tabs.set_value(tab_studio)
                await load_view("studio")
            elif any(
                k in target_key
                for k in (
                    "system",
                    "service",
                    "help",
                    "about",
                    "doc",
                    "info",
                )
            ):
                tabs.set_value(tab_system)
                sub_target = (subtab_name or target_key).lower()
                if "help" in sub_target or "doc" in sub_target:
                    if system_subtabs and subtab_help:
                        system_subtabs.set_value(subtab_help)
                    await load_view("help")
                elif "about" in sub_target or "info" in sub_target:
                    if system_subtabs and subtab_about:
                        system_subtabs.set_value(subtab_about)
                    await load_view("about")
                else:
                    if system_subtabs and subtab_services:
                        system_subtabs.set_value(subtab_services)
                    await load_view("services")

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
                    .on(
                        "click",
                        lambda: asyncio.create_task(navigate_to("services")),
                    )
                ):
                    ui.element("span").classes("status-pulse")
                    ui.label("Online").props('id="gui-status-text"').classes(
                        "text-xs font-semibold"
                    )

                with (
                    ui.element("div")
                    .classes(
                        "px-2.5 py-1 rounded-full bg-white/5 border border-white/10 "
                        "text-gray-400 text-xs font-semibold hover:border-cyan-500/40 "
                        "hover:text-cyan-300 transition-all cursor-pointer"
                    )
                    .tooltip("Click to view About & System info")
                    .on("click", lambda: asyncio.create_task(navigate_to("about")))
                ):
                    ui.label(f"v{VERSION}")

        client_config_version = _callbacks.get_config_version()

        with ui.splitter(value=8, limits=(6, 12)).classes(
            "w-full flex-1 min-h-0 sidebar-splitter"
        ) as splitter:
            with (
                splitter.before,
                ui.tabs().props(TABS_PROPS_VERTICAL).classes(TABS_BAR_VERTICAL) as tabs,
            ):
                tab_dashboard = (
                    ui.tab("dashboard", label="Dashboard", icon="speed")
                    .props('aria-label="Dashboard"')
                    .tooltip("Dashboard & Live Readouts")
                )
                tab_settings = (
                    ui.tab("settings", label="Settings", icon="tune")
                    .props('aria-label="Settings"')
                    .tooltip("Calibration & Settings")
                )
                tab_studio = (
                    ui.tab("studio", label="Studio", icon="science")
                    .props('aria-label="Studio"')
                    .tooltip("Studio & Simulation")
                )
                tab_system = (
                    ui.tab("system", label="System", icon="dns")
                    .props('aria-label="System"')
                    .tooltip("System Diagnostics & Services")
                )

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

                ui.timer(0.5, check_config_reload)

                with ui.tab_panels(tabs, value=tab_dashboard).classes(
                    "w-full flex-1 p-0 overflow-hidden min-h-0"
                ):
                    # 1. Dashboard Pillar
                    with ui.tab_panel(tab_dashboard).classes(
                        NAV_PILLAR_PANEL_SCROLL_FLUSH
                    ):
                        panel_dashboard = ui.element("div").classes(
                            NAV_PILLAR_PANEL_SCROLL
                        )

                    # 2. Calibration & Settings Pillar
                    with ui.tab_panel(tab_settings).classes(NAV_PILLAR_PANEL):
                        with (
                            ui.tabs()
                            .props(TABS_PROPS_HORIZONTAL)
                            .classes(TABS_BAR_HORIZONTAL) as settings_subtabs
                        ):
                            subtab_wizard = (
                                ui.tab(
                                    "setup",
                                    label="Setup Wizard",
                                    icon="auto_fix_high",
                                )
                                .props('aria-label="Setup"')
                                .tooltip("10-Step Visual Calibration Wizard")
                            )
                            subtab_config = (
                                ui.tab(
                                    "config",
                                    label="Config Editor",
                                    icon="tune",
                                )
                                .props('aria-label="Config"')
                                .tooltip("Visual Form & Raw INI Editor")
                            )
                            subtab_baselines = (
                                ui.tab(
                                    "baselines",
                                    label="Baselines",
                                    icon="history_edu",
                                )
                                .props('aria-label="Baselines"')
                                .tooltip("Baseline & Previous Values Manager")
                            )

                        with ui.tab_panels(
                            settings_subtabs, value=subtab_wizard
                        ).classes(NAV_SUBTAB_PANELS):
                            with ui.tab_panel(subtab_wizard).classes(
                                NAV_PILLAR_PANEL_FLUSH
                            ):
                                panel_wizard = ui.element("div").classes(
                                    "w-full h-full p-0 overflow-hidden flex flex-col min-h-0"
                                )
                            with ui.tab_panel(subtab_config).classes(
                                NAV_PILLAR_PANEL_FLUSH
                            ):
                                panel_config = ui.element("div").classes(
                                    "w-full h-full p-0 overflow-hidden flex flex-col min-h-0"
                                )
                            with ui.tab_panel(subtab_baselines).classes(
                                NAV_PILLAR_PANEL_SCROLL_FLUSH
                            ):
                                panel_baselines = ui.element("div").classes(
                                    NAV_PILLAR_PANEL_SCROLL_FLUSH
                                )

                    # 3. Studio & Simulation Pillar
                    with ui.tab_panel(tab_studio).classes(NAV_PILLAR_PANEL_FLUSH):
                        panel_studio = ui.element("div").classes(
                            "w-full h-full p-0 overflow-hidden flex flex-col min-h-0"
                        )

                    # 4. System & Health Pillar
                    with ui.tab_panel(tab_system).classes(NAV_PILLAR_PANEL):
                        with (
                            ui.tabs()
                            .props(TABS_PROPS_HORIZONTAL)
                            .classes(TABS_BAR_HORIZONTAL) as system_subtabs
                        ):
                            subtab_services = (
                                ui.tab(
                                    "services",
                                    label="Services & Health",
                                    icon="hub",
                                )
                                .props('aria-label="Services"')
                                .tooltip("Services, Health & Diagnostics")
                            )
                            subtab_help = (
                                ui.tab(
                                    "help",
                                    label="Help & Documentation",
                                    icon="help_outline",
                                )
                                .props('aria-label="Help"')
                                .tooltip("Wiki Guides & Keyboard Shortcuts")
                            )
                            subtab_about = (
                                ui.tab(
                                    "about",
                                    label="About",
                                    icon="info",
                                )
                                .props('aria-label="About"')
                                .tooltip("Version, Build Info & License")
                            )

                        with ui.tab_panels(
                            system_subtabs, value=subtab_services
                        ).classes(NAV_SUBTAB_PANELS):
                            with ui.tab_panel(subtab_services).classes(
                                NAV_PILLAR_PANEL_SCROLL_FLUSH
                            ):
                                panel_services = ui.element("div").classes(
                                    NAV_PILLAR_PANEL_SCROLL_FLUSH
                                )
                            with ui.tab_panel(subtab_help).classes(
                                NAV_PILLAR_PANEL_FLUSH
                            ):
                                panel_help = ui.element("div").classes(
                                    "w-full h-full p-0 overflow-hidden flex flex-col min-h-0"
                                )
                            with ui.tab_panel(subtab_about).classes(
                                NAV_PILLAR_PANEL_SCROLL_FLUSH
                            ):
                                panel_about = ui.element("div").classes(
                                    NAV_PILLAR_PANEL_SCROLL_FLUSH
                                )

                view_mounts = {
                    "dashboard": (panel_dashboard, meter_page.show),
                    "setup": (panel_wizard, setup_page.show),
                    "config": (panel_config, config_page.show),
                    "baselines": (panel_baselines, previous_values_page.show),
                    "studio": (panel_studio, api_console_page.show),
                    "services": (panel_services, services_page.show),
                    "help": (panel_help, help_page.show),
                    "about": (panel_about, about_page.show),
                }

                async def on_tab_change(e: Any) -> None:
                    val = getattr(e, "value", e)
                    if isinstance(val, str):
                        await navigate_to(val)
                    elif val in (tab_dashboard, "dashboard"):
                        await load_view("dashboard")
                    elif val in (tab_settings, "settings"):
                        cur = getattr(settings_subtabs, "value", None)
                        if cur in (subtab_config, "config"):
                            await load_view("config")
                        elif cur in (subtab_baselines, "baselines"):
                            await load_view("baselines")
                        else:
                            await load_view("setup")
                    elif val in (tab_studio, "studio"):
                        await load_view("studio")
                    elif val in (tab_system, "system"):
                        cur = getattr(system_subtabs, "value", None)
                        if cur in (subtab_help, "help"):
                            await load_view("help")
                        elif cur in (subtab_about, "about"):
                            await load_view("about")
                        else:
                            await load_view("services")
                    elif val in (subtab_wizard, "setup"):
                        await load_view("setup")
                    elif val in (subtab_config, "config"):
                        await load_view("config")
                    elif val in (subtab_baselines, "baselines"):
                        await load_view("baselines")
                    elif val in (subtab_services, "services"):
                        await load_view("services")
                    elif val in (subtab_help, "help"):
                        await load_view("help")
                    elif val in (subtab_about, "about"):
                        await load_view("about")

                tabs.on_value_change(on_tab_change)
                settings_subtabs.on_value_change(on_tab_change)
                system_subtabs.on_value_change(on_tab_change)

                if tab:
                    await navigate_to(tab)
                else:
                    await load_view("dashboard")

                if _callbacks.is_config_missing():
                    from gui.dialogs import show_config_onboarding_dialog

                    class TabCoordinator:
                        def set_value(self, val: Any) -> None:
                            if tabs and tab_settings:
                                tabs.set_value(tab_settings)
                            if settings_subtabs and subtab_wizard:
                                settings_subtabs.set_value(subtab_wizard)

                    async def _onboarding_load_tab(tab_ref: Any) -> None:
                        await navigate_to("setup")

                    show_config_onboarding_dialog(
                        _callbacks,
                        tabs=TabCoordinator(),
                        setup_tab=subtab_wizard,
                        load_tab_fn=_onboarding_load_tab,
                    )

    # Nothing special is stored in the cookie, so it's fine to use random secret
    secret = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=20)  # nosec
    )

    ui.run_with(
        fastapi_app,
        mount_path="",
        storage_secret=secret,
    )
