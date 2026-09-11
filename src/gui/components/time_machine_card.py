"""Time Machine Historical Frame Scrubber & Before/After Anomaly Inspector for NiceGUI."""

import contextlib
import logging
from datetime import datetime
from typing import Any

from nicegui import ui

from callbacks import Callbacks

logger = logging.getLogger(__name__)


class TimeMachineCard:
    """Interactive historical frame scrubber, anomaly inspector, and visual diff viewer."""

    def __init__(self, callbacks: Callbacks) -> None:
        self.callbacks = callbacks
        self.timeline_records: list[dict[str, Any]] = []
        self.selected_index: int = 0
        self.anomalies_only: bool = False
        self.frames_only: bool = True
        self.view_mode: str = (
            "side_by_side"  # side_by_side, diff_heatmap, blink, digit_strip
        )
        self.is_playing: bool = False
        self.blink_state: bool = False
        self.playback_interval: float = 3.0
        self._seconds_left: float = 3.0
        self._timer: Any = None
        self._slider: Any = None
        self._programmatic_index: int = -1

    def _cancel_timer(self) -> None:
        """Safely cancel any active playback timer."""
        if self._timer is not None:
            with contextlib.suppress(Exception):
                self._timer.cancel()
            self._timer = None

    def render(self, container: ui.column) -> None:
        """Render the Time Machine interface."""

        def refresh_timeline() -> None:
            logger.info(
                "TimeMachine: refreshing timeline (anomalies_only=%s, frames_only=%s)",
                self.anomalies_only,
                self.frames_only,
            )
            records = self.callbacks.get_timeline(
                limit=100,
                offset=0,
                anomalies_only=self.anomalies_only,
                frames_only=self.frames_only,
            )
            if not records and self.frames_only:
                logger.info(
                    "TimeMachine: no frames found with frames_only=True, falling back to all records"
                )
                records = self.callbacks.get_timeline(
                    limit=100,
                    offset=0,
                    anomalies_only=self.anomalies_only,
                    frames_only=False,
                )

            # Store in chronological order (index 0 = Oldest past, index -1 = Latest live)
            self.timeline_records = list(reversed(records))
            logger.info(
                "TimeMachine: timeline loaded %d records in chronological order",
                len(self.timeline_records),
            )
            if not self.timeline_records:
                self.selected_index = 0
            else:
                self.selected_index = len(self.timeline_records) - 1
            rebuild_ui()

        def rebuild_ui() -> None:
            self.is_playing = False
            self._cancel_timer()
            container.clear()
            storage = self.callbacks.get_storage()
            if storage is None:
                with container:
                    ui.label("History storage backend is disabled.").classes(
                        "text-gray-400 italic p-4"
                    )
                return

            summary = storage.get_summary()
            total_snaps = getattr(summary, "total_snapshots", 0)
            disk_bytes = getattr(summary, "snapshot_disk_bytes", 0)
            snap_mode = getattr(summary, "snapshot_mode", "smart_tiered")
            try:
                mb_str = f"{float(disk_bytes) / (1024 * 1024):.1f} MB"
            except Exception:
                mb_str = "0.0 MB"

            with container:
                # 1. Header Toolbar
                with ui.row().classes(
                    "w-full justify-between items-center gap-4 flex-wrap "
                    "bg-slate-900/80 p-4 rounded-xl border border-white/10 shadow-lg"
                ):
                    with ui.row().classes("items-center gap-3"):
                        ui.icon("history_toggle_off", size="32px").classes(
                            "text-cyan-400"
                        )
                        with ui.column().classes("gap-0"):
                            ui.label("Time Machine & Frame Inspector").classes(
                                "text-lg font-bold text-white tracking-wide"
                            )
                            ui.label(
                                f"Archived Snapshots: {total_snaps} | "
                                f"Storage: {mb_str} | "
                                f"Mode: {snap_mode}"
                            ).classes("text-xs text-cyan-300/80 font-mono")

                    with ui.row().classes("items-center gap-2 flex-wrap"):
                        # Frames only filter
                        def on_frames_toggle(e: Any) -> None:
                            self.frames_only = bool(e.value)
                            refresh_timeline()

                        ui.switch(
                            "Frames Only",
                            value=self.frames_only,
                            on_change=on_frames_toggle,
                        ).props("dense color=cyan").classes("text-sm text-gray-300")

                        # Anomalies filter toggle
                        def on_filter_toggle(e: Any) -> None:
                            self.anomalies_only = bool(e.value)
                            refresh_timeline()

                        ui.switch(
                            "Anomalies Only",
                            value=self.anomalies_only,
                            on_change=on_filter_toggle,
                        ).props("dense color=amber").classes("text-sm text-gray-300")

                        ui.button(
                            "Refresh",
                            icon="refresh",
                            on_click=refresh_timeline,
                        ).props("dense flat color=cyan")

                        def on_prune_click() -> None:
                            pruned = storage.prune_snapshots(max_disk_mb=500.0)
                            ui.notify(f"Pruned {pruned} older frames.", type="info")
                            refresh_timeline()

                        ui.button(
                            "Prune",
                            icon="cleaning_services",
                            on_click=on_prune_click,
                        ).props("dense flat color=amber").tooltip(
                            "Prune old frames to stay within disk cap"
                        )

                if not self.timeline_records:
                    with ui.card().classes(
                        "w-full p-8 text-center bg-slate-900/40 border border-dashed border-white/10 rounded-xl mt-4"
                    ):
                        ui.icon("photo_camera_back", size="48px").classes(
                            "text-gray-500 mx-auto mb-2"
                        )
                        ui.label("No snapshot frames recorded yet.").classes(
                            "text-gray-300 font-medium"
                        )
                        ui.label(
                            "Frames will be captured automatically on meter readouts, flow changes, or anomalies."
                        ).classes("text-xs text-gray-500 mt-1")
                    return

                # 2. Scrubber Card (Slider + Badges)
                scrubber_card = ui.card().classes(
                    "w-full p-4 bg-slate-900/60 border border-white/10 rounded-xl mt-3 shadow-md"
                )
                badge_row = ui.row().classes(
                    "w-full justify-between items-center gap-4 flex-wrap"
                )
                with badge_row:
                    metadata_container = ui.row().classes(
                        "items-center gap-2 flex-wrap"
                    )
                    controls_container = ui.row().classes(
                        "items-center gap-1.5 flex-wrap"
                    )

                slider_container = ui.row().classes("w-full mt-2")

                # 3. Mode Toolbar & Presentation Card
                display_container = ui.column().classes("w-full gap-2 mt-2")

                play_btn: Any = None
                countdown_badge: Any = None

                def update_play_button() -> None:
                    if play_btn is not None:
                        play_color = "amber" if self.is_playing else "cyan"
                        play_icon = "pause" if self.is_playing else "play_arrow"
                        play_btn.props(f"dense flat color={play_color}")
                        play_btn._props["icon"] = play_icon
                        play_btn.tooltip(
                            "Pause Scrubber"
                            if self.is_playing
                            else "Play Time-lapse Scrubber"
                        )
                        play_btn.update()

                def update_countdown_label() -> None:
                    if countdown_badge is not None:
                        if self.is_playing:
                            countdown_badge.set_text(
                                f"⏱️ Next: {max(0.0, self._seconds_left):.1f}s"
                            )
                            countdown_badge.props("color=amber")
                            countdown_badge.set_visibility(True)
                        else:
                            countdown_badge.set_text("⏱️ Paused")
                            countdown_badge.props("color=dark")
                            countdown_badge.set_visibility(False)

                def stop_playback() -> None:
                    self.is_playing = False
                    self._cancel_timer()
                    update_play_button()
                    update_countdown_label()

                def play_tick() -> None:
                    if not self.is_playing or not self.timeline_records:
                        stop_playback()
                        return
                    self._seconds_left -= 0.1
                    if self._seconds_left <= 0.05:
                        # Advance forward in time towards latest
                        if self.selected_index < len(self.timeline_records) - 1:
                            self.selected_index += 1
                        else:
                            self.selected_index = 0  # Loop back to oldest
                        self._seconds_left = self.playback_interval
                        self._programmatic_index = self.selected_index
                        if self._slider:
                            self._slider.value = self.selected_index
                        update_display()
                    else:
                        update_countdown_label()

                def start_playback() -> None:
                    if len(self.timeline_records) <= 1:
                        return
                    self.is_playing = True
                    if self.selected_index >= len(self.timeline_records) - 1:
                        self.selected_index = 0
                        self._programmatic_index = self.selected_index
                        if self._slider:
                            self._slider.value = self.selected_index
                        update_display()
                    self._seconds_left = self.playback_interval
                    self._cancel_timer()
                    self._timer = ui.timer(0.1, play_tick)
                    update_play_button()
                    update_countdown_label()

                def toggle_play() -> None:
                    logger.info(
                        "TimeMachine: toggle_play called (current is_playing=%s, interval=%.2fs)",
                        self.is_playing,
                        self.playback_interval,
                    )
                    if self.is_playing:
                        stop_playback()
                    else:
                        start_playback()
                    update_display()

                def step_prev() -> None:
                    if self.is_playing:
                        stop_playback()
                    if self.selected_index > 0:
                        self.selected_index -= 1
                        self._programmatic_index = self.selected_index
                        if self._slider:
                            self._slider.value = self.selected_index
                        update_display()

                def step_next() -> None:
                    if self.is_playing:
                        stop_playback()
                    if self.selected_index < len(self.timeline_records) - 1:
                        self.selected_index += 1
                        self._programmatic_index = self.selected_index
                        if self._slider:
                            self._slider.value = self.selected_index
                        update_display()

                def jump_live() -> None:
                    if self.is_playing:
                        stop_playback()
                    self.selected_index = len(self.timeline_records) - 1
                    self._programmatic_index = self.selected_index
                    if self._slider:
                        self._slider.value = self.selected_index
                    update_display()

                def on_speed_change(e: Any) -> None:
                    self.playback_interval = float(e.value)
                    self._seconds_left = min(self._seconds_left, self.playback_interval)
                    logger.info(
                        "TimeMachine: playback speed changed to %.2fs",
                        self.playback_interval,
                    )
                    update_countdown_label()

                # Mount static controls once
                with controls_container:
                    ui.button(icon="skip_previous", on_click=step_prev).props(
                        "dense flat color=cyan"
                    ).tooltip("Older Frame (Step Back / Left)")

                    play_btn = (
                        ui.button(icon="play_arrow", on_click=toggle_play)
                        .props("dense flat color=cyan")
                        .tooltip("Play Time-lapse Scrubber")
                    )

                    countdown_badge = ui.badge("⏱️ 0.0s", color="amber").classes(
                        "font-mono text-xs px-2 py-1"
                    )
                    countdown_badge.set_visibility(False)

                    ui.button(icon="skip_next", on_click=step_next).props(
                        "dense flat color=cyan"
                    ).tooltip("Newer Frame (Step Forward / Right)")

                    ui.button(
                        "Live", icon="fiber_manual_record", on_click=jump_live
                    ).props("dense flat color=negative").tooltip(
                        "Jump to Latest Live Frame (Far Right)"
                    )

                    speed_options = {
                        10.0: "10s (Slowest)",
                        5.0: "5s (Slow)",
                        3.0: "3s (Relaxed)",
                        2.0: "2s (Medium)",
                        1.0: "1s (Normal)",
                        0.5: "0.5s (Fast)",
                    }

                    ui.select(
                        speed_options,
                        value=self.playback_interval,
                        on_change=on_speed_change,
                    ).props("dense options-dense outlined dark").classes(
                        "text-xs w-36 bg-slate-900/90 text-cyan-300"
                    ).tooltip(
                        "Playback Speed (seconds per frame)"
                    )

                def update_display() -> None:
                    if not self.timeline_records:
                        return
                    cur_rec = self.timeline_records[self.selected_index]
                    cur_id = cur_rec.get("id", 1)

                    logger.info(
                        "TimeMachine: updating display for index=%d (reading_id=%s, mode=%s, is_playing=%s)",
                        self.selected_index,
                        cur_id,
                        self.view_mode,
                        self.is_playing,
                    )

                    # Update Metadata Badges
                    metadata_container.clear()
                    with metadata_container:
                        ts_str = cur_rec.get("timestamp", "")
                        try:
                            dt = datetime.fromisoformat(ts_str)
                            ts_formatted = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                        except Exception:
                            ts_formatted = ts_str

                        ui.badge(
                            f"Frame #{cur_id} ({self.selected_index + 1}/{len(self.timeline_records)})",
                            color="cyan",
                        ).classes("font-mono font-bold")
                        ui.label(ts_formatted).classes(
                            "text-sm font-mono text-gray-300"
                        )

                        if cur_rec.get("flow_detected"):
                            ui.badge("💧 Flow Active", color="blue").classes("text-xs")
                        if cur_rec.get("error"):
                            ui.badge(
                                f"⚠️ {cur_rec.get('error')}", color="negative"
                            ).classes("text-xs")
                        elif cur_rec.get("frame_type") == "roi_strip":
                            ui.badge("ROI Strip", color="indigo").classes("text-xs")
                        elif cur_rec.get("has_frame"):
                            ui.badge("Full Frame", color="teal").classes("text-xs")
                        else:
                            ui.badge("No Snapshot", color="grey-8").classes("text-xs")

                    update_play_button()
                    update_countdown_label()

                    # Update Display Container
                    display_container.clear()
                    with display_container:
                        # Reading Values Summary
                        meters_dict = cur_rec.get("meters", {})
                        if meters_dict:
                            with ui.row().classes(
                                "w-full justify-between items-center gap-2 mt-1"
                            ):
                                ui.label("Extracted Readings & Meter Values").classes(
                                    "text-xs font-mono font-bold text-gray-400"
                                )
                                with ui.row().classes("items-center gap-2 flex-wrap"):
                                    for m_name, m_data in meters_dict.items():
                                        val = m_data.get("value")
                                        unit = m_data.get("unit", "")
                                        conf = m_data.get("confidence", 100.0)
                                        ui.badge(
                                            f"{m_name}: {val} {unit} ({conf:.1f}%)",
                                            color="dark",
                                        ).classes(
                                            "border border-white/10 font-mono text-xs text-cyan-200"
                                        )

                        compare_id = (
                            self.timeline_records[-1].get("id", cur_id)
                            if len(self.timeline_records) > 0
                            else cur_id
                        )

                        # Formatted timestamps for both frames
                        hist_ts_raw = cur_rec.get("timestamp", "")
                        try:
                            dt_hist = datetime.fromisoformat(hist_ts_raw)
                            hist_ts_str = dt_hist.strftime("%Y-%m-%d %H:%M:%S UTC")
                        except Exception:
                            hist_ts_str = hist_ts_raw

                        live_rec = (
                            self.timeline_records[-1]
                            if self.timeline_records
                            else cur_rec
                        )
                        live_ts_raw = live_rec.get("timestamp", "")
                        try:
                            dt_live = datetime.fromisoformat(live_ts_raw)
                            live_ts_str = dt_live.strftime("%Y-%m-%d %H:%M:%S UTC")
                        except Exception:
                            live_ts_str = live_ts_raw

                        # Fetch base64 data URIs
                        frame_data_uri = self.callbacks.get_frame_data_uri(cur_id)
                        compare_data_uri = self.callbacks.get_frame_data_uri(compare_id)

                        logger.info(
                            "TimeMachine: frame_data_uri result for reading_id=%s: %s (compare_id=%s: %s)",
                            cur_id,
                            (
                                f"available ({len(frame_data_uri)} chars)"
                                if frame_data_uri
                                else "None"
                            ),
                            compare_id,
                            (
                                f"available ({len(compare_data_uri)} chars)"
                                if compare_data_uri
                                else "None"
                            ),
                        )

                        # 1. Side-by-Side Comparison Card
                        with ui.card().classes(
                            "w-full p-4 bg-slate-950/90 border border-white/10 rounded-xl mt-2 flex flex-col items-center justify-center min-h-[360px]"
                        ):
                            if not frame_data_uri:
                                with ui.column().classes(
                                    "items-center p-6 text-center gap-2"
                                ):
                                    ui.icon("image_not_supported", size="48px").classes(
                                        "text-gray-500"
                                    )
                                    ui.label(
                                        f"No snapshot image stored for Reading #{cur_id}"
                                    ).classes("text-gray-300 font-medium")
                                    ui.label(
                                        "This reading was recorded during numeric-only logging (smart tiering / no flow detected)."
                                    ).classes("text-xs text-gray-400 max-w-md")
                                    if not self.frames_only:
                                        ui.button(
                                            "Filter Snapshots Only",
                                            icon="filter_alt",
                                            on_click=lambda: on_frames_toggle(
                                                type("Obj", (), {"value": True})()
                                            ),
                                        ).props("dense unelevated color=cyan").classes(
                                            "text-xs mt-2"
                                        )
                            else:
                                with ui.row().classes(
                                    "w-full justify-around items-stretch gap-4 flex-wrap"
                                ):
                                    # Historical Frame Column
                                    with ui.column().classes(
                                        "flex-1 min-w-[280px] items-center justify-between gap-1.5"
                                    ):
                                        with ui.column().classes(
                                            "w-full items-center gap-1.5"
                                        ):
                                            ui.label(
                                                f"Historical Frame (#{cur_id})"
                                            ).classes(
                                                "text-xs font-mono font-bold text-cyan-300"
                                            )
                                            with ui.element("div").classes(
                                                "w-full h-[360px] rounded-xl bg-black/40 p-2 border border-cyan-500/30 shadow-lg flex items-center justify-center overflow-hidden"
                                            ):
                                                ui.image(frame_data_uri).props(
                                                    "fit=contain no-spinner"
                                                ).classes(
                                                    "max-w-full max-h-full rounded-lg"
                                                )

                                        with ui.row().classes(
                                            "items-center gap-1 text-gray-300 text-xs font-mono mt-1"
                                        ):
                                            ui.icon("schedule", size="15px").classes(
                                                "text-cyan-400"
                                            )
                                            ui.label(hist_ts_str).classes(
                                                "font-semibold text-cyan-200"
                                            )

                                    # Latest Live Frame Column
                                    with ui.column().classes(
                                        "flex-1 min-w-[280px] items-center justify-between gap-1.5"
                                    ):
                                        with ui.column().classes(
                                            "w-full items-center gap-1.5"
                                        ):
                                            ui.label(
                                                f"Latest Live Frame (#{compare_id})"
                                            ).classes(
                                                "text-xs font-mono font-bold text-green-300"
                                            )
                                            comp_src = (
                                                compare_data_uri or frame_data_uri
                                            )
                                            with ui.element("div").classes(
                                                "w-full h-[360px] rounded-xl bg-black/40 p-2 border border-green-500/30 shadow-lg flex items-center justify-center overflow-hidden"
                                            ):
                                                ui.image(comp_src).props(
                                                    "fit=contain no-spinner"
                                                ).classes(
                                                    "max-w-full max-h-full rounded-lg"
                                                )

                                        with ui.row().classes(
                                            "items-center gap-1 text-gray-300 text-xs font-mono mt-1"
                                        ):
                                            ui.icon("schedule", size="15px").classes(
                                                "text-green-400"
                                            )
                                            ui.label(live_ts_str).classes(
                                                "font-semibold text-green-200"
                                            )

                        # 2. Combined Digit & Analog ROI Crops Breakdown Card
                        dig_res = cur_rec.get("digital_results", {})
                        ana_res = cur_rec.get("analog_results", {})
                        conf_scores = cur_rec.get("confidence_scores", {})

                        if dig_res or ana_res:
                            with ui.card().classes(
                                "w-full p-4 bg-slate-900/60 border border-white/10 rounded-xl mt-2 flex flex-col items-center"
                            ):
                                ui.label(
                                    f"Historical Frame #{cur_id} ROI Detections & Confidence Breakdown"
                                ).classes(
                                    "text-xs font-mono font-bold text-cyan-300 mb-3"
                                )
                                with ui.row().classes(
                                    "gap-4 flex-wrap justify-center items-stretch w-full"
                                ):
                                    if dig_res:
                                        with ui.card().classes(
                                            "p-3 bg-slate-900/90 border border-white/10 rounded-lg flex-1 min-w-[260px]"
                                        ):
                                            with ui.row().classes(
                                                "w-full justify-between items-center mb-2 flex-wrap gap-1"
                                            ):
                                                with ui.row().classes(
                                                    "items-center gap-1.5"
                                                ):
                                                    ui.label("Digital Drums").classes(
                                                        "text-xs font-bold text-gray-300"
                                                    )
                                                    ui.badge(
                                                        f"Historical Frame #{cur_id}",
                                                        color="cyan",
                                                    ).classes("text-[10px] font-mono")
                                                ui.label(hist_ts_str).classes(
                                                    "text-[10px] font-mono text-cyan-300/80"
                                                )

                                            with ui.row().classes("gap-2 flex-wrap"):
                                                for k, v in dig_res.items():
                                                    c_val = conf_scores.get(
                                                        f"digital_{k}", 98.5
                                                    )
                                                    with ui.column().classes(
                                                        "items-center p-1.5 bg-black/40 rounded border border-white/5 min-w-[42px]"
                                                    ):
                                                        ui.label(str(v)).classes(
                                                            "text-lg font-bold font-mono text-cyan-400"
                                                        )
                                                        ui.label(f"{k}").classes(
                                                            "text-[10px] text-gray-400"
                                                        )
                                                        ui.label(
                                                            f"{c_val:.0f}%"
                                                        ).classes(
                                                            "text-[9px] text-green-400"
                                                        )

                                    if ana_res:
                                        with ui.card().classes(
                                            "p-3 bg-slate-900/90 border border-white/10 rounded-lg flex-1 min-w-[260px]"
                                        ):
                                            with ui.row().classes(
                                                "w-full justify-between items-center mb-2 flex-wrap gap-1"
                                            ):
                                                with ui.row().classes(
                                                    "items-center gap-1.5"
                                                ):
                                                    ui.label("Analog Dials").classes(
                                                        "text-xs font-bold text-gray-300"
                                                    )
                                                    ui.badge(
                                                        f"Historical Frame #{cur_id}",
                                                        color="amber",
                                                    ).classes("text-[10px] font-mono")
                                                ui.label(hist_ts_str).classes(
                                                    "text-[10px] font-mono text-amber-300/80"
                                                )

                                            with ui.row().classes("gap-2 flex-wrap"):
                                                for k, v in ana_res.items():
                                                    with ui.column().classes(
                                                        "items-center p-1.5 bg-black/40 rounded border border-white/5 min-w-[42px]"
                                                    ):
                                                        ui.label(str(v)).classes(
                                                            "text-lg font-bold font-mono text-amber-400"
                                                        )
                                                        ui.label(f"{k}").classes(
                                                            "text-[10px] text-gray-400"
                                                        )

                # Build Scrubber Card contents
                with scrubber_card:
                    scrubber_card.add_slot("default")

                    # Slider
                    def on_slider_change(e: Any) -> None:
                        val = int(e.value)
                        if (
                            val == self._programmatic_index
                            or val == self.selected_index
                        ):
                            return
                        logger.info("TimeMachine: manual slider drag value=%d", val)
                        if 0 <= val < len(self.timeline_records):
                            self.selected_index = val
                            self._programmatic_index = val
                            if self.is_playing:
                                stop_playback()
                            update_display()

                    with slider_container, ui.column().classes("w-full gap-1"):
                        oldest_ts = ""
                        latest_ts = ""
                        if self.timeline_records:
                            try:
                                dt0 = datetime.fromisoformat(
                                    self.timeline_records[0].get("timestamp", "")
                                )
                                oldest_ts = dt0.strftime("%Y-%m-%d %H:%M:%S")
                            except Exception:
                                oldest_ts = self.timeline_records[0].get(
                                    "timestamp", ""
                                )

                            try:
                                dt_last = datetime.fromisoformat(
                                    self.timeline_records[-1].get("timestamp", "")
                                )
                                latest_ts = dt_last.strftime("%Y-%m-%d %H:%M:%S")
                            except Exception:
                                latest_ts = self.timeline_records[-1].get(
                                    "timestamp", ""
                                )

                        with ui.row().classes(
                            "w-full justify-between items-center text-xs font-mono px-1"
                        ):
                            with ui.row().classes("items-center gap-1.5 text-gray-400"):
                                ui.icon("fast_rewind", size="16px").classes(
                                    "text-cyan-400"
                                )
                                ui.label(
                                    f"◀ Oldest (Past): {oldest_ts}"
                                    if oldest_ts
                                    else "◀ Oldest (Past)"
                                ).classes("font-semibold text-cyan-300")

                            with ui.row().classes("items-center gap-1.5 text-gray-400"):
                                ui.label(
                                    f"Latest (Live): {latest_ts} ▶"
                                    if latest_ts
                                    else "Latest (Live) ▶"
                                ).classes("font-semibold text-emerald-400")
                                ui.icon("fiber_manual_record", size="14px").classes(
                                    "text-rose-500 animate-pulse"
                                )

                        self._slider = (
                            ui.slider(
                                min=0,
                                max=len(self.timeline_records) - 1,
                                step=1,
                                value=self.selected_index,
                                on_change=on_slider_change,
                            )
                            .props("color=cyan label")
                            .classes("w-full")
                        )

                # Initial render of badges & presentation
                update_display()

        # Initial load
        refresh_timeline()
