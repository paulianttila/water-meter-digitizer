"""Model Benchmark Dialog component for side-by-side CNN evaluation and selection."""

import logging
import time
from typing import Any, Callable
from nicegui import ui
from processor.digitizer import DigitizerProcessor

logger = logging.getLogger(__name__)


def open_model_benchmark_dialog(
    model_type: str,
    candidate_models: list[dict[str, str]],
    cut_images: list[Any],
    cnn_type_val: str,
    convert_value_fn: Callable[[Any], str],
    roi_thumbnails: dict[str, str],
    on_apply_callback: Callable[[str], None],
) -> None:
    """Render and open the interactive CNN Model Benchmark side-by-side dialog."""
    benchmark_results: list[dict[str, Any]] = []

    for item in candidate_models:
        modelfile = item["file"]
        model_display_name = item["name"]
        start = time.time()
        try:
            dp = DigitizerProcessor()
            if model_type == "digital":
                dp.init_digital_model(modelfile, cnn_type_val)
                dp.execute_digital_cnn(cut_images)
                dp.evaluate_cnn_results()
                results = dp.cnn_digital_results
            else:
                dp.init_analog_model(modelfile, cnn_type_val)
                dp.execute_analog_cnn(cut_images)
                dp.evaluate_cnn_results()
                results = dp.cnn_analog_results

            latency_ms = round((time.time() - start) * 1000, 1)
            avg_conf = (
                round(sum(r.confidence for r in results) / len(results), 1)
                if results
                else 0.0
            )
            composite_val = " ".join(str(convert_value_fn(r.value)) for r in results)
            benchmark_results.append(
                {
                    "file": modelfile,
                    "name": model_display_name,
                    "latency_ms": latency_ms,
                    "avg_confidence": avg_conf,
                    "composite": composite_val,
                    "results": results,
                    "error": None,
                }
            )
        except Exception as e:
            logger.exception(f"Error evaluating model {model_display_name}: {e}")
            benchmark_results.append(
                {
                    "file": modelfile,
                    "name": model_display_name,
                    "latency_ms": 0.0,
                    "avg_confidence": 0.0,
                    "composite": "ERR",
                    "results": [],
                    "error": str(e),
                }
            )

    # Sort descending by average confidence, then ascending by latency
    benchmark_results.sort(
        key=lambda x: (
            x["error"] is None,
            x["avg_confidence"],
            -x["latency_ms"],
        ),
        reverse=True,
    )

    top_model = (
        benchmark_results[0]
        if benchmark_results and benchmark_results[0]["error"] is None
        else None
    )
    fastest_model = (
        min(
            (b for b in benchmark_results if b["error"] is None),
            key=lambda x: x["latency_ms"],
            default=None,
        )
        if benchmark_results
        else None
    )

    with (
        ui.dialog() as dialog,
        ui.card().classes(
            "w-[94vw] max-w-5xl h-[88vh] bg-slate-950/95 "
            "border border-white/10 rounded-2xl shadow-2xl p-0 "
            "flex flex-col overflow-hidden backdrop-blur-xl"
        ),
    ):
        # Dialog Header
        with ui.row().classes(
            "w-full justify-between items-center px-6 py-4 border-b "
            "border-white/10 bg-slate-900/80 shrink-0"
        ):
            with ui.row().classes("items-center gap-3"):
                with ui.element("div").classes(
                    "w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 "
                    "to-cyan-500 flex items-center justify-center shadow-md "
                    "shadow-indigo-500/20"
                ):
                    ui.icon("analytics", color="white").classes("text-xl")
                with ui.column().classes("gap-0"):
                    ui.label("Neural Network Model Benchmark").classes(
                        "text-lg font-bold text-white leading-tight"
                    )
                    ui.label(
                        f"Evaluated {len(benchmark_results)} candidate "
                        f"{model_type} models across {len(cut_images)} ROIs"
                    ).classes("text-xs text-slate-400")
            ui.button(icon="close", on_click=dialog.close).props(
                "flat round dense text-color=slate-400"
            ).classes("hover:bg-white/10")

        # KPI Summary Bar
        with ui.row().classes(
            "w-full px-6 py-3 bg-slate-900/40 border-b border-white/5 "
            "gap-4 items-center justify-between text-xs shrink-0 flex-wrap"
        ):
            with ui.row().classes("items-center gap-2"):
                if top_model:
                    ui.label("★ Top Accuracy:").classes("text-slate-400 font-medium")
                    ui.label(
                        f"{top_model['name']} ({top_model['avg_confidence']}%)"
                    ).classes("font-bold text-emerald-400 font-mono")
            with ui.row().classes("items-center gap-2"):
                if fastest_model:
                    ui.label("⚡ Fastest:").classes("text-slate-400 font-medium")
                    ui.label(
                        f"{fastest_model['name']} ({fastest_model['latency_ms']}ms)"
                    ).classes("font-bold text-cyan-400 font-mono")
            with ui.row().classes("items-center gap-2"):
                ui.label("ROIs:").classes("text-slate-400 font-medium")
                ui.label(f"{len(cut_images)} regions").classes(
                    "font-semibold text-slate-300 font-mono"
                )

        # Reference ROI Crops Bar (Visual Ground Truth)
        with ui.row().classes(
            "w-full px-6 py-2.5 bg-slate-900/60 border-b border-white/5 "
            "gap-3 items-center shrink-0 flex-nowrap overflow-x-auto "
            "custom-scrollbar"
        ):
            with ui.row().classes("items-center gap-1.5 shrink-0 mr-2"):
                ui.icon("photo_camera", size="xs").classes("text-cyan-400")
                ui.label("ROI Reference:").classes(
                    "text-xs font-semibold text-slate-300 whitespace-nowrap"
                )
            for cut_img in cut_images:
                b64 = roi_thumbnails.get(cut_img.name, "")
                img_w_h = "w-9 h-14" if model_type == "digital" else "w-12 h-12"
                with ui.element("div").classes(
                    "p-1.5 rounded-lg bg-slate-950/80 border border-white/10 "
                    "flex flex-col items-center gap-1 shrink-0"
                ):
                    ui.label(cut_img.name).classes(
                        "text-[10px] text-slate-400 font-semibold "
                        "uppercase font-mono"
                    )
                    if b64:
                        ui.html(
                            f'<img src="data:image/jpeg;base64,{b64}" '
                            f'class="{img_w_h} rounded bg-slate-900 p-0.5 '
                            'border border-white/5 object-contain" />'
                        )

        # Benchmark Results Table Container
        with ui.element("div").classes(
            "w-full flex-1 min-h-0 overflow-y-auto p-4 flex flex-col gap-3 "
            "custom-scrollbar"
        ):
            with ui.element("table").classes("w-full text-left border-collapse"):
                with ui.element("thead").classes(
                    "text-xs font-semibold uppercase text-slate-400 "
                    "bg-slate-900/80 sticky top-0 z-10 border-b border-white/10"
                ):
                    with ui.element("tr"):
                        with ui.element("th").classes("p-3"):
                            ui.label("Model File")
                        with ui.element("th").classes("p-3 text-center"):
                            ui.label("Avg Conf")
                        with ui.element("th").classes("p-3 text-center"):
                            ui.label("Speed")
                        with ui.element("th").classes("p-3"):
                            ui.label("Per-ROI Predictions")
                        with ui.element("th").classes("p-3 text-right"):
                            ui.label("Action")

                with ui.element("tbody").classes("text-sm divide-y divide-white/5"):
                    for idx, item in enumerate(benchmark_results):
                        is_top = idx == 0 and item["error"] is None
                        row_bg = (
                            "bg-indigo-950/20 hover:bg-indigo-950/40"
                            if is_top
                            else "hover:bg-slate-900/60"
                        )
                        with ui.element("tr").classes(f"{row_bg} transition-colors"):
                            # Model Name
                            with ui.element("td").classes("p-3 align-middle"):
                                with ui.column().classes("gap-1"):
                                    with ui.row().classes(
                                        "items-center gap-1.5 flex-nowrap"
                                    ):
                                        if is_top:
                                            ui.icon("verified", size="xs").classes(
                                                "text-emerald-400"
                                            ).tooltip("Top Ranked Model")
                                        ui.label(item["name"]).classes(
                                            "font-medium text-slate-200 "
                                            "font-mono text-xs"
                                        ).tooltip(item["file"])

                                    # Architecture & Precision Badges
                                    with ui.row().classes(
                                        "items-center gap-1 flex-wrap"
                                    ):
                                        n_low = item["name"].lower()
                                        if "class100" in n_low:
                                            ui.label("Class 100").classes(
                                                "text-[9px] px-1.5 py-0.2 "
                                                "rounded bg-indigo-900/60 "
                                                "text-indigo-300 font-semibold "
                                                "border border-indigo-500/30"
                                            )
                                        elif "class11" in n_low:
                                            ui.label("Class 11").classes(
                                                "text-[9px] px-1.5 py-0.2 "
                                                "rounded bg-purple-900/60 "
                                                "text-purple-300 font-semibold "
                                                "border border-purple-500/30"
                                            )
                                        elif "cont" in n_low:
                                            ui.label("Continuous").classes(
                                                "text-[9px] px-1.5 py-0.2 "
                                                "rounded bg-cyan-900/60 "
                                                "text-cyan-300 font-semibold "
                                                "border border-cyan-500/30"
                                            )
                                        elif "legacy" in n_low or "version" in n_low:
                                            ui.label("Legacy").classes(
                                                "text-[9px] px-1.5 py-0.2 "
                                                "rounded bg-slate-800 "
                                                "text-slate-400 font-semibold "
                                                "border border-white/10"
                                            )

                                        if "_q" in n_low or "-q" in n_low:
                                            ui.label("⚡ Int8").classes(
                                                "text-[9px] px-1.5 py-0.2 "
                                                "rounded bg-emerald-950/80 "
                                                "text-emerald-300 font-semibold "
                                                "border border-emerald-500/30 "
                                                "font-mono"
                                            )
                                        else:
                                            ui.label("Float32").classes(
                                                "text-[9px] px-1.5 py-0.2 "
                                                "rounded bg-slate-900 "
                                                "text-slate-400 font-semibold "
                                                "border border-white/10 font-mono"
                                            )

                            # Avg Confidence
                            with ui.element("td").classes(
                                "p-3 align-middle text-center"
                            ):
                                if item["error"]:
                                    ui.label("—").classes("text-slate-500")
                                else:
                                    conf = item["avg_confidence"]
                                    if conf >= 90:
                                        badge_cls = (
                                            "bg-emerald-500/15 text-emerald-400 "
                                            "border-emerald-500/30"
                                        )
                                    elif conf >= 70:
                                        badge_cls = (
                                            "bg-amber-500/15 text-amber-400 "
                                            "border-amber-500/30"
                                        )
                                    else:
                                        badge_cls = (
                                            "bg-red-500/15 text-red-400 "
                                            "border-red-500/30"
                                        )
                                    ui.label(f"{conf:.1f}%").classes(
                                        "px-2 py-0.5 rounded-full "
                                        "text-xs font-semibold border "
                                        f"{badge_cls} font-mono"
                                    )

                            # Speed
                            with ui.element("td").classes(
                                "p-3 align-middle text-center text-xs "
                                "font-mono text-slate-400"
                            ):
                                ui.label(
                                    f"{item['latency_ms']}ms"
                                    if not item["error"]
                                    else "—"
                                )

                            # Per-ROI Predictions
                            with ui.element("td").classes("p-3 align-middle"):
                                if item["error"]:
                                    ui.label("Failed to infer").classes(
                                        "text-xs text-red-400 italic"
                                    )
                                else:
                                    with ui.row().classes(
                                        "items-center gap-2 flex-wrap"
                                    ):
                                        for res in item["results"]:
                                            val_str = convert_value_fn(res.value)
                                            c = res.confidence
                                            c_color = (
                                                "text-emerald-400"
                                                if c >= 90
                                                else (
                                                    "text-amber-400"
                                                    if c >= 70
                                                    else "text-red-400"
                                                )
                                            )
                                            b64 = roi_thumbnails.get(res.name, "")
                                            thumb_w_h = (
                                                "w-6 h-9"
                                                if model_type == "digital"
                                                else "w-8 h-8"
                                            )
                                            with (
                                                ui.element("div")
                                                .classes(
                                                    "p-1.5 rounded-lg "
                                                    "bg-slate-900/90 border "
                                                    "border-white/10 text-xs "
                                                    "flex items-center gap-2 "
                                                    "font-mono "
                                                    "hover:border-cyan-500/40 "
                                                    "transition-colors"
                                                )
                                                .tooltip(
                                                    f"{res.name}: "
                                                    f"value={val_str}, "
                                                    f"confidence={c:.1f}%"
                                                )
                                            ):
                                                if b64:
                                                    img_src = (
                                                        f"data:image/jpeg;base64,{b64}"
                                                    )
                                                    ui.html(
                                                        f'<img src="{img_src}" '
                                                        f'class="{thumb_w_h} '
                                                        "rounded bg-slate-950 "
                                                        "p-0.5 border "
                                                        "border-white/10 shrink-0 "
                                                        "object-contain "
                                                        'inline-block" />'
                                                    )
                                                with ui.column().classes(
                                                    "gap-0 leading-tight"
                                                ):
                                                    ui.label(f"{res.name}").classes(
                                                        "text-slate-400 "
                                                        "text-[10px] "
                                                        "uppercase font-semibold"
                                                    )
                                                    ui.label(f"{val_str}").classes(
                                                        "font-bold "
                                                        "text-slate-100 text-xs"
                                                    )
                                                    ui.label(f"{c:.0f}%").classes(
                                                        f"text-[10px] "
                                                        f"font-semibold {c_color}"
                                                    )

                            # Action Button
                            with ui.element("td").classes(
                                "p-3 align-middle text-right"
                            ):

                                def _make_apply(f=item["file"], n=item["name"]):
                                    def _apply():
                                        on_apply_callback(f)
                                        dialog.close()
                                        ui.notify(
                                            f"Applied model: {n}",
                                            type="positive",
                                        )

                                    return _apply

                                ui.button(
                                    "Apply",
                                    icon="check",
                                    on_click=_make_apply(item["file"], item["name"]),
                                ).props("unelevated dense").classes(
                                    "bg-indigo-600 hover:bg-indigo-500 "
                                    "text-white text-xs px-2.5 py-1 "
                                    "rounded-lg font-medium"
                                    if is_top
                                    else "bg-slate-800 hover:bg-slate-700 "
                                    "text-slate-300 border border-white/10 "
                                    "text-xs px-2.5 py-1 rounded-lg"
                                ).tooltip(
                                    f"Set {item['name']} as active model"
                                )

        # Dialog Footer
        with ui.row().classes(
            "w-full px-6 py-3 border-t border-white/10 bg-slate-900/60 "
            "justify-between items-center shrink-0 text-xs text-slate-400"
        ):
            ui.label(
                "Tip: Higher average confidence indicates better prediction certainty."
            )
            ui.button("Close", on_click=dialog.close).props("outline dense").classes(
                "text-slate-300 border-white/20 hover:bg-white/10"
            )

    dialog.open()
