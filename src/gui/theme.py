from nicegui import ui

# --- Card & Container Styles ---
CARD_CONTAINER = (
    "w-full max-w-5xl p-6 bg-slate-900 border border-white/10 rounded-2xl gap-4"
)
CARD_DEFAULT = "w-full p-4 rounded-xl bg-slate-900/60 border border-white/10"
CARD_SUBTLE = (
    "w-full p-3 rounded-xl bg-slate-950/50 border border-white/5 "
    "hover:border-indigo-500/30 transition-all"
)
CARD_PANEL = "w-full rounded-xl bg-slate-950 p-3 border border-white/10"
CARD_EXPANSION = (
    "w-full max-w-full bg-slate-900/60 border border-white/10 rounded-xl "
    "overflow-hidden shadow-sm hover:border-white/20 transition-colors shrink-0 min-w-0"
)
CARD_HERO_TOTAL = (
    "p-4 rounded-2xl border border-cyan-500/40 flex-1 min-w-[220px] backdrop-blur-md "
    "bg-gradient-to-br from-blue-950/60 via-slate-900/80 to-cyan-950/40 shadow-xl shadow-cyan-500/5"
)
CARD_HERO_SUBMETER = (
    "p-4 rounded-2xl border border-white/10 flex-1 min-w-[220px] backdrop-blur-md "
    "bg-slate-900/70 shadow-lg"
)
CARD_TELEMETRY = (
    "p-4 rounded-2xl border border-white/10 bg-slate-900/70 shadow-lg min-w-[200px] "
    "flex-1 backdrop-blur-md"
)
CARD_DIGIT_CROP = (
    "p-2.5 rounded-xl bg-slate-900/90 border border-white/10 "
    "flex flex-col items-center gap-1 min-w-[80px] shadow-lg"
)
PANEL_STAGE_IMAGE = (
    "w-full rounded-2xl bg-slate-950/80 p-2.5 border border-white/10 "
    "flex items-center justify-center overflow-hidden shadow-xl"
)
BANNER_WARNING = (
    "w-full p-3.5 rounded-2xl bg-amber-950/50 border border-amber-500/40 "
    "text-amber-200 text-xs flex items-center justify-between gap-2 mb-3 shadow-lg"
)
PANEL_TAB_CONTENT = (
    "w-full h-full p-0 overflow-y-auto overflow-x-hidden min-w-0 max-w-full "
    "flex flex-col flex-nowrap gap-3 pr-1"
)
TOOLBAR_ROW = (
    "w-full items-center justify-between gap-3 mb-3 p-3 rounded-xl "
    "bg-slate-900/60 border border-white/10"
)

# --- Typography ---
HEADING_SECTION = "font-['Outfit'] font-bold text-base text-gray-100"
HEADING_SUBSECTION = (
    "text-xs font-semibold text-gray-300 uppercase tracking-wider font-mono"
)
TEXT_MONO_MUTED = "text-[11px] font-mono text-gray-400"
TEXT_MONO_SMALL = "text-[10px] font-mono text-gray-400"
FONT_MONO_VALUE = "font-['Outfit'] text-2xl font-bold"

# --- Layout Rows & Flexbox ---
ROW_HEADER = "w-full justify-between items-center"
ROW_ACTIONS = "items-center gap-2"
ROW_ITEMS_CENTER = "items-center gap-1.5"

# --- Inner Panels ---
PANEL_INNER = (
    "p-3 rounded-xl bg-slate-950/60 border border-white/5 "
    "flex flex-col justify-between gap-2"
)
PANEL_DARK = "w-full rounded-xl bg-slate-950 p-3 border border-white/10"

# --- Dialogs ---
DIALOG_CARD = (
    "w-full p-5 bg-slate-900 border border-white/10 "
    "rounded-2xl gap-4 shadow-2xl text-white"
)
DIALOG_HEADER_ROW = "w-full justify-between items-center pb-2 border-b border-white/10"
DIALOG_FOOTER_ROW = (
    "w-full justify-end items-center gap-2 pt-2 border-t border-white/10"
)

# --- Stats / Metric Cards ---
STAT_VALUE_LARGE = "font-['Outfit'] text-3xl font-extrabold tracking-tight"

# --- Interactive & Selectable Cards ---
CLICKABLE_CARD = (
    "cursor-pointer hover:border-cyan-500/50 hover:bg-slate-800/90 transition-all"
)
CARD_SELECTABLE = (
    "p-4 rounded-xl border-2 transition-all duration-150 cursor-pointer select-none "
    "active:scale-[0.99] flex flex-col justify-between"
)
CARD_SELECTABLE_ACTIVE_MODIFIERS = "border-indigo-500 bg-indigo-950/70 ring-2 ring-indigo-500/50 shadow-lg shadow-indigo-950/50"
CARD_SELECTABLE_INACTIVE_MODIFIERS = (
    "border-slate-700/80 bg-slate-800/40 hover:border-indigo-400/60 "
    "hover:bg-slate-800/80 hover:shadow-md"
)
CARD_SELECTABLE_ACTIVE = f"{CARD_SELECTABLE} {CARD_SELECTABLE_ACTIVE_MODIFIERS}"
CARD_SELECTABLE_INACTIVE = f"{CARD_SELECTABLE} {CARD_SELECTABLE_INACTIVE_MODIFIERS}"
CARD_SELECTABLE_BASE = CARD_SELECTABLE_INACTIVE
CARD_SELECTABLE_SELECTED = CARD_SELECTABLE_ACTIVE

# --- Status & Classification Badges ---
BADGE_SUCCESS = (
    "bg-emerald-950/60 text-emerald-300 border border-emerald-500/30 "
    "text-xs px-2.5 py-0.5 rounded-full font-medium"
)
BADGE_INFO = (
    "bg-cyan-950/60 text-cyan-300 border border-cyan-500/30 "
    "text-xs px-2.5 py-0.5 rounded-full font-medium"
)
BADGE_WARNING = (
    "bg-amber-950/60 text-amber-300 border border-amber-500/30 "
    "text-xs px-2.5 py-0.5 rounded-full font-medium"
)
BADGE_ERROR = (
    "bg-rose-950/60 text-rose-300 border border-rose-500/30 "
    "text-xs px-2.5 py-0.5 rounded-full font-medium"
)
BADGE_PURPLE = (
    "bg-purple-950/60 text-purple-300 border border-purple-500/30 "
    "text-xs px-2.5 py-0.5 rounded-full font-medium"
)
BADGE_FILLED = (
    "bg-indigo-950/60 text-indigo-300 border border-indigo-500/30 "
    "text-xs px-2.5 py-0.5 rounded-full font-medium"
)
BADGE_MUTED = (
    "bg-slate-800/60 text-slate-400 border border-white/10 "
    "text-xs px-2.5 py-0.5 rounded-full font-medium"
)

# --- Config History & Snapshot Tags ---
TAG_AUTO_CLS = "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
TAG_SNAP_CLS = "bg-purple-500/10 text-purple-400 border border-purple-500/20"
BADGE_AUTO_CLS = BADGE_INFO
BADGE_SNAP_CLS = BADGE_PURPLE

# --- Interactive Button States ---
BTN_ACTIVE_CLS = "bg-cyan-600/80 text-white"
BTN_INACTIVE_CLS = "text-cyan-400 hover:bg-cyan-500/10"

# --- ROI Color Overlays (RGB & Hex) ---
COLOR_ROI_REFS = (16, 185, 129)  # Emerald Green
COLOR_ROI_DIGITAL = (59, 130, 246)  # Electric Blue
COLOR_ROI_ANALOG = (245, 158, 11)  # Vivid Amber / Orange

HEX_ROI_REFS = "#10b981"
HEX_ROI_DIGITAL = "#3b82f6"
HEX_ROI_ANALOG = "#f59e0b"


def copy_to_clipboard(text: str, notify_message: str = "") -> None:
    """Copy text to clipboard using NiceGUI clipboard service."""
    ui.clipboard.write(text)
    if notify_message:
        ui.notify(notify_message, type="positive")
