"""System Diagnostics and Telemetry Card for NiceGUI."""

import asyncio
from typing import Any

from nicegui import ui

from callbacks import Callbacks
from gui.theme import (
    BADGE_ERROR,
    BADGE_INFO,
    BADGE_SUCCESS,
    BADGE_WARNING,
    CARD_DEFAULT,
)


class DiagnosticsCard:
    """Component rendering system health, camera telemetry, LiteRT metrics, and memory."""

    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks
        self.container: ui.column | None = None
        self._data: dict[str, Any] = {}

    def render(self) -> None:
        """Render the diagnostics telemetry card."""
        with ui.column().classes("w-full gap-4") as self.container:
            self._render_content()

    def update_data(self, data: dict[str, Any]) -> None:
        """Update diagnostics data and refresh view."""
        self._data = data
        if self.container is not None:
            self.container.clear()
            with self.container:
                self._render_content()

    async def fetch_and_update(self) -> None:
        """Fetch fresh diagnostics from backend asynchronously and update."""
        try:
            data = await asyncio.to_thread(self.callbacks.get_health_data)
            self.update_data(data)
        except Exception as e:
            ui.notify(f"Failed to fetch diagnostics: {e}", type="negative")

    def _render_content(self) -> None:
        if not self._data:
            with ui.card().classes(CARD_DEFAULT):
                with ui.row().classes("w-full justify-between items-center"):
                    ui.label("System Diagnostics & Health").classes(
                        "font-['Outfit'] font-bold text-base text-gray-200"
                    )
                    ui.button(
                        "Fetch Diagnostics",
                        icon="refresh",
                        on_click=self.fetch_and_update,
                    ).props("flat dense color=cyan text-xs")
                ui.label("No diagnostics telemetry available yet.").classes(
                    "text-xs text-gray-400 mt-2"
                )
            return

        status = self._data.get("status", "unknown").lower()
        uptime_info = self._data.get("uptime", {})
        camera_info = self._data.get("camera", {})
        mem_info = self._data.get("memory", {})
        cache_info = self._data.get("cache", {})
        models_info = self._data.get("models", {})
        sys_info = self._data.get("system", {})

        status_badge_cls = (
            BADGE_SUCCESS
            if status == "healthy"
            else (BADGE_WARNING if status == "degraded" else BADGE_ERROR)
        )
        status_text = status.upper()

        with ui.card().classes(CARD_DEFAULT + " gap-4"):
            # Header Row
            with ui.row().classes("w-full justify-between items-center"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("health_and_safety", color="cyan").classes("text-xl")
                    ui.label("System Diagnostics & Health").classes(
                        "font-['Outfit'] font-bold text-base text-gray-100"
                    )
                    with ui.element("span").classes(status_badge_cls):
                        ui.label(status_text)

                with ui.row().classes("items-center gap-2"):
                    ui.label(f"Uptime: {uptime_info.get('uptime_human', '—')}").classes(
                        "text-xs font-mono text-gray-400"
                    )
                    ui.button(
                        icon="refresh",
                        on_click=self.fetch_and_update,
                    ).props(
                        "flat round dense color=cyan text-xs"
                    ).tooltip("Refresh Diagnostics")

            # 4 Grid Sub-Panels: Camera, Memory & System, Image Cache, LiteRT Pool
            with ui.grid(columns=4).classes(
                "w-full gap-3 grid-cols-1 md:grid-cols-2 lg:grid-cols-4"
            ):
                # 1. Camera Status
                with ui.element("div").classes(
                    "p-3 rounded-xl bg-slate-950/60 border border-white/5 flex flex-col justify-between"
                ):
                    with ui.row().classes("items-center justify-between mb-1"):
                        ui.label("Camera Feed").classes(
                            "text-xs font-semibold text-gray-400 uppercase tracking-wider"
                        )
                        cam_reachable = camera_info.get("reachable", False)
                        with ui.element("span").classes(
                            BADGE_SUCCESS if cam_reachable else BADGE_ERROR
                        ):
                            ui.label("ONLINE" if cam_reachable else "OFFLINE")

                    latency = camera_info.get("latency_ms")
                    with ui.row().classes("items-baseline gap-1 my-1"):
                        ui.label(
                            f"{latency:.1f} ms" if latency is not None else "—"
                        ).classes("font-['Outfit'] text-2xl font-bold text-cyan-300")
                        ui.label("latency").classes("text-xs text-gray-400")

                    url_str = camera_info.get("url", "")
                    if len(url_str) > 30:
                        url_str = url_str[:27] + "..."
                    ui.label(url_str or "No URL configured").classes(
                        "text-[11px] font-mono text-gray-400 truncate"
                    )

                # 2. Process & Memory
                with ui.element("div").classes(
                    "p-3 rounded-xl bg-slate-950/60 border border-white/5 flex flex-col justify-between"
                ):
                    with ui.row().classes("items-center justify-between mb-1"):
                        ui.label("Memory & Process").classes(
                            "text-xs font-semibold text-gray-400 uppercase tracking-wider"
                        )
                        with ui.element("span").classes(BADGE_INFO):
                            ui.label(f"v{sys_info.get('version', '1.0.0')}")

                    rss = mem_info.get("rss_mb", 0.0)
                    peak = mem_info.get("peak_rss_mb", 0.0)
                    with ui.row().classes("items-baseline gap-1 my-1"):
                        ui.label(f"{rss:.1f} MB").classes(
                            "font-['Outfit'] text-2xl font-bold text-white"
                        )
                        ui.label(f"(Peak: {peak:.1f} MB)").classes(
                            "text-xs text-gray-400"
                        )

                    ui.label(
                        f"Python {sys_info.get('python_version', '3.11')} • {sys_info.get('platform', 'Darwin')}"
                    ).classes("text-[11px] text-gray-400 truncate")

                # 3. Cache Metrics
                with ui.element("div").classes(
                    "p-3 rounded-xl bg-slate-950/60 border border-white/5 flex flex-col justify-between"
                ):
                    with ui.row().classes("items-center justify-between mb-1"):
                        ui.label("Image Cache").classes(
                            "text-xs font-semibold text-gray-400 uppercase tracking-wider"
                        )
                        hit_ratio = cache_info.get("hit_ratio_percent", 0.0)
                        with ui.element("span").classes(
                            BADGE_SUCCESS if hit_ratio > 0 else BADGE_INFO
                        ):
                            ui.label(f"{hit_ratio:.0f}% HIT")

                    cur_size = cache_info.get("current_size", 0)
                    max_sz = cache_info.get("max_size", 0)
                    with ui.row().classes("items-baseline gap-1 my-1"):
                        ui.label(f"{cur_size} / {max_sz}").classes(
                            "font-['Outfit'] text-2xl font-bold text-emerald-300"
                        )
                        ui.label("items").classes("text-xs text-gray-400")

                    hits = cache_info.get("hits", 0)
                    misses = cache_info.get("misses", 0)
                    ui.label(f"Hits: {hits} | Misses: {misses}").classes(
                        "text-[11px] text-gray-400 truncate"
                    )

                # 4. Neural Inference Pool
                with ui.element("div").classes(
                    "p-3 rounded-xl bg-slate-950/60 border border-white/5 flex flex-col justify-between"
                ):
                    with ui.row().classes("items-center justify-between mb-1"):
                        ui.label("LiteRT Models").classes(
                            "text-xs font-semibold text-gray-400 uppercase tracking-wider"
                        )
                        total_inf = models_info.get("total_inferences", 0)
                        with ui.element("span").classes(BADGE_INFO):
                            ui.label(f"{total_inf} INF")

                    avg_ms = models_info.get("avg_inference_ms")
                    with ui.row().classes("items-baseline gap-1 my-1"):
                        ui.label(
                            f"{avg_ms:.1f} ms" if avg_ms is not None else "—"
                        ).classes("font-['Outfit'] text-2xl font-bold text-purple-300")
                        ui.label("avg inference").classes("text-xs text-gray-400")

                    dig_m = models_info.get("digital", {})
                    ana_m = models_info.get("analog", {})
                    dig_status = (
                        "Ready"
                        if dig_m.get("exists")
                        else ("Disabled" if not dig_m.get("enabled") else "Missing")
                    )
                    ana_status = (
                        "Ready"
                        if ana_m.get("exists")
                        else ("Disabled" if not ana_m.get("enabled") else "Missing")
                    )
                    ui.label(f"Dig: {dig_status} | Ana: {ana_status}").classes(
                        "text-[11px] text-gray-400 truncate"
                    )

            # Granular LiteRT Neural Models Detail Panel
            dig_info = models_info.get("digital", {})
            ana_info = models_info.get("analog", {})
            if dig_info or ana_info:
                with (
                    ui.expansion(
                        "LiteRT Neural Model Architecture & Performance Details",
                        icon="psychology",
                    ).classes(
                        "w-full bg-slate-950/40 rounded-xl border border-white/5 text-gray-300 text-xs font-semibold"
                    ),
                    ui.grid(columns=2).classes(
                        "w-full gap-3 p-3 grid-cols-1 md:grid-cols-2"
                    ),
                ):
                    for label, _m_key, m_info in [
                        ("Digital Counters Model", "digital", dig_info),
                        ("Analog Dials Model", "analog", ana_info),
                    ]:
                        with ui.element("div").classes(
                            "p-3 rounded-lg bg-slate-900/60 border border-white/5 flex flex-col gap-1.5"
                        ):
                            with ui.row().classes(
                                "w-full justify-between items-center"
                            ):
                                ui.label(label).classes("font-bold text-slate-200")
                                enabled = m_info.get("enabled", False)
                                exists = m_info.get("exists", False)
                                with ui.element("span").classes(
                                    BADGE_SUCCESS
                                    if (enabled and exists)
                                    else (BADGE_INFO if not enabled else BADGE_ERROR)
                                ):
                                    ui.label(
                                        "LOADED"
                                        if (enabled and exists)
                                        else (
                                            "DISABLED"
                                            if not enabled
                                            else "FILE MISSING"
                                        )
                                    )

                            path_str = m_info.get("path", "")
                            if path_str:
                                ui.label(f"Path: {path_str}").classes(
                                    "text-[11px] font-mono text-gray-400 truncate"
                                )

                            size_bytes = m_info.get("size_bytes")
                            if size_bytes:
                                ui.label(f"Size: {size_bytes / 1024:.1f} KB").classes(
                                    "text-[11px] text-gray-400"
                                )

                            metrics = m_info.get("metrics") or {}
                            in_shape = metrics.get("input_shape")
                            out_shape = metrics.get("output_shape")
                            if in_shape or out_shape:
                                ui.label(
                                    f"Tensors: In {in_shape} ➔ Out {out_shape}"
                                ).classes("text-[11px] font-mono text-cyan-300")

                            min_lat = metrics.get("min_inference_ms")
                            avg_lat = metrics.get("avg_inference_ms")
                            max_lat = metrics.get("max_inference_ms")
                            inf_count = metrics.get("inferences", 0)
                            if inf_count > 0:
                                ui.label(
                                    f"Inferences: {inf_count} | Latency (min/avg/max): {min_lat} / {avg_lat} / {max_lat} ms"
                                ).classes("text-[11px] font-mono text-emerald-400")
