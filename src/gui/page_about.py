from nicegui import ui

from main import VERSION


class AboutPage:
    def __init__(self) -> None:
        pass

    def show(self) -> None:
        with ui.column().classes("w-full max-w-3xl gap-4"):
            ui.label("About Water Meter System").classes("text-h4")

            with ui.element("div").classes(
                "w-full p-6 rounded-2xl "
                "bg-gradient-to-tr from-blue-900/30 to-cyan-900/20 "
                "border border-blue-500/30 shadow-xl shadow-blue-500/10 "
                "flex items-center gap-6"
            ):
                with ui.element("div").classes(
                    "w-16 h-16 rounded-2xl "
                    "bg-gradient-to-tr from-blue-600 to-cyan-400 "
                    "flex items-center justify-center shadow-lg "
                    "shadow-blue-500/30 shrink-0"
                ):
                    ui.icon("water_drop", color="white").classes("text-3xl")

                with ui.column().classes("gap-1"):
                    ui.label("Water Meter System").classes("text-h5 font-['Outfit']")
                    ui.label(
                        "Automatic utility meter digitizer using neural network "
                        "inference, affine computer vision alignment, and rolling "
                        "odometer predecessor deduction."
                    ).classes("text-sm text-gray-300")

            with ui.row().classes("w-full gap-4 flex-wrap"):
                with ui.element("div").classes(
                    "p-4 rounded-xl bg-slate-900/60 border border-white/10 "
                    "flex-1 min-w-[200px]"
                ):
                    ui.label("APPLICATION VERSION").classes(
                        "text-xs font-semibold text-gray-400 tracking-wider mb-1"
                    )
                    ui.label(f"v{VERSION}").classes(
                        "font-['Outfit'] text-2xl font-bold text-white"
                    )

                with ui.element("div").classes(
                    "p-4 rounded-xl bg-slate-900/60 border border-white/10 "
                    "flex-1 min-w-[200px]"
                ):
                    ui.label("INFERENCE ENGINE").classes(
                        "text-xs font-semibold text-gray-400 tracking-wider mb-1"
                    )
                    ui.label("Google LiteRT").classes(
                        "font-['Outfit'] text-2xl font-bold text-cyan-400"
                    )

                with ui.element("div").classes(
                    "p-4 rounded-xl bg-slate-900/60 border border-white/10 "
                    "flex-1 min-w-[200px]"
                ):
                    ui.label("FRONTEND FRAMEWORK").classes(
                        "text-xs font-semibold text-gray-400 tracking-wider mb-1"
                    )
                    ui.label("NiceGUI 3.16.0").classes(
                        "font-['Outfit'] text-2xl font-bold text-emerald-400"
                    )
