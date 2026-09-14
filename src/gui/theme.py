import json

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
TOOLBAR_ROW = (
    "w-full items-center justify-between gap-3 mb-3 p-3 rounded-xl "
    "bg-slate-900/60 border border-white/10"
)

# --- Status & Classification Badges ---
BADGE_SUCCESS = (
    "bg-emerald-950/60 text-emerald-300 border border-emerald-500/30 "
    "text-[10px] px-2 py-0.5 rounded-full font-medium"
)
BADGE_INFO = (
    "bg-cyan-950/60 text-cyan-300 border border-cyan-500/30 "
    "text-[10px] px-2 py-0.5 rounded-full font-medium"
)
BADGE_WARNING = (
    "bg-amber-950/60 text-amber-300 border border-amber-500/30 "
    "text-[10px] px-2 py-0.5 rounded-full font-medium"
)
BADGE_ERROR = (
    "bg-rose-950/60 text-rose-300 border border-rose-500/30 "
    "text-[10px] px-2 py-0.5 rounded-full font-medium"
)
BADGE_PURPLE = (
    "bg-purple-950/60 text-purple-300 border border-purple-500/30 "
    "text-[10px] px-2 py-0.5 rounded-full font-medium"
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
    """Copy text to clipboard with automatic fallback for non-secure HTTP (e.g. LAN IP) contexts."""
    escaped_json = json.dumps(text)
    ui.run_javascript(f"""
        (function(text) {{
            function fallbackCopy(val) {{
                try {{
                    var t = document.createElement("textarea");
                    t.value = val;
                    t.setAttribute("readonly", "");
                    t.style.position = "fixed";
                    t.style.left = "0";
                    t.style.top = "0";
                    t.style.width = "2em";
                    t.style.height = "2em";
                    t.style.padding = "0";
                    t.style.border = "none";
                    t.style.outline = "none";
                    t.style.boxShadow = "none";
                    t.style.background = "transparent";
                    t.style.opacity = "0.01";
                    t.style.zIndex = "-1";
                    document.body.appendChild(t);
                    t.focus();
                    t.select();
                    t.setSelectionRange(0, val.length);
                    var successful = false;
                    try {{
                        successful = document.execCommand("copy");
                    }} catch (e) {{
                        console.warn("document.execCommand copy error:", e);
                    }}
                    document.body.removeChild(t);
                    return successful;
                }} catch (err) {{
                    console.error("Fallback clipboard copy failed:", err);
                    return false;
                }}
            }}

            if (navigator.clipboard && window.isSecureContext) {{
                navigator.clipboard.writeText(text).catch(function(e) {{
                    console.warn("navigator.clipboard failed, attempting fallback:", e);
                    fallbackCopy(text);
                }});
                return;
            }}

            if (window.Quasar && typeof window.Quasar.copyToClipboard === "function") {{
                window.Quasar.copyToClipboard(text).catch(function(e) {{
                    console.warn("Quasar copyToClipboard failed, attempting fallback:", e);
                    fallbackCopy(text);
                }});
                return;
            }}

            fallbackCopy(text);
        }})({escaped_json});
    """)
    if notify_message:
        ui.notify(notify_message, type="positive")
