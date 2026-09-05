import logging
import random
import string
from fastapi import FastAPI
from nicegui import ui

from callbacks import Callbacks
from main import VERSION
from .page_config import ConfigPage
from .page_meter import MeterPage
from .page_setup import SetupPage
from .page_about import AboutPage
from .page_help import HelpPage

logger = logging.getLogger(__name__)

_callbacks: Callbacks

GLOBAL_CSS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    '<link href="https://fonts.googleapis.com/css2?'
    "family=Inter:wght@400;500;600;700&"
    'family=Outfit:wght@600;700;800&display=swap" rel="stylesheet">\n'
    """<style>
    :root {
        --bg-primary: #0a0f1d;
        --bg-card: rgba(17, 24, 39, 0.75);
        --bg-card-hover: rgba(30, 41, 59, 0.85);
        --border-color: rgba(255, 255, 255, 0.08);
        --border-hover: rgba(59, 130, 246, 0.5);
        --text-main: #f3f4f6;
        --text-muted: #9ca3af;
        --accent-blue: #3b82f6;
        --accent-cyan: #06b6d4;
        --accent-teal: #10b981;
        --gradient-hero: linear-gradient(135deg, #2563eb 0%, #06b6d4 100%);
        --shadow-glow: 0 0 25px rgba(37, 99, 235, 0.25);
        --shadow-card: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
        --radius-lg: 16px;
        --radius-md: 12px;
        --radius-sm: 8px;
    }

    body, body.body--dark {
        background-color: var(--bg-primary) !important;
        background-image:
            radial-gradient(at 0% 0%, rgba(37, 99, 235, 0.15) 0px, transparent 50%),
            radial-gradient(at 100% 0%, rgba(6, 182, 212, 0.12) 0px, transparent 50%),
            radial-gradient(
                at 50% 100%, rgba(139, 92, 246, 0.1) 0px, transparent 50%
            ) !important;
        background-attachment: fixed !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: var(--text-main) !important;
    }

    .q-card, .q-table__container {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        backdrop-filter: blur(12px) !important;
        border-radius: var(--radius-md) !important;
        box-shadow: var(--shadow-card) !important;
    }

    .q-tab-panels {
        background: transparent !important;
    }

    .q-splitter__panel {
        background: transparent !important;
    }

    .q-stepper {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        backdrop-filter: blur(12px) !important;
        border-radius: var(--radius-md) !important;
    }

    .q-tab--active {
        color: #38bdf8 !important;
    }

    .q-btn {
        border-radius: var(--radius-sm) !important;
        text-transform: none !important;
        font-weight: 600 !important;
    }

    .q-field__native, .q-field__input {
        color: #f3f4f6 !important;
    }

    .q-field--outlined .q-field__control {
        border-radius: var(--radius-sm) !important;
        border-color: rgba(255, 255, 255, 0.12) !important;
        background: rgba(15, 23, 42, 0.6) !important;
    }

    .text-h4, .text-h5 {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        color: #f8fafc !important;
    }

    .gui-badge-status {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #34d399;
        transition: all 0.3s ease;
    }

    .gui-badge-status.gui-status-offline {
        background: rgba(239, 68, 68, 0.15);
        border-color: rgba(239, 68, 68, 0.35);
        color: #f87171;
    }

    .status-pulse {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 8px #10b981;
        animation: pulse 2s infinite;
        transition: background-color 0.3s ease, box-shadow 0.3s ease;
    }

    .gui-status-offline .status-pulse {
        background-color: #ef4444;
        box-shadow: 0 0 8px #ef4444;
        animation: none;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(0.85); }
    }
</style>
<script>
    async function checkGuiHealth() {
        const badge = document.getElementById('gui-status-badge');
        const text = document.getElementById('gui-status-text');
        if (!badge || !text) return;

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3500);
            const response = await fetch('/healthcheck', { signal: controller.signal });
            clearTimeout(timeoutId);

            if (response.ok) {
                const body = await response.text();
                if (body.includes('Health - OK')) {
                    badge.className = 'gui-badge-status';
                    text.textContent = 'Online';
                    return;
                }
            }
            badge.className = 'gui-badge-status gui-status-offline';
            text.textContent = 'Degraded';
        } catch (err) {
            badge.className = 'gui-badge-status gui-status-offline';
            text.textContent = 'Offline';
        }
    }

    setInterval(checkGuiHealth, 5000);
    setTimeout(checkGuiHealth, 800);
</script>
"""
)


def init(fastapi_app: FastAPI, callbacks: Callbacks) -> None:
    global _callbacks
    _callbacks = callbacks

    @ui.page("/")
    async def show() -> None:
        ui.dark_mode(True)
        ui.add_head_html(GLOBAL_CSS)
        meter_page = MeterPage(callbacks=_callbacks)
        setup_page = SetupPage(callbacks=_callbacks)
        config_page = ConfigPage(callbacks=_callbacks)
        help_page = HelpPage()
        about_page = AboutPage()

        # Top Navigation Bar
        with ui.row().classes(
            "w-full items-center justify-between px-4 py-2 border-b "
            "border-white/10 bg-slate-950/80 backdrop-blur-md"
        ):
            with ui.row().classes("items-center gap-3"):
                with ui.element("div").classes(
                    "w-9 h-9 rounded-lg flex items-center justify-center "
                    "bg-gradient-to-tr from-blue-600 to-cyan-400 "
                    "shadow-md shadow-blue-500/20"
                ):
                    ui.icon("water_drop", color="white").classes("text-xl")
                with ui.column().classes("gap-0"):
                    ui.label("Water Meter System").classes(
                        "font-['Outfit'] font-bold text-lg text-white leading-tight"
                    )
                    ui.label("Interactive Web UI & Setup Wizard").classes(
                        "text-xs text-gray-400 leading-tight"
                    )

            with ui.row().classes("items-center gap-3"):
                with (
                    ui.element("div")
                    .classes("gui-badge-status")
                    .props('id="gui-status-badge"')
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

                ui.button("Landing Page", icon="home").props(
                    'flat dense color=cyan href="/"'
                ).classes("text-xs")

        with ui.splitter(value=7, limits=(6, 8)).classes(
            "w-full h-[calc(100vh-60px)]"
        ) as splitter:
            with splitter.before:
                with ui.tabs().props("vertical").classes("w-full") as tabs:
                    main = ui.tab("Meter", icon="sym_s_speed")
                    setup = ui.tab("Setup", icon="settings")
                    config = ui.tab("Config", icon="sym_s_manufacturing")
                    help_tab = ui.tab("Help", icon="help_outline")
                    about = ui.tab("About", icon="info")
            with splitter.after:
                with ui.tab_panels(tabs, value=main).classes(
                    "w-full h-full p-4 overflow-auto"
                ):
                    with ui.tab_panel(main):
                        await meter_page.show()
                    with ui.tab_panel(setup):
                        await setup_page.show()
                    with ui.tab_panel(config):
                        config_page.show()
                    with ui.tab_panel(help_tab):
                        help_page.show()
                    with ui.tab_panel(about):
                        about_page.show()

    # Nothing special is stored in the cookie, so it's fine to use random secret
    secret = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=20)  # nosec
    )

    ui.run_with(
        fastapi_app,
        mount_path="/gui",
        storage_secret=secret,
    )
