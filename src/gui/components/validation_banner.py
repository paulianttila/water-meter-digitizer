"""Reusable reactive validation / status banner component for configuration state."""

from nicegui import ui


class ValidationBanner:
    """Standardized banner displaying configuration persistence and validity status."""

    def __init__(
        self,
        saved_text: str = (
            "Configuration and reference templates successfully saved to disk. "
            "Click 'Take In Use' to apply changes immediately to running services."
        ),
        unsaved_text: str = (
            "Configuration not yet saved. Review the configuration below "
            "and click 'Save Config' when ready to write files to disk."
        ),
    ) -> None:
        self.saved_text = saved_text
        self.unsaved_text = unsaved_text
        self.banner: ui.row | None = None
        self.icon: ui.icon | None = None
        self.label: ui.label | None = None
        self.is_saved = False

    def render(
        self,
        initial_saved: bool = False,
        classes: str = "w-full p-3.5 rounded-xl border flex items-center gap-3 text-sm transition-all",
    ) -> ui.row:
        """Render the banner DOM element."""
        self.is_saved = initial_saved
        bg_cls = (
            "bg-emerald-950/40 border-emerald-500/40 text-emerald-200"
            if initial_saved
            else "bg-amber-950/40 border-amber-500/40 text-amber-200"
        )
        icon_name = "check_circle" if initial_saved else "pending_actions"
        icon_color = "emerald" if initial_saved else "amber"
        text = self.saved_text if initial_saved else self.unsaved_text

        with ui.row().classes(f"{classes} {bg_cls}") as self.banner:
            self.icon = ui.icon(icon_name, color=icon_color).classes("text-xl shrink-0")
            self.label = ui.label(text).classes("flex-1 leading-snug")
        return self.banner

    def update(self, is_saved: bool, custom_message: str | None = None) -> None:
        """Update banner appearance and message based on save state."""
        self.is_saved = is_saved
        if self.banner is None or self.icon is None or self.label is None:
            return

        if is_saved:
            self.banner.classes(
                "bg-emerald-950/40 border-emerald-500/40 text-emerald-200",
                remove="bg-amber-950/40 border-amber-500/40 text-amber-200",
            )
            self.icon.props("name=check_circle color=emerald")
            self.label.text = custom_message or self.saved_text
        else:
            self.banner.classes(
                "bg-amber-950/40 border-amber-500/40 text-amber-200",
                remove="bg-emerald-950/40 border-emerald-500/40 text-emerald-200",
            )
            self.icon.props("name=pending_actions color=amber")
            self.label.text = custom_message or self.unsaved_text
