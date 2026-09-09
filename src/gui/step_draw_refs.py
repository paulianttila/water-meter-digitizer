from collections.abc import Callable

from nicegui import ui

from data_classes import RefImage

from .step_draw_rois_base import DrawRoisBaseStep

HELP_TEXT = (
    "- **Reference Points**: Mark **3 distinct visual landmarks** "
    "(e.g. text labels, screws, dial centers) for affine alignment.\n"
    "- **Drawing**: Click `+` then drag a box on the canvas.\n"
    "- **Visibility**: Toggle colored checkboxes to show/hide boxes."
)


class DrawRefsStep(DrawRoisBaseStep):
    def __init__(
        self,
        name: str,
        name_template: str,
        set_image_callback: Callable[[str], None],
        set_rois_to_svg_func: Callable[[str], None],
        show_temp_draw_in_svg_func: Callable[[str], None],
        spinner=None,
    ) -> None:
        super().__init__(
            name,
            name_template,
            set_image_callback=set_image_callback,
            draw_roi_func=self.draw_roi_func,
            set_rois_to_svg_func=set_rois_to_svg_func,
            show_temp_draw_in_svg_func=show_temp_draw_in_svg_func,
            spinner=spinner,
        )

    def load_from_config(self, ref_images: list[RefImage]) -> None:
        self.load_rois(ref_images)

    def draw_roi_func(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        color: str,
        text: str,
    ) -> str:
        style = f"stroke-width:3;stroke:{color};fill-opacity:0;stroke-opacity:0.9"
        style2 = f"font-size:10;fill:{color};font-weight:bold;"
        return (
            f'<text x="{x}" y="{y-7}" text-anchor="left" style="{style2}">{text}</text>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" style="{style}" />'
        )

    def _add_roi(self) -> None:
        for roi in self.rois:
            roi.enabled = False
        super()._add_roi()

    async def show(self, stepper, first_step=False, last_step=False) -> None:
        with ui.step(self.name):
            self.add_help(HELP_TEXT)

            with ui.row().classes(
                "w-full justify-between items-center px-3 py-2 rounded-xl "
                "bg-slate-900/60 border border-white/10 mb-3"
            ):
                with ui.row().classes("items-center gap-2"):
                    self.select_all = ui.checkbox(
                        "Show all overlays",
                        value=(
                            bool(self.rois and all(r.enabled for r in self.rois))
                            if self.rois
                            else True
                        ),
                        on_change=self._select_all_rois,
                    ).tooltip("Toggle all reference point overlays on canvas")
                    self._sync_select_all_checkbox()

                with ui.row().classes("items-center gap-2"):
                    ui.button(
                        "Add Reference Point",
                        icon="add_circle_outline",
                        on_click=self._add_roi,
                    ).props("color=primary dense").classes(
                        "px-3 py-1 text-xs font-semibold bg-gradient-to-r "
                        "from-blue-600 to-cyan-600 text-white rounded-lg shadow-sm"
                    ).tooltip(
                        "Add a new reference landmark bounding box"
                    )

            self.container = ui.column().classes("w-full gap-2")
            super().add_navigator(stepper, first_step, last_step)
