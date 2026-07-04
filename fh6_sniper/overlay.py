from __future__ import annotations
import collections
import ctypes
import logging
import math
import sys
import time
import webbrowser

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt, QPoint, QRect, QRectF, QTimer, Signal, QObject

from . import locales
from .locales import tr

# ── Color palette ───────────────────────────────────────────────────────────

_PRIMARY   = "#C6F94A"
_SECONDARY = "#F4A93B"
_TEXT_1    = "#F4F6F8"
_TEXT_2    = "#7E8A97"
_STATUS_VAL = "#F4F6F8"
_BTN_BG    = "#C6F94A"
_BTN_FG    = "#0A0D12"
_BTN_HV    = "#D4FB6E"

_BG_HDR   = "#070A0E"
_BG       = "#0B0D11"
_BG_MID   = "#13171D"
_CARD     = "#161B22"
_NAV_BG   = "#0B0D11"
_NAV_ACT  = "#1B2129"
_DIVIDER  = "#242B33"

_TRACK    = "#2A323C"
_GAUGE_TRACK = "#39434F"
_SUCCESS  = "#C6F94A"
_STATUSRED= "#FF5470"

# Header panel
_HEADER_BG = "#11161D"
_TAB_BG    = "#080A0E"
_TAB_HOVER = "#0E1218"

# Muted START/STOP button
_BTN_PAUSE_BG = "#1C232B"
_BTN_PAUSE_FG = "#8A949E"
_BTN_PAUSE_HV = "#222A33"

_BORDER   = _PRIMARY
_ROG      = _PRIMARY
_DIM      = _TEXT_2
_FAINT    = _TEXT_2
_RED_STAT = _STATUSRED
_IT_GREEN = _SUCCESS

# ── Fonts ────────────────────────────────────────────────────────────────────
_UI = "Sora"
_MONO = "Fira Code"
_FONTS_LOADED = False
_MSG_FILTER_INSTALLED = False


def _install_qt_msg_filter():
    global _MSG_FILTER_INSTALLED
    if _MSG_FILTER_INSTALLED:
        return
    _MSG_FILTER_INSTALLED = True
    try:
        prev = QtCore.qInstallMessageHandler(None)

        def handler(mode, ctx, message):
            low = message.lower()
            if ("populating font family aliases" in low
                    or "missing font family" in low
                    or "replace uses of missing font" in low):
                return
            if prev is not None:
                prev(mode, ctx, message)
        QtCore.qInstallMessageHandler(handler)
    except Exception:
        pass


def _set_process_dpi_aware():
    if not sys.platform.startswith("win"):
        return
    import ctypes
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(
            ctypes.c_void_p(-4))
        return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _load_fonts():
    global _FONTS_LOADED
    if _FONTS_LOADED:
        return
    _FONTS_LOADED = True
    try:
        QtGui.QFont.insertSubstitution(_UI, "Segoe UI")
        QtGui.QFont.insertSubstitution(_MONO, "Consolas")
    except Exception:
        pass
    import os
    def _wanted(fn):
        low = fn.lower()
        if not low.endswith((".ttf", ".otf")):
            return False
        return low.startswith(("sora", "firacode", "fira code",
                               "inter", "spacegrotesk", "space grotesk"))
    candidates = []
    base = getattr(sys, "_MEIPASS", None)
    if base:
        candidates.append(os.path.join(base, "fonts"))
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(os.path.dirname(sys.executable), "fonts"))
    here = os.path.dirname(os.path.abspath(__file__))
    roots = [here]
    try:
        roots.append(os.path.dirname(os.path.abspath(sys.argv[0])))
    except Exception:
        pass
    roots.append(os.getcwd())
    for r in roots:
        d = r
        for _ in range(5):
            candidates.append(os.path.join(d, "fonts"))
            nd = os.path.dirname(d)
            if nd == d:
                break
            d = nd
    sysroot = os.environ.get("SystemRoot", r"C:\Windows").lower()
    seen = set()
    loaded = []
    found_dir = None
    for d in candidates:
        d = os.path.normpath(d)
        if d in seen:
            continue
        seen.add(d)
        if d.lower().startswith(sysroot):
            continue
        try:
            if not os.path.isdir(d):
                continue
            for fn in os.listdir(d):
                if _wanted(fn):
                    fid = QtGui.QFontDatabase.addApplicationFont(
                        os.path.join(d, fn))
                    fams = QtGui.QFontDatabase.applicationFontFamilies(fid)
                    if fams:
                        loaded += list(fams)
                        found_dir = d
        except Exception:
            pass
        if any(f == _UI for f in loaded):
            break
    log = logging.getLogger("fh6")
    if loaded:
        log.debug("Fonts loaded from %s: %s", found_dir,
                  ", ".join(sorted(set(loaded))))
    else:
        log.debug("UI font '%s' not found - using system fallback. Put "
                  "Sora-Regular/Medium/SemiBold/Bold.ttf in a 'fonts' folder "
                  "next to the app.", _UI)

# ── Live UI scale ────────────────────────────────────────────────────────────
UI_SCALE_MIN, UI_SCALE_MAX = 0.7, 1.4
_SCALE = 1.0
_BASE_SCALE = 0.9


def _set_scale(scale):
    global _SCALE
    _SCALE = max(UI_SCALE_MIN, min(UI_SCALE_MAX, float(scale)))
    return _SCALE


def px(n):
    return max(1, round(n * _SCALE * _BASE_SCALE))


def fs(n):
    return max(9, round(n * _SCALE * _BASE_SCALE))


GEO_PAGE_W = 404
GEO_PAGE_H = 401
GEO_GAUGE_H = 182
GEO_GAUGE_RMAX = 128


# ── Settings menu spec ───────────────────────────────────────────────────────
SETTINGS_SPEC = [
    ("section", "Speed"),
    {"key": "poll_interval_ms", "label": "Poll interval (ms)", "kind": "range",
     "lo": 5, "hi": 150, "step": 1, "int": True,
     "desc": "How often the screen is re-checked. Lower = reacts sooner."},
    {"key": "key_hold_ms", "label": "Key hold (ms)", "kind": "range",
     "lo": 5, "hi": 80, "step": 1, "int": True,
     "desc": "Duration of each keypress. Lower = faster (too low drops keys)."},
    {"key": "between_keys_ms", "label": "Delay between keys (ms)", "kind": "range",
     "lo": 5, "hi": 120, "step": 1, "int": True,
     "desc": "Pause after each key. Lower = faster navigation."},
    {"key": "loop_pace_s", "label": "Delay between loops (s)", "kind": "slider",
     "lo": 0.0, "hi": 1.0, "step": 0.01, "int": False,
     "desc": "Pause between one search and the next. Lower = more attempts per minute."},
    {"key": "buyout_select_delay_ms", "label": "Confirm delay (ms)", "kind": "slider",
     "lo": 0, "hi": 500, "step": 5, "int": True,
     "desc": "Extra wait before confirming the purchase. 0 = maximum speed."},

    ("section", "Match search"),
    {"key": "match_threshold_ah_landing", "label": "Match: Landing", "kind": "slider",
     "lo": 0.50, "hi": 0.95, "step": 0.01, "int": False,
     "desc": "Threshold for the Auction House landing screen. Recommended ~0.80 (matches strong)."},
    {"key": "match_threshold_search", "label": "Match: Search", "kind": "slider",
     "lo": 0.50, "hi": 0.95, "step": 0.01, "int": False,
     "desc": "Threshold for the Search screen. Recommended ~0.80 (matches strong)."},
    {"key": "match_threshold_results", "label": "Match: Results", "kind": "slider",
     "lo": 0.50, "hi": 0.95, "step": 0.01, "int": False,
     "desc": "Threshold for the results list (cars found). Recommended ~0.80 (matches strong)."},
    {"key": "match_threshold_results_empty", "label": "Match: Empty results", "kind": "slider",
     "lo": 0.50, "hi": 0.95, "step": 0.01, "int": False,
     "desc": "Threshold for the 'no auctions' screen. Recommended ~0.80 (matches strong)."},
    {"key": "match_threshold_sold", "label": "Match: SOLD stamp", "kind": "slider",
     "lo": 0.40, "hi": 0.95, "step": 0.01, "int": False,
     "desc": "Match for the SOLD stamp (skips sold cars). Recommended ~0.70."},

    ("section", "Match buy"),
    {"key": "match_threshold_auction_options", "label": "Match: Auction options", "kind": "slider",
     "lo": 0.50, "hi": 0.95, "step": 0.01, "int": False,
     "desc": "Threshold for the auction options menu. Recommended ~0.80 (matches strong)."},
    {"key": "match_threshold_player_options", "label": "Match: Player options", "kind": "slider",
     "lo": 0.50, "hi": 0.95, "step": 0.01, "int": False,
     "desc": "Threshold for your own listing menu (sold cars). Recommended ~0.80 (matches strong)."},
    {"key": "match_threshold_buy_out", "label": "Match: Buy Out", "kind": "slider",
     "lo": 0.50, "hi": 0.95, "step": 0.01, "int": False,
     "desc": "Buy Out confirm screen. Recommended ~0.60 (weak match)."},
    {"key": "match_threshold_buyout_progress", "label": "Match: Buyout progress", "kind": "slider",
     "lo": 0.50, "hi": 0.95, "step": 0.01, "int": False,
     "desc": "Buyout 'in progress' screen. Recommended ~0.60 (weak match)."},

    ("section", "Match collect"),
    {"key": "match_threshold_buyout_success", "label": "Match: Buyout success", "kind": "slider",
     "lo": 0.50, "hi": 0.95, "step": 0.01, "int": False,
     "desc": "Threshold for the 'purchase successful' screen. Recommended ~0.78."},
    {"key": "match_threshold_buyout_failed", "label": "Match: Buyout failed", "kind": "slider",
     "lo": 0.50, "hi": 0.95, "step": 0.01, "int": False,
     "desc": "Threshold for the 'purchase failed' screen. Recommended ~0.78."},
    {"key": "match_threshold_claim_car", "label": "Match: Claim car", "kind": "slider",
     "lo": 0.50, "hi": 0.95, "step": 0.01, "int": False,
     "desc": "Threshold for the Claim/Collect car screen. Recommended ~0.78."},

    ("section", "Auto-stop"),
    {"key": "auto_stop_enabled", "label": "Auto-stop", "kind": "toggle",
     "desc": "Stops the bot when the limits below are reached."},
    {"key": "max_cars", "label": "Cars to buy", "kind": "slider",
     "lo": 1, "hi": 100, "step": 1, "int": True,
     "desc": "How many cars to buy before stopping."},
    {"key": "max_minutes", "label": "Maximum duration (min)", "kind": "slider",
     "lo": 1, "hi": 600, "step": 1, "int": False,
     "desc": "Maximum minutes of runtime before stopping."},

    ("section", "Behavior"),
    {"key": "jitter_maxbid", "label": "Update Max Bid", "kind": "toggle",
     "exclusive_group": "jitter_field",
     "desc": "Nudges Max Bid by 1 before each search to refresh the list. Turns off Max Buyout."},
    {"key": "jitter_maxbuyout", "label": "Update Max Buyout", "kind": "toggle",
     "exclusive_group": "jitter_field",
     "desc": "Same, but on Max Buyout. Turns off Max Bid."},
    {"key": "collect_after_buyout", "label": "Collect after buyout", "kind": "toggle",
     "desc": "Immediately collects the car you bought (slower but automatic)."},
    {"key": "notify_sound", "label": "Notification sound", "kind": "toggle",
     "desc": "Windows beep on every successful purchase."},
    {"key": "notify_toast", "label": "Windows notification", "kind": "toggle",
     "desc": "Windows toast notification on every purchase."},
    {"key": "overlay_capturable", "label": "Show overlay in captures", "kind": "toggle",
     "desc": "Makes the overlay visible in captures (for screenshots only). Keep off while sniping."},
    {"key": "match_score_logging", "label": "Diagnostic Mode", "kind": "toggle",
     "desc": "Logs all match scores to logs/match_diag.log for calibration. Keep off while sniping."},

    ("section", "Safety"),
    {"key": "timeout_results_s", "label": "Results timeout (s)", "kind": "slider",
     "lo": 2, "hi": 30, "step": 0.5, "int": False,
     "desc": "Maximum wait for results after a search."},
    {"key": "results_settle_s", "label": "Results settle timeout (s)", "kind": "slider",
     "lo": 0.0, "hi": 2.0, "step": 0.05, "int": False,
     "desc": "Wait for the SOLD stamps to finish fading in. 0 = off."},
    {"key": "timeout_outcome_s", "label": "Outcome timeout (s)", "kind": "slider",
     "lo": 5, "hi": 60, "step": 1, "int": False,
     "desc": "Maximum wait for the purchase outcome."},
    {"key": "timeout_claim_s", "label": "Collect timeout (s)", "kind": "slider",
     "lo": 5, "hi": 60, "step": 1, "int": False,
     "desc": "Maximum wait for collecting the car."},
    {"key": "timeout_generic_s", "label": "Generic timeout (s)", "kind": "slider",
     "lo": 2, "hi": 30, "step": 0.5, "int": False,
     "desc": "Maximum wait for other screen transitions."},
    {"key": "buyout_confirm_window_s", "label": "Buyout confirm window (s)", "kind": "slider",
     "lo": 0.0, "hi": 3.0, "step": 0.05, "int": False,
     "desc": "Wait for the outcome after the confirm Enter."},
    {"key": "buyout_open_wait_s", "label": "Buyout open wait (s)", "kind": "slider",
     "lo": 0.0, "hi": 5.0, "step": 0.1, "int": False,
     "desc": "How long it waits for the buy-out screen to open."},
    {"key": "collect_claim_wait_s", "label": "Collect: pause after confirm (s)", "kind": "slider",
     "lo": 0.0, "hi": 1.5, "step": 0.05, "int": False,
     "desc": "Pause after the Enter on car collect. Lower = faster collect."},
    {"key": "collect_unknown_wait_s", "label": "Collect: transition pause (s)", "kind": "slider",
     "lo": 0.0, "hi": 1.0, "step": 0.05, "int": False,
     "desc": "Pause when the screen is transitioning during collect."},

    ("section", "Customization Language"),
    {"key": "language", "label": "Language", "kind": "dropdown",
     "options": "languages",
     "desc": "Change the interface language. Applies live."},
    {"key": "game_language", "label": "Game language", "kind": "dropdown",
     "options": "languages",
     "desc": "The language Forza Horizon 6 runs in (matches the on-screen templates)."
             ""},

    ("section", "Customization Appearance"),
    {"key": "ui_scale", "label": "UI scale", "kind": "slider",
     "lo": 0.7, "hi": 1.4, "step": 0.05, "int": False,
     "desc": "Drag to resize. Applies live."},

    ("section", "Customization Keybinds"),
    {"key": "hotkey_start_stop", "label": "Start/stop key", "kind": "keybind",
     "desc": "Click, then press the key you want. Applies live. (Esc cancels.)"},
    {"key": "hotkey_panic", "label": "Panic key", "kind": "keybind",
     "desc": "Stops the bot and closes the tool. Click, then press a key. Applies live."},
]

SETTINGS_CATS = [
    ("Speed",    ["Speed", "Safety"]),
    ("Matching", ["Match search", "Match buy", "Match collect"]),
    ("Behavior", ["Behavior", "Auto-stop"]),
    ("Custom",   ["Customization Language", "Customization Appearance",
                  "Customization Keybinds"]),
]

SECTION_GROUPS = {
    "Match": ["Match search", "Match buy", "Match collect"],
    "Customization": ["Customization Language", "Customization Appearance",
                      "Customization Keybinds"],
}
_CHILD_TO_GROUP = {c: g for g, cs in SECTION_GROUPS.items() for c in cs}

NAV = [
    ("status",   "status",   "Status"),
    ("settings", "settings", "Settings"),
    ("logs",     "logs",     "Logs"),
    ("help",     "help",     "Help"),
    ("about",    "info",     "Info"),
]
def _fmt(val, is_int):
    if val is None:
        return ""
    if is_int:
        return str(int(round(val)))
    return f"{val:.2f}".rstrip("0").rstrip(".")


def _coerce(val, lo, hi, step, is_int):
    val = max(lo, min(hi, val))
    val = round((val - lo) / step) * step + lo
    val = max(lo, min(hi, val))
    return int(round(val)) if is_int else round(val, 4)


import re as _re

# ── Colour model (customisable theme) ────────────────────────────────────────

def _parse_color(s):
    if isinstance(s, QtGui.QColor):
        return QtGui.QColor(s)
    if not isinstance(s, str):
        return QtGui.QColor("#000000")
    t = s.strip()
    m = _re.fullmatch(r"#([0-9a-fA-F]{3,8})", t)
    if m:
        h = m.group(1)
        try:
            if len(h) == 3:
                r, g, b = (int(c * 2, 16) for c in h); a = 255
            elif len(h) == 4:
                r, g, b, a = (int(c * 2, 16) for c in h)
            elif len(h) == 6:
                r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16); a = 255
            elif len(h) == 8:
                r, g, b, a = (int(h[i:i + 2], 16) for i in (0, 2, 4, 6))
            else:
                return QtGui.QColor("#000000")
            return QtGui.QColor(r, g, b, a)
        except Exception:
            return QtGui.QColor("#000000")
    m = _re.fullmatch(r"rgba?\(([^)]*)\)", t, _re.IGNORECASE)
    if m:
        try:
            parts = [p.strip() for p in m.group(1).split(",")]
            r, g, b = (max(0, min(255, int(round(float(p))))) for p in parts[:3])
            a = 255
            if len(parts) >= 4:
                ap = parts[3]
                if ap.endswith("%"):
                    a = round(float(ap[:-1]) / 100.0 * 255)
                else:
                    f = float(ap)
                    a = round(f * 255) if f <= 1 else round(f)
            return QtGui.QColor(r, g, b, max(0, min(255, int(a))))
        except Exception:
            return QtGui.QColor("#000000")
    c = QtGui.QColor(t)
    return c if c.isValid() else QtGui.QColor("#000000")


def _color_to_css(c):
    if not isinstance(c, QtGui.QColor):
        c = _parse_color(c)
    if c.alpha() >= 255:
        return "#%02X%02X%02X" % (c.red(), c.green(), c.blue())
    return "rgba(%d, %d, %d, %.4g%%)" % (
        c.red(), c.green(), c.blue(), c.alpha() / 255.0 * 100.0)


def _color_to_hex(c):
    if not isinstance(c, QtGui.QColor):
        c = _parse_color(c)
    if c.alpha() >= 255:
        return "#%02X%02X%02X" % (c.red(), c.green(), c.blue())
    return "#%02X%02X%02X%02X" % (c.red(), c.green(), c.blue(), c.alpha())


def _qc(spec):
    return _parse_color(spec)


def _shift_value(c, dv):
    h, s, v, a = c.getHsvF()
    if h < 0:
        h = 0.0
    v = max(0.0, min(1.0, v + dv))
    return QtGui.QColor.fromHsvF(h, s, v, a)


COLOR_ROLES = [
    ("color_primary",   "Primary",        "Main accent.",          _PRIMARY),
    ("color_secondary", "Secondary",      "Paused bar and dot.",   _SECONDARY),
    ("color_status_values", "Status values", "Active-time & searches value.",
                                                                    _STATUS_VAL),
    ("color_text_dim",  "Secondary text", "Dim text.",             _TEXT_2),
    ("color_btn_bg",    "Button",         "Button background.",    _BTN_BG),
    ("color_btn_fg",    "Button text",    "Button label.",         _BTN_FG),
    ("color_btn_hover", "Button hover",   "Button hover.",         _BTN_HV),
    ("color_bg",        "Background",     "Window background.",    _BG),
    ("color_card",      "Panel",          "Cards and panels.",     _CARD),
    ("color_nav_active", "Selected item", "Active item highlight.", _NAV_ACT),
    ("color_control",   "Controls",       "Outlines and tracks.",  _TRACK),
]
_COLOR_DEFAULTS = {k: d for k, _l, _d, d in COLOR_ROLES}


def _apply_theme_from_cfg(cfg):
    global _PRIMARY, _SECONDARY, _TEXT_1, _TEXT_2, _BTN_BG, _BTN_FG, _BTN_HV
    global _BORDER, _ROG, _DIM, _FAINT, _STATUS_VAL
    global _BG, _BG_HDR, _BG_MID, _NAV_BG, _CARD, _NAV_ACT
    global _TRACK, _DIVIDER, _HEADER_BG, _TAB_BG, _TAB_HOVER, _GAUGE_TRACK

    def role(key):
        val = getattr(cfg, key, None) if cfg is not None else None
        if not val:
            val = _COLOR_DEFAULTS[key]
        return _color_to_css(_parse_color(val))

    _PRIMARY   = role("color_primary")
    _SECONDARY = role("color_secondary")
    _TEXT_1    = "#F4F6F8"
    _STATUS_VAL = role("color_status_values")
    _TEXT_2    = role("color_text_dim")
    _BTN_BG    = role("color_btn_bg")
    _BTN_FG    = role("color_btn_fg")
    _BTN_HV    = role("color_btn_hover")
    _bg_base = _parse_color(role("color_bg"))
    _BG      = _color_to_css(_bg_base)
    _BG_HDR  = _color_to_css(_shift_value(_bg_base, -0.0235))
    _NAV_BG  = _color_to_css(_shift_value(_bg_base, -0.0118))
    _BG_MID  = _color_to_css(_shift_value(_bg_base,  0.0157))
    _HEADER_BG = _color_to_css(_shift_value(_bg_base,  0.0275))
    _TAB_BG    = _color_to_css(_shift_value(_bg_base, -0.0180))
    _TAB_HOVER = _color_to_css(_shift_value(_bg_base,  0.0120))
    _CARD    = role("color_card")
    _NAV_ACT = role("color_nav_active")
    _TRACK = _DIVIDER = role("color_control")
    _GAUGE_TRACK = _color_to_css(_shift_value(_parse_color(_TRACK), 0.0700))
    _BORDER  = _ROG = _PRIMARY
    _DIM     = _FAINT = _TEXT_2


def _inject_color_settings():
    size_title = [{"kind": "note", "label": "Size"}]
    rows = [{"kind": "note", "label": "Colors"}]
    rows += [{"key": k, "label": lbl, "kind": "color", "desc": desc}
             for (k, lbl, desc, _default) in COLOR_ROLES]
    try:
        idx = next(i for i, s in enumerate(SETTINGS_SPEC)
                   if isinstance(s, dict) and s.get("key") == "ui_scale")
        SETTINGS_SPEC[idx:idx] = size_title
        idx = next(i for i, s in enumerate(SETTINGS_SPEC)
                   if isinstance(s, dict) and s.get("key") == "ui_scale")
        SETTINGS_SPEC[idx + 1:idx + 1] = rows
    except StopIteration:
        SETTINGS_SPEC.extend(rows)


_inject_color_settings()


# ── Icon (vector, recolorable) ───────────────────────────────────────────────
class Icon(QtWidgets.QWidget):
    def __init__(self, name, color=_DIM, size=22, parent=None):
        super().__init__(parent)
        self._name = name
        self._color = color
        self._sz = size
        self.setFixedSize(size, size)

    def set_color(self, color):
        if color != self._color:
            self._color = color
            self.update()

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        c = _qc(self._color)
        w = self.width()
        pen = QtGui.QPen(c, max(1.5, w * 0.09))
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        m = w * 0.14
        r = QRectF(m, m, w - 2 * m, w - 2 * m)
        n = self._name
        if n == "status":
            cx = cy = w / 2.0
            R = (w - 2 * m) / 2.0
            ring = R * 0.60
            gap = R * 0.30
            p.drawEllipse(QtCore.QPointF(cx, cy), ring, ring)
            p.drawLine(QtCore.QLineF(cx, cy - R, cx, cy - gap))
            p.drawLine(QtCore.QLineF(cx, cy + gap, cx, cy + R))
            p.drawLine(QtCore.QLineF(cx - R, cy, cx - gap, cy))
            p.drawLine(QtCore.QLineF(cx + R, cy, cx + gap, cy))
        elif n == "scope":
            cx = cy = w / 2.0
            R = (w - 2 * m) / 2.0
            ring = R * 0.72
            outer = R * 1.04
            p.drawEllipse(QtCore.QPointF(cx, cy), ring, ring)
            p.drawLine(QtCore.QLineF(cx, cy - outer, cx, cy + outer))
            p.drawLine(QtCore.QLineF(cx - outer, cy, cx + outer, cy))
        elif n == "settings":
            ys = (w * 0.30, w * 0.5, w * 0.70)
            knobs = (0.66, 0.36, 0.58)
            for y, kx in zip(ys, knobs):
                p.drawLine(int(m), int(y), int(w - m), int(y))
                p.setBrush(c)
                p.drawEllipse(QPoint(int(m + (w - 2 * m) * kx), int(y)),
                              int(w * 0.07), int(w * 0.07))
                p.setBrush(Qt.NoBrush)
        elif n == "logs":
            for y in (w * 0.32, w * 0.5, w * 0.68):
                p.drawLine(int(m), int(y), int(w - m), int(y))
        elif n == "help":
            p.drawEllipse(r)
            f = _mkfont(int(w * 0.42))
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignCenter, "?")
        elif n == "info":
            p.drawEllipse(r)
            f = _mkfont(int(w * 0.46))
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignCenter, "i")
        elif n == "close":
            p.drawLine(int(m), int(m), int(w - m), int(w - m))
            p.drawLine(int(w - m), int(m), int(m), int(w - m))
        p.end()


class HoverIcon(Icon):
    def __init__(self, name, color=_DIM, hover=_ROG, size=22, parent=None):
        super().__init__(name, color=color, size=size, parent=parent)
        self._base = color
        self._hover = hover

    def enterEvent(self, _e):
        self.set_color(self._hover)

    def leaveEvent(self, _e):
        self.set_color(self._base)


# ── Toggle switch (animated pill) ────────────────────────────────────────────
class ToggleSwitch(QtWidgets.QWidget):
    def __init__(self, value=False, command=None, parent=None):
        super().__init__(parent)
        self._value = bool(value)
        self._command = command
        self._W, self._H = px(46), px(26)
        self.setFixedSize(self._W, self._H)
        self.setCursor(Qt.PointingHandCursor)
        self._pos = 1.0 if self._value else 0.0
        self._anim = QtCore.QVariantAnimation(self)
        self._anim.setDuration(130)
        self._anim.valueChanged.connect(self._on_anim)

    def _on_anim(self, v):
        self._pos = float(v)
        self.update()

    def get(self):
        return self._value

    def set(self, v, emit=False):
        v = bool(v)
        if v == self._value:
            return
        self._value = v
        self._animate_to(1.0 if v else 0.0)
        if emit and self._command:
            self._command(self._value)

    def _animate_to(self, target):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(target)
        self._anim.start()

    def mousePressEvent(self, _e):
        self._value = not self._value
        self._animate_to(1.0 if self._value else 0.0)
        if self._command:
            self._command(self._value)

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        w, h = self.width(), self.height()
        track = _qc(_ROG if self._value else _TRACK)
        p.setBrush(track)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        margin = h * 0.16
        d = h - 2 * margin
        x0 = margin
        x1 = w - margin - d
        kx = x0 + (x1 - x0) * self._pos
        p.setBrush(_qc("#ffffff"))
        p.drawEllipse(QRectF(kx, margin, d, d))
        p.end()


# ── Slider ───────────────────────────────────────────────────────────────────
class Slider(QtWidgets.QWidget):
    def __init__(self, value, lo, hi, step, is_int, width, on_change=None,
                 parent=None):
        super().__init__(parent)
        self._lo, self._hi, self._step, self._int = lo, hi, step, is_int
        self._on_change = on_change
        self._H = px(32)
        self._knob = px(19)
        self._track = px(9)
        self.setFixedSize(int(width), self._H)
        self.setCursor(Qt.PointingHandCursor)
        self._value = _coerce(value if value is not None else lo,
                              lo, hi, step, is_int)

    def get(self):
        return self._value

    def _x0(self):
        return self._knob / 2 + 1

    def _tw(self):
        return self.width() - self._knob - 2

    def _value_from_x(self, x):
        tw = self._tw()
        frac = 0.0 if tw <= 0 else (x - self._x0()) / tw
        frac = max(0.0, min(1.0, frac))
        val = self._lo + frac * (self._hi - self._lo)
        return _coerce(val, self._lo, self._hi, self._step, self._int)

    def _set_from_event(self, e):
        nv = self._value_from_x(e.position().x())
        if nv != self._value:
            self._value = nv
            self.update()
        if self._on_change:
            self._on_change(self._value)

    def mousePressEvent(self, e):
        self._set_from_event(e)

    def mouseMoveEvent(self, e):
        self._set_from_event(e)

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        cy = self.height() / 2
        x0 = self._x0()
        tw = self._tw()
        pen = QtGui.QPen(_qc(_TRACK), self._track)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(QtCore.QPointF(x0, cy), QtCore.QPointF(x0 + tw, cy))
        frac = 0.0 if self._hi == self._lo else \
            (self._value - self._lo) / (self._hi - self._lo)
        frac = max(0.0, min(1.0, frac))
        kx = x0 + tw * frac
        pen2 = QtGui.QPen(_qc(_ROG), self._track)
        pen2.setCapStyle(Qt.RoundCap)
        p.setPen(pen2)
        p.drawLine(QtCore.QPointF(x0, cy), QtCore.QPointF(kx, cy))
        p.setPen(Qt.NoPen)
        p.setBrush(_qc(_ROG))
        p.drawEllipse(QtCore.QPointF(kx, cy), self._knob / 2, self._knob / 2)
        p.end()
# ── Pill button ──────────────────────────────────────────────────────────────
class PillButton(QtWidgets.QWidget):
    def __init__(self, text, command=None, height=None, base=_BTN_BG,
                 hover=_BTN_HV, fg=_BTN_FG, parent=None):
        super().__init__(parent)
        self._text = text
        self._command = command
        self._base, self._hover, self._fg = base, hover, fg
        self._cur = base
        self._h = height or px(46)
        self.setFixedHeight(self._h)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Fixed)

    def set_command(self, cmd):
        self._command = cmd

    def set_mode(self, text, base, hover, fg):
        self._text, self._base, self._hover, self._fg = text, base, hover, fg
        self._cur = base
        self.update()

    def enterEvent(self, _e):
        self._cur = self._hover
        self.update()

    def leaveEvent(self, _e):
        self._cur = self._base
        self.update()

    def mousePressEvent(self, _e):
        if self._command:
            self._command()

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        w, h = self.width(), self.height()
        p.setBrush(_qc(self._cur))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(0, 0, w, h), px(14), px(14))
        f = _mkfont(fs(13))
        p.setFont(f)
        p.setPen(_qc(self._fg))
        p.drawText(self.rect(), Qt.AlignCenter, self._text)
        p.end()


# ── Small status dot ─────────────────────────────────────────────────────────
class Dot(QtWidgets.QWidget):
    def __init__(self, color=_DIM, size=10, parent=None):
        super().__init__(parent)
        self._c = color
        self.setFixedSize(size, size)

    def set_color(self, c):
        if c != self._c:
            self._c = c
            self.update()

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        p.setBrush(_qc(self._c))
        p.setPen(Qt.NoPen)
        m = px(1)
        p.drawEllipse(QRectF(m, m, self.width() - 2 * m, self.height() - 2 * m))
        p.end()


# ── Semicircle gauge (speedometer) ───────────────────────────────────────────
class Gauge(QtWidgets.QWidget):
    _SPAN = 184.0
    _START = 90.0 + _SPAN / 2.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._frac = 0.0
        self._frac_target = 0.0
        self._frac_ready = False
        self._accent = _GAUGE_TRACK
        self._word = tr("IDLE")
        self._word_color = _DIM
        self._time = "00:00"
        self._caption = tr("ACTIVE TIME")
        self.setFixedHeight(px(GEO_GAUGE_H))
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Fixed)
        self._frac_anim = QTimer(self)
        self._frac_anim.setInterval(16)
        self._frac_anim.timeout.connect(self._anim_step)

    def set_fraction(self, f):
        f = max(0.0, min(1.0, float(f)))
        if not self._frac_ready:
            self._frac = self._frac_target = f
            self._frac_ready = True
            self.update()
            return
        if abs(f - self._frac_target) < 1e-4:
            return
        self._frac_target = f
        if not self._frac_anim.isActive():
            self._frac_anim.start()

    def _anim_step(self):
        d = self._frac_target - self._frac
        if abs(d) <= 0.004:
            self._frac = self._frac_target
            self._frac_anim.stop()
        else:
            self._frac += d * 0.22
        self.update()

    def set_accent(self, color):
        if color != self._accent:
            self._accent = color
            self.update()

    def set_word(self, word, color):
        self._word, self._word_color = word, color
        self.update()

    def set_time(self, t):
        if t != self._time:
            self._time = t
            self.update()

    def _geom(self):
        w, h = self.width(), self.height()
        margin = px(10)
        thick = px(13)
        dip = max(0.0, math.sin(math.radians(self._SPAN / 2.0 - 90.0)))
        r_w = w / 2.0 - margin - thick * 1.4
        r_h = (h - margin - thick) / (1.0 + dip)
        R = max(px(28), min(r_w, r_h, float(px(GEO_GAUGE_RMAX))))
        cx = w / 2.0
        cy = margin + thick / 2.0 + R
        return cx, cy, R, thick

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        cx, cy, R, thick = self._geom()
        rect = QRectF(cx - R, cy - R, 2 * R, 2 * R)

        track = QtGui.QPen(_qc(_GAUGE_TRACK), thick)
        track.setCapStyle(Qt.RoundCap)
        p.setPen(track)
        p.drawArc(rect, int(self._START * 16), int(-self._SPAN * 16))

        lit = (self._frac > 0.001
               and self._accent not in (_TRACK, _GAUGE_TRACK))
        if lit and self._accent != _DIM:
            span16 = int(-self._SPAN * self._frac * 16)
            for wmul, alpha in ((2.35, 28), (1.65, 52)):
                gc = _qc(self._accent)
                gc.setAlpha(alpha)
                gp = QtGui.QPen(gc, thick * wmul)
                gp.setCapStyle(Qt.RoundCap)
                p.setPen(gp)
                p.drawArc(rect, int(self._START * 16), span16)
        if self._frac > 0.001:
            fill = QtGui.QPen(_qc(self._accent), thick)
            fill.setCapStyle(Qt.RoundCap)
            p.setPen(fill)
            p.drawArc(rect, int(self._START * 16),
                      int(-self._SPAN * self._frac * 16))

        n = 6
        pen_off = QtGui.QPen(_qc(_GAUGE_TRACK), max(1, px(2)))
        pen_off.setCapStyle(Qt.RoundCap)
        pen_on = QtGui.QPen(_qc(self._accent), max(1, px(2)))
        pen_on.setCapStyle(Qt.RoundCap)
        for i in range(n):
            a = self._START - self._SPAN * (i / (n - 1))
            ar = math.radians(a)
            r1, r2 = R - thick * 0.62, R - thick * 1.45
            p.setPen(pen_on if (lit and self._frac + 1e-6 >= i / (n - 1))
                     else pen_off)
            p.drawLine(QtCore.QPointF(cx + r1 * math.cos(ar),
                                      cy - r1 * math.sin(ar)),
                       QtCore.QPointF(cx + r2 * math.cos(ar),
                                      cy - r2 * math.sin(ar)))

        # state word
        wf = _mkfont(fs(12))
        wf.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, px(2))
        p.setFont(wf)
        p.setPen(_qc(self._word_color))
        self._centered(p, cy - R * 0.46, self._word)

        # big time (shrink a little when hours push it to HH:MM:SS)
        p.setFont(_mkfont(fs(24) if len(self._time) > 5 else fs(31)))
        p.setPen(_qc(_STATUS_VAL))
        self._centered(p, cy - R * 0.10, self._time)

        # caption
        cf = _mkfont(fs(9))
        cf.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, px(1))
        p.setFont(cf)
        p.setPen(_qc(_DIM))
        self._centered(p, cy + R * 0.20, self._caption)
        p.end()

    def _centered(self, p, ycenter, text):
        fm = p.fontMetrics()
        h = fm.height()
        rect = QRect(0, int(round(ycenter - h / 2.0)), self.width(), h)
        p.drawText(rect, Qt.AlignCenter, text)


# ── Top tab button ───────────────────────────────────────────────────────────
def _mkfont(pt, bold=True):
    f = QtGui.QFont(_UI, int(pt))
    f.setBold(bold)
    f.setHintingPreference(QtGui.QFont.PreferFullHinting)
    return f


def _fit_font(text, max_pt, avail_w, pad, bold=True):
    pt = int(max_pt)
    while pt > 7:
        f = _mkfont(pt, bold)
        if QtGui.QFontMetrics(f).horizontalAdvance(text) <= max(1, avail_w - pad):
            return f
        pt -= 1
    return _mkfont(7, bold)


class TabButton(QtWidgets.QWidget):
    def __init__(self, text, on_click=None, parent=None):
        super().__init__(parent)
        self._text = text
        self._on_click = on_click
        self._active = False
        self._hover = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(px(32))
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Fixed)
        self.setMinimumWidth(px(34))

    def set_active(self, a):
        if a != self._active:
            self._active = a
            self.update()

    def enterEvent(self, _e):
        self._hover = True
        self.update()

    def leaveEvent(self, _e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        e.accept()
        if self._on_click:
            self._on_click()

    def mouseMoveEvent(self, e):
        e.accept()

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        w, h = self.width(), self.height()
        rad = h / 2.0
        if self._active:
            p.setBrush(_qc(_PRIMARY))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(0, 0, w, h), rad, rad)
            fg = _qc(_BTN_FG)
        else:
            fg = _qc(_PRIMARY if self._hover else _DIM)
        p.setFont(_fit_font(self._text, fs(12), w, px(10)))
        p.setPen(fg)
        p.drawText(self.rect(), Qt.AlignCenter, self._text)
        p.end()


# ── Settings sub-category button ──────────────────────
class SubTabButton(QtWidgets.QWidget):
    def __init__(self, text, width=None, on_click=None, parent=None):
        super().__init__(parent)
        self._text = text
        self._on_click = on_click
        self._active = False
        self._hover = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(px(24))
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Fixed)
        self.setMinimumWidth(px(28))

    def set_active(self, a):
        if a != self._active:
            self._active = a
            self.update()

    def enterEvent(self, _e):
        self._hover = True
        self.update()

    def leaveEvent(self, _e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        e.accept()
        if self._on_click:
            self._on_click()

    def mouseMoveEvent(self, e):
        e.accept()

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        w, h = self.width(), self.height()
        rad = h / 2.0
        if self._active:
            p.setBrush(_qc(_PRIMARY))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(0, 0, w, h), rad, rad)
            fg = _qc(_BTN_FG)
        else:
            fg = _qc(_PRIMARY if self._hover else _DIM)
        p.setFont(_fit_font(self._text, fs(10), w, px(6)))
        p.setPen(fg)
        p.drawText(self.rect(), Qt.AlignCenter, self._text)
        p.end()


# ── Logging handler ──────────────────────────────────────────────────────────
class _OverlayLogHandler(logging.Handler):
    def __init__(self, overlay):
        super().__init__()
        self._ov = overlay

    def emit(self, record):
        try:
            msg = self.format(record)
        except Exception:
            try:
                msg = record.getMessage()
            except Exception:
                return
        self._ov.log(msg)


# ── Thread-safe bridge ───────────────────────────────────────────────────────
class _Bridge(QObject):
    status = Signal(str, object)
    running = Signal(bool)
    stats = Signal(int, int, int)
    logmsg = Signal(str)
    quit = Signal()
# ── Colour picker ────────────────────────────────────────────────────────────
def _paint_checker(p, rect, cell=None):
    cell = cell or px(6)
    p.fillRect(rect, _qc("#4a4a4a"))
    p.setPen(Qt.NoPen)
    p.setBrush(_qc("#6a6a6a"))
    x0, y0 = int(rect.left()), int(rect.top())
    nx = int(rect.width()) // cell + 1
    ny = int(rect.height()) // cell + 1
    for iy in range(ny):
        for ix in range(nx):
            if (ix + iy) % 2 == 0:
                p.drawRect(x0 + ix * cell, y0 + iy * cell, cell, cell)


def _clamp01(x):
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


class ColorButton(QtWidgets.QWidget):
    def __init__(self, value, on_open=None, width=None, parent=None):
        super().__init__(parent)
        self._value = _color_to_hex(_parse_color(value))
        self._on_open = on_open
        self.setFixedHeight(px(34))
        if width:
            self.setFixedWidth(int(width))
        self.setCursor(Qt.PointingHandCursor)

    def get(self):
        return self._value

    def set_color(self, value):
        self._value = _color_to_hex(_parse_color(value))
        self.update()

    def mousePressEvent(self, _e):
        if self._on_open:
            self._on_open(self)

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        w, h = self.width(), self.height()
        rad = px(8)
        path = QtGui.QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), rad, rad)
        p.fillPath(path, _qc(_CARD))
        f = QtGui.QFont(_MONO, fs(12))
        p.setFont(f)
        p.setPen(_qc(_DIM))
        p.drawText(QRectF(px(10), 0, w - px(10), h),
                   Qt.AlignVCenter | Qt.AlignLeft, self._value.upper())
        chip = QRectF(w - px(40), px(5), px(32), h - px(10))
        cp = QtGui.QPainterPath()
        cp.addRoundedRect(chip, px(5), px(5))
        p.save()
        p.setClipPath(cp)
        col = _qc(self._value)
        if col.alpha() < 255:
            _paint_checker(p, chip, px(5))
        p.fillRect(chip, col)
        p.restore()
        p.setPen(QtGui.QPen(_qc(_DIVIDER), max(1, px(1))))
        p.setBrush(Qt.NoBrush)
        p.drawPath(cp)
        p.drawPath(path)
        p.end()


class _DropdownItem(QtWidgets.QWidget):
    def __init__(self, value, label, selected, on_click, parent=None):
        super().__init__(parent)
        self._value = value
        self._label = label
        self._selected = selected
        self._hover = False
        self._on_click = on_click
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(px(32))

    def enterEvent(self, _e):
        self._hover = True
        self.update()

    def leaveEvent(self, _e):
        self._hover = False
        self.update()

    def mousePressEvent(self, _e):
        if self._on_click:
            self._on_click(self._value)

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        hot = self._hover or self._selected
        if hot:
            path = QtGui.QPainterPath()
            path.addRoundedRect(
                QRectF(0, 0, self.width(), self.height()), px(6), px(6))
            p.fillPath(path, _qc(_NAV_ACT))
        p.setFont(_mkfont(fs(13), False))
        p.setPen(_qc(_ROG if hot else _DIM))
        p.drawText(self.rect(), Qt.AlignCenter, self._label)
        p.end()


class _DropdownPopup(QtWidgets.QFrame):
    def __init__(self, anchor, options, current, on_choose, on_close):
        super().__init__(anchor.window())
        self.setWindowFlags(Qt.Popup)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self._on_choose = on_choose
        self._on_close = on_close
        self.setStyleSheet(
            f"background:{_CARD}; border:1px solid {_DIVIDER};"
            f"border-radius:{px(8)}px;")
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(px(4), px(4), px(4), px(4))
        lay.setSpacing(px(2))
        for v, lbl in options:
            lay.addWidget(_DropdownItem(
                v, lbl, selected=(v == current), on_click=self._pick))

    def _pick(self, value):
        self.close()
        if self._on_choose:
            self._on_choose(value)

    def hideEvent(self, e):
        if self._on_close:
            self._on_close()
        super().hideEvent(e)

    def show_below(self, anchor):
        self.setFixedWidth(anchor.width())
        gp = anchor.mapToGlobal(QPoint(0, anchor.height() + px(4)))
        self.move(gp)
        self.show()


class Dropdown(QtWidgets.QWidget):
    def __init__(self, value, options, on_change=None, width=None, parent=None):
        super().__init__(parent)
        self._options = [(str(v), str(lbl)) for v, lbl in options]
        self._value = str(value)
        if not any(v == self._value for v, _ in self._options) and self._options:
            self._value = self._options[0][0]
        self._on_change = on_change
        self._popup = None
        self._closed_at = 0.0
        self.setFixedHeight(px(34))
        if width:
            self.setFixedWidth(int(width))
        self.setCursor(Qt.PointingHandCursor)

    def get(self):
        return self._value

    def _label(self):
        for v, lbl in self._options:
            if v == self._value:
                return lbl
        return self._value

    def mousePressEvent(self, _e):
        self._toggle()

    def _toggle(self):
        if (time.monotonic() - self._closed_at) < 0.15:
            return
        if self._popup is not None and self._popup.isVisible():
            self._popup.close()
            return
        self._open_popup()

    def _open_popup(self):
        popup = _DropdownPopup(self, self._options, self._value,
                               self._choose, self._on_popup_closed)
        self._popup = popup
        popup.show_below(self)

    def _on_popup_closed(self):
        self._closed_at = time.monotonic()
        self._popup = None

    def _choose(self, value):
        value = str(value)
        if value == self._value:
            return
        self._value = value
        self.update()
        if self._on_change:
            self._on_change(value)

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        w, h = self.width(), self.height()
        rad = px(8)
        path = QtGui.QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), rad, rad)
        p.fillPath(path, _qc(_CARD))
        f = _mkfont(fs(13), False)
        p.setFont(f)
        p.setPen(_qc(_DIM))
        p.drawText(QRectF(px(28), 0, w - px(56), h),
                   Qt.AlignVCenter | Qt.AlignHCenter, self._label())
        cx, cy = w - px(18), h / 2
        s = px(4)
        chev = QtGui.QPainterPath()
        chev.moveTo(cx - s, cy - s / 2)
        chev.lineTo(cx, cy + s / 2)
        chev.lineTo(cx + s, cy - s / 2)
        pen = QtGui.QPen(_qc(_ROG), max(1, px(2)))
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(chev)
        p.setPen(QtGui.QPen(_qc(_DIVIDER), max(1, px(1))))
        p.drawPath(path)
        p.end()


# ── Keybind capture helpers ───────────────────────────────────────────────────

_QT_SPECIAL_TOKENS = {
    Qt.Key_Escape: "<esc>",
    Qt.Key_Space: "<space>",
    Qt.Key_Return: "<enter>",
    Qt.Key_Enter: "<enter>",
    Qt.Key_Tab: "<tab>",
    Qt.Key_Backspace: "<backspace>",
    Qt.Key_Delete: "<delete>",
    Qt.Key_Insert: "<insert>",
    Qt.Key_Home: "<home>",
    Qt.Key_End: "<end>",
    Qt.Key_PageUp: "<page_up>",
    Qt.Key_PageDown: "<page_down>",
    Qt.Key_Up: "<up>",
    Qt.Key_Down: "<down>",
    Qt.Key_Left: "<left>",
    Qt.Key_Right: "<right>",
    Qt.Key_CapsLock: "<caps_lock>",
    Qt.Key_NumLock: "<num_lock>",
    Qt.Key_ScrollLock: "<scroll_lock>",
    Qt.Key_Pause: "<pause>",
    Qt.Key_Print: "<print_screen>",
    Qt.Key_Menu: "<menu>",
}

_QT_PURE_MODIFIERS = {
    Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_AltGr,
    Qt.Key_Meta, Qt.Key_Super_L, Qt.Key_Super_R,
}


def _hotkey_token_for_key(key) -> str | None:
    if Qt.Key_F1 <= key <= Qt.Key_F35:
        return f"<f{key - Qt.Key_F1 + 1}>"
    if key in _QT_SPECIAL_TOKENS:
        return _QT_SPECIAL_TOKENS[key]
    if Qt.Key_A <= key <= Qt.Key_Z:
        return chr(key).lower()
    if Qt.Key_0 <= key <= Qt.Key_9:
        return chr(key)
    return None


def hotkey_from_qt_event(event) -> str | None:
    key = event.key()
    if key in _QT_PURE_MODIFIERS or key == 0:
        return None
    token = _hotkey_token_for_key(key)
    if token is None:
        return None
    mods = event.modifiers()
    prefix = []
    if mods & Qt.ControlModifier:
        prefix.append("<ctrl>")
    if mods & Qt.AltModifier:
        prefix.append("<alt>")
    if mods & Qt.ShiftModifier:
        prefix.append("<shift>")
    if mods & Qt.MetaModifier:
        prefix.append("<cmd>")
    return "+".join(prefix + [token])


_TOKEN_LABELS = {
    "esc": "Esc", "space": "Space", "enter": "Enter", "tab": "Tab",
    "backspace": "Backspace", "delete": "Del", "insert": "Ins",
    "home": "Home", "end": "End", "page_up": "PgUp", "page_down": "PgDn",
    "up": "\u2191", "down": "\u2193", "left": "\u2190", "right": "\u2192",
    "caps_lock": "Caps", "num_lock": "NumLk", "scroll_lock": "ScrLk",
    "pause": "Pause", "print_screen": "PrtSc", "menu": "Menu",
    "ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "cmd": "Win",
}


def hotkey_label(hotkey: str) -> str:
    if not hotkey:
        return "\u2014"
    parts = []
    for raw in str(hotkey).split("+"):
        tok = raw.strip()
        inner = tok[1:-1] if tok.startswith("<") and tok.endswith(">") else tok
        inner = inner.strip()
        if inner in _TOKEN_LABELS:
            parts.append(_TOKEN_LABELS[inner])
        elif inner.startswith("f") and inner[1:].isdigit():
            parts.append("F" + inner[1:])
        else:
            parts.append(inner.upper())
    return " + ".join(p for p in parts if p)


class KeybindButton(QtWidgets.QWidget):
    def __init__(self, value, on_capture=None, width=None, parent=None,
                 on_active=None):
        super().__init__(parent)
        self._value = str(value or "")
        self._on_capture = on_capture
        self._on_active = on_active
        self._capturing = False
        self.setFixedHeight(px(34))
        if width:
            self.setFixedWidth(int(width))
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)

    def get(self):
        return self._value

    def _start_capture(self):
        if self._capturing:
            return
        self._capturing = True
        self.setFocus(Qt.MouseFocusReason)
        self.grabKeyboard()
        if self._on_active:
            self._on_active(True)
        self.update()

    def _end_capture(self):
        if not self._capturing:
            return
        self._capturing = False
        try:
            self.releaseKeyboard()
        except Exception:
            pass
        if self._on_active:
            self._on_active(False)
        self.update()

    def mousePressEvent(self, _e):
        if self._capturing:
            self._end_capture()
        else:
            self._start_capture()

    def keyPressEvent(self, e):
        if not self._capturing:
            super().keyPressEvent(e)
            return
        if e.key() == Qt.Key_Escape:
            self._end_capture()
            return
        if e.key() in _QT_PURE_MODIFIERS:
            return
        hk = hotkey_from_qt_event(e)
        if hk is None:
            return
        self._value = hk
        self._end_capture()
        if self._on_capture:
            self._on_capture(hk)

    def focusOutEvent(self, e):
        self._end_capture()
        super().focusOutEvent(e)

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        w, h = self.width(), self.height()
        rad = px(8)
        path = QtGui.QPainterPath()
        path.addRoundedRect(QRectF(0, 0, w, h), rad, rad)
        p.fillPath(path, _qc(_NAV_ACT if self._capturing else _CARD))
        border = _qc(_ROG if self._capturing else _DIVIDER)
        p.setPen(QtGui.QPen(border, max(1, px(1))))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        if self._capturing:
            text, col = "Press a key\u2026", _ROG
            f = _mkfont(fs(12), False)
        else:
            text, col = hotkey_label(self._value), _DIM
            f = QtGui.QFont(_MONO, fs(13))
            f.setHintingPreference(QtGui.QFont.PreferFullHinting)
        p.setFont(f)
        p.setPen(_qc(col))
        p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, text)
        p.end()


class _SVField(QtWidgets.QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._h, self._s, self._v = 0.0, 1.0, 1.0
        self.setMinimumSize(px(210), px(150))
        self.setCursor(Qt.CrossCursor)

    def set_hsv(self, h, s, v):
        self._h, self._s, self._v = h, s, v
        self.update()

    def _pick(self, e):
        self._s = _clamp01(e.position().x() / max(1, self.width()))
        self._v = 1.0 - _clamp01(e.position().y() / max(1, self.height()))
        self.changed.emit()
        self.update()

    def mousePressEvent(self, e):
        self._pick(e)

    def mouseMoveEvent(self, e):
        self._pick(e)

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        w, h = self.width(), self.height()
        rect = QRectF(0, 0, w, h)
        path = QtGui.QPainterPath()
        path.addRoundedRect(rect, px(8), px(8))
        p.setClipPath(path)
        p.fillRect(rect, QtGui.QColor.fromHsvF(min(0.9999, self._h), 1.0, 1.0))
        gx = QtGui.QLinearGradient(0, 0, w, 0)
        gx.setColorAt(0.0, _qc("#ffffff"))
        gx.setColorAt(1.0, QtGui.QColor(255, 255, 255, 0))
        p.fillRect(rect, gx)
        gy = QtGui.QLinearGradient(0, 0, 0, h)
        gy.setColorAt(0.0, QtGui.QColor(0, 0, 0, 0))
        gy.setColorAt(1.0, _qc("#000000"))
        p.fillRect(rect, gy)
        p.setClipping(False)
        cx = self._s * w
        cy = (1.0 - self._v) * h
        ring = _qc("#000000") if self._v > 0.55 and self._s < 0.55 \
            else _qc("#ffffff")
        p.setPen(QtGui.QPen(ring, max(1.5, px(2))))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QtCore.QPointF(cx, cy), px(6), px(6))
        p.end()


class _HueBar(QtWidgets.QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._h = 0.0
        self.setFixedWidth(px(20))
        self.setMinimumHeight(px(150))
        self.setCursor(Qt.PointingHandCursor)

    def set_hue(self, h):
        self._h = h
        self.update()

    def _pick(self, e):
        self._h = _clamp01(e.position().y() / max(1, self.height()))
        if self._h > 0.9999:
            self._h = 0.9999
        self.changed.emit()
        self.update()

    def mousePressEvent(self, e):
        self._pick(e)

    def mouseMoveEvent(self, e):
        self._pick(e)

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        w, h = self.width(), self.height()
        rect = QRectF(0, 0, w, h)
        path = QtGui.QPainterPath()
        path.addRoundedRect(rect, w / 2, w / 2)
        p.setClipPath(path)
        g = QtGui.QLinearGradient(0, 0, 0, h)
        for i in range(7):
            t = i / 6.0
            g.setColorAt(t, QtGui.QColor.fromHsvF(min(0.9999, t), 1.0, 1.0))
        p.fillRect(rect, g)
        p.setClipping(False)
        cy = self._h * h
        p.setPen(QtGui.QPen(_qc("#ffffff"), max(1.5, px(2))))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(1, cy - px(3), w - 2, px(6)), px(3), px(3))
        p.end()


class _AlphaBar(QtWidgets.QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._a = 1.0
        self._col = _qc("#ff0028")
        self.setFixedWidth(px(20))
        self.setMinimumHeight(px(150))
        self.setCursor(Qt.PointingHandCursor)

    def set_alpha(self, a):
        self._a = a
        self.update()

    def set_color(self, c):
        self._col = _qc(c)
        self._col.setAlpha(255)
        self.update()

    def _pick(self, e):
        self._a = 1.0 - _clamp01(e.position().y() / max(1, self.height()))
        self.changed.emit()
        self.update()

    def mousePressEvent(self, e):
        self._pick(e)

    def mouseMoveEvent(self, e):
        self._pick(e)

    def paintEvent(self, _e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        w, h = self.width(), self.height()
        rect = QRectF(0, 0, w, h)
        path = QtGui.QPainterPath()
        path.addRoundedRect(rect, w / 2, w / 2)
        p.setClipPath(path)
        _paint_checker(p, rect, px(5))
        top = QtGui.QColor(self._col); top.setAlpha(255)
        bot = QtGui.QColor(self._col); bot.setAlpha(0)
        g = QtGui.QLinearGradient(0, 0, 0, h)
        g.setColorAt(0.0, top)
        g.setColorAt(1.0, bot)
        p.fillRect(rect, g)
        p.setClipping(False)
        cy = (1.0 - self._a) * h
        p.setPen(QtGui.QPen(_qc("#ffffff"), max(1.5, px(2))))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(1, cy - px(3), w - 2, px(6)), px(3), px(3))
        p.end()


class ColorPickerPopup(QtWidgets.QWidget):
    def __init__(self, value, default_hex, on_change, parent=None):
        super().__init__(parent)
        self._on_change = on_change
        self._default = default_hex
        self._committed = False
        self._guard = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool
                            | Qt.WindowStaysOnTopHint
                            | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        col = _parse_color(value)
        h, s, v, a = col.getHsvF()
        if h < 0:
            h = 0.0

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        card = QtWidgets.QFrame()
        card.setObjectName("pick")
        card.setStyleSheet(
            f"#pick{{background:{_BG_MID}; border:1px solid {_PRIMARY};"
            f"border-radius:{px(12)}px;}}")
        outer.addWidget(card)
        lay = QtWidgets.QVBoxLayout(card)
        lay.setContentsMargins(px(14), px(14), px(14), px(14))
        lay.setSpacing(px(10))

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(px(10))
        self._sv = _SVField()
        self._sv.set_hsv(h, s, v)
        top.addWidget(self._sv, 1)
        self._hue = _HueBar()
        self._hue.set_hue(h)
        top.addWidget(self._hue)
        self._alpha = _AlphaBar()
        self._alpha.set_alpha(a)
        self._alpha.set_color(col)
        top.addWidget(self._alpha)
        lay.addLayout(top)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(px(8))
        self._preview = QtWidgets.QFrame()
        self._preview.setFixedSize(px(34), px(34))
        row.addWidget(self._preview)
        self._hex = QtWidgets.QLineEdit()
        self._hex.setStyleSheet(
            f"background:{_CARD}; color:{_DIM}; border:1px solid {_DIVIDER};"
            f"border-radius:{px(6)}px; padding:{px(6)}px;"
            f"font-family:'Fira Code','Consolas'; font-size:{fs(13)}px;")
        self._hex.editingFinished.connect(self._hex_done)
        self._hex.textEdited.connect(self._hex_edited)
        row.addWidget(self._hex, 1)
        lay.addLayout(row)

        bottom = QtWidgets.QHBoxLayout()
        reset = QtWidgets.QLabel("Reset")
        reset.setCursor(Qt.PointingHandCursor)
        reset.setStyleSheet(
            f"color:{_TEXT_2}; font-family:'Sora','Segoe UI';"
            f"font-size:{fs(12)}px; font-weight:bold; background:transparent;")
        reset.mousePressEvent = lambda _e: self._reset()
        bottom.addWidget(reset)
        bottom.addStretch(1)
        done = PillButton("Done", height=px(34), base=_BTN_BG,
                          hover=_BTN_HV, fg=_BTN_FG,
                          command=self._commit_and_close)
        done.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                           QtWidgets.QSizePolicy.Fixed)
        done.setFixedWidth(px(110))
        bottom.addWidget(done)
        lay.addLayout(bottom)

        self.setFixedWidth(px(300))
        self._sv.changed.connect(self._from_sv)
        self._hue.changed.connect(self._from_hue)
        self._alpha.changed.connect(self._from_alpha)
        self._h, self._s, self._v, self._a = h, s, v, a
        self._refresh(emit=False)

    def _color(self):
        c = QtGui.QColor.fromHsvF(min(0.9999, _clamp01(self._h)),
                                  _clamp01(self._s), _clamp01(self._v))
        c.setAlphaF(_clamp01(self._a))
        return c

    def _refresh(self, emit=True):
        c = self._color()
        self._alpha.set_color(c)
        self._preview.setStyleSheet(
            f"background:{_color_to_css(c)}; border:1px solid {_DIVIDER};"
            f"border-radius:{px(8)}px;")
        self._guard = True
        self._hex.setText(_color_to_hex(c).upper())
        self._guard = False
        if emit and self._on_change:
            self._on_change(c, False)

    def _from_sv(self):
        self._s, self._v = self._sv._s, self._sv._v
        self._refresh()

    def _from_hue(self):
        self._h = self._hue._h
        self._sv.set_hsv(self._h, self._s, self._v)
        self._refresh()

    def _from_alpha(self):
        self._a = self._alpha._a
        self._refresh()

    def _hex_edited(self, _t):
        if self._guard:
            return
        c = _parse_color(self._hex.text())
        if not c.isValid():
            return
        h, s, v, a = c.getHsvF()
        if h < 0:
            h = self._h
        self._h, self._s, self._v, self._a = h, s, v, a
        self._sv.set_hsv(h, s, v)
        self._hue.set_hue(h)
        self._alpha.set_alpha(a)
        self._alpha.set_color(c)
        self._preview.setStyleSheet(
            f"background:{_color_to_css(c)}; border:1px solid {_DIVIDER};"
            f"border-radius:{px(8)}px;")
        if self._on_change:
            self._on_change(c, False)

    def _hex_done(self):
        if self._on_change:
            self._on_change(self._color(), False)

    def _reset(self):
        c = _parse_color(self._default)
        h, s, v, a = c.getHsvF()
        if h < 0:
            h = 0.0
        self._h, self._s, self._v, self._a = h, s, v, a
        self._sv.set_hsv(h, s, v)
        self._hue.set_hue(h)
        self._alpha.set_alpha(a)
        self._refresh()

    def show_at(self, anchor_widget):
        self.adjustSize()
        self._anchor = anchor_widget
        self._owner = anchor_widget.window()
        self.setWindowOpacity(0.0)
        self._place(nudge_owner=True)
        self.show()
        self.raise_()
        QtCore.QTimer.singleShot(0, lambda: self.setWindowOpacity(1.0))
        QtWidgets.QApplication.instance().installEventFilter(self)
    def _place(self, nudge_owner=False):
        win = getattr(self, "_owner", None)
        anchor = getattr(self, "_anchor", None)
        if win is None or anchor is None:
            return
        wg = win.frameGeometry()
        g = anchor.mapToGlobal(QPoint(0, 0))
        pw, ph = self.width(), self.sizeHint().height()
        scr = (QtWidgets.QApplication.screenAt(wg.center())
               or QtWidgets.QApplication.primaryScreen())
        av = scr.availableGeometry()
        overlap = px(10)
        x = wg.right() - overlap
        if x + pw > av.right() - 4:
            if nudge_owner:
                shift = (x + pw) - (av.right() - 4)
                nx = max(av.left() + 4, wg.left() - shift)
                win.move(int(nx), wg.top())
                wg = win.frameGeometry()
                x = wg.right() - overlap
            if x + pw > av.right() - 4:
                x = wg.left() + overlap - pw
        x = max(av.left() + 4, min(x, av.right() - pw - 4))
        y = g.y() - px(4)
        y = max(av.top() + 4, min(y, av.bottom() - ph - 4))
        self.move(int(x), int(y))

    def eventFilter(self, _obj, ev):
        if ev.type() == QtCore.QEvent.MouseButtonPress:
            if QtWidgets.QApplication.activePopupWidget() is not None:
                return False
            try:
                gp = ev.globalPosition().toPoint()
            except Exception:
                gp = ev.globalPos()
            if self.frameGeometry().contains(gp):
                return False
            QtCore.QTimer.singleShot(0, self._dismiss)
        return False

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter):
            self._commit_and_close()
        else:
            super().keyPressEvent(e)

    def _dismiss(self):
        if self._committed:
            return
        self._committed = True
        try:
            QtWidgets.QApplication.instance().removeEventFilter(self)
        except Exception:
            pass
        self.close()

    def _commit_and_close(self):
        if self._committed:
            return
        self._committed = True
        try:
            QtWidgets.QApplication.instance().removeEventFilter(self)
        except Exception:
            pass
        if self._on_change:
            self._on_change(self._color(), True)
        self.close()


class Overlay:
    def __init__(self, cfg=None, on_save=None, hide_from_capture: bool = True,
                 on_hotkeys_changed=None):
        self._cfg = cfg
        self._on_save = on_save
        self._on_hotkeys_changed = on_hotkeys_changed
        self._on_game_lang_changed = None
        self._hide_from_capture = hide_from_capture
        self._toggle_cb = None

        self._page = "status"
        self._status_src = "ready to start"
        self._status_kwargs = {}
        self._settings_open = True
        self._group_expanded = {g: False for g in SECTION_GROUPS}
        self._setting_widgets = {}
        self._excl_group = {}
        self._sec_index = {}
        self._value_labels = {}
        self._logs = collections.deque(maxlen=300)
        self._running = False
        self._active = False
        self._bought_n = 0
        self._autostop_done = False
        self._gauge = None
        self._started = None
        self._elapsed_base = 0.0
        self._segment_start = None
        self._was_running = False
        self._subbar_open = False
        self._settings_cat = None
        self._ready = False
        self._drag_off = None
        self._autosave_timer = None
        self._scale_timer = None
        self._theme_timer = None
        self._color_popup = None
        self._active_color_key = None
        self._hotkey_footer = None
        self._on_capture_active = None

        _set_scale(getattr(cfg, "ui_scale", 1.0) if cfg is not None else 1.0)
        locales.set_language(getattr(cfg, "language", "en") if cfg is not None else "en")
        _apply_theme_from_cfg(cfg)

        try:
            _set_process_dpi_aware()
        except Exception:
            pass
        try:
            QtWidgets.QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        except Exception:
            pass
        self._app = QtWidgets.QApplication.instance() \
            or QtWidgets.QApplication(sys.argv)
        _install_qt_msg_filter()
        _load_fonts()
        self._app.setQuitOnLastWindowClosed(False)
        try:
            self._app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        except Exception:
            pass
        try:
            if _UI in QtGui.QFontDatabase.families():
                self._app.setFont(QtGui.QFont(_UI))
        except Exception:
            pass

        self._win = QtWidgets.QWidget()
        self._win.setWindowTitle("AuctionSniper - V.2")
        self._win.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self._win.setAttribute(Qt.WA_TranslucentBackground, True)
        self._win.setAttribute(Qt.WA_NoSystemBackground, True)
        self._win.closeEvent = self._on_close_event

        self._bridge = _Bridge()
        self._bridge.status.connect(self._apply_status)
        self._bridge.running.connect(self._apply_running)
        self._bridge.stats.connect(self._apply_stats)
        self._bridge.logmsg.connect(self._add_log)
        self._bridge.quit.connect(self._do_quit)

        self._build_ui()
        self._apply_page_geometry(initial=True)
        self._ready = True

        self._tick_timer = QTimer(self._win)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start()

    # ── UI construction ──────────────────────────────────────────────────
    def _build_ui(self):
        self._PAGE_W = px(GEO_PAGE_W)
        self._PAGE_H = px(GEO_PAGE_H)

        outer = QtWidgets.QVBoxLayout(self._win)
        outer.setContentsMargins(px(8), px(8), px(8), px(8))

        self._frame = QtWidgets.QFrame(self._win)
        self._frame.setObjectName("frame")
        self._frame.setStyleSheet(
            f"#frame{{background:{_BG}; border-radius:{px(18)}px;}}")
        self._frame.setFixedWidth(self._PAGE_W + px(20))
        outer.addWidget(self._frame, 0, Qt.AlignHCenter)

        root = QtWidgets.QVBoxLayout(self._frame)
        root.setContentsMargins(px(10), px(10), px(10), px(6))
        root.setSpacing(px(10))

        root.addWidget(self._build_header())

        self._content = QtWidgets.QWidget()
        self._content.setStyleSheet("background:transparent;")
        self._content_lay = QtWidgets.QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(0, 0, 0, 0)
        self._content_lay.setSpacing(0)
        root.addWidget(self._content, 1)

        self._pages = {
            "status": self._build_status_page(),
            "settings": self._build_settings_page(),
            "logs": self._build_logs_page(),
            "help": self._build_help_page(),
            "about": self._build_about_page(),
        }
        for w in self._pages.values():
            w.setParent(self._content)
            w.hide()
        self._page_in_holder = None
        self._wide_h = 0

        self._toast_timer = QTimer(self._win)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.timeout.connect(self._toast.hide)

        self._select_page(self._page, refit=False)


    def _build_header(self):
        card = QtWidgets.QFrame()
        card.setObjectName("hcard")
        card.setStyleSheet(
            f"#hcard{{background:{_HEADER_BG}; border-radius:{px(16)}px;}}")
        card.mousePressEvent = self._drag_start
        card.mouseMoveEvent = self._drag_move
        v = QtWidgets.QVBoxLayout(card)
        v.setContentsMargins(px(13), px(11), px(13), px(12))
        v.setSpacing(px(12))

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(px(7))
        logo = Icon("scope", color=_ROG, size=px(26))
        logo.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        lglow = QtWidgets.QGraphicsDropShadowEffect(logo)
        lglow.setOffset(0, 0)
        lglow.setBlurRadius(px(14))
        lcol = _qc(_ROG)
        lcol.setAlpha(170)
        lglow.setColor(lcol)
        lglow.setEnabled(False)
        logo.setGraphicsEffect(lglow)
        self._logo_glow = lglow
        top.addWidget(logo)
        title_row = QtWidgets.QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(0)
        title = QtWidgets.QLabel(
            f"<span style='color:{_DIM}'>Auction</span>")
        title.setTextFormat(Qt.RichText)
        title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        title.setStyleSheet(
            "font-family:'Sora','Segoe UI';"
            f"font-size:{fs(18)}px; font-weight:bold; background:transparent;")
        title_row.addWidget(title)
        sniper = QtWidgets.QLabel("Sniper")
        sniper.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        sniper.setStyleSheet(
            f"color:{_PRIMARY}; font-family:'Sora','Segoe UI';"
            f"font-size:{fs(18)}px; font-weight:bold; background:transparent;")
        glow = QtWidgets.QGraphicsDropShadowEffect(sniper)
        glow.setOffset(0, 0)
        glow.setBlurRadius(px(16))
        gcol = _qc(_PRIMARY)
        gcol.setAlpha(170)
        glow.setColor(gcol)
        sniper.setGraphicsEffect(glow)
        title_row.addWidget(sniper)
        top.addLayout(title_row)
        top.addSpacing(px(6))
        self._toast = QtWidgets.QLabel(tr("Saved \u2713"))
        self._toast.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._toast.setStyleSheet(
            f"color:{_ROG}; font-family:'Sora','Segoe UI'; font-size:{fs(11)}px;"
            "font-weight:bold; background:transparent;")
        self._toast.hide()
        top.addWidget(self._toast)
        top.addStretch(1)
        info = HoverIcon("info", color=_DIM, hover=_ROG, size=px(20))
        info.setCursor(Qt.PointingHandCursor)
        info.mousePressEvent = lambda _e: self._nav_click("about")
        top.addWidget(info)
        top.addSpacing(px(10))
        close = HoverIcon("close", color=_DIM, hover=_ROG, size=px(18))
        close.setCursor(Qt.PointingHandCursor)
        close.mousePressEvent = lambda _e: self._win.close()
        top.addWidget(close)
        v.addLayout(top)

        v.addLayout(self._build_tab_row())
        self._dot = logo
        return card
    def _build_subbar_row(self):
        holder = QtWidgets.QWidget()
        holder.setStyleSheet("background:transparent;")
        h = QtWidgets.QHBoxLayout(holder)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(px(2))
        self._subcat_btns = {}
        for label, _secs in SETTINGS_CATS:
            b = SubTabButton(tr(label),
                             on_click=lambda c=label: self._sub_click(c))
            b.set_active(label == self._settings_cat)
            h.addWidget(b, 1)
            self._subcat_btns[label] = b
        return holder

    def _update_subbar(self):
        sb = getattr(self, "_subbar", None)
        if sb is None:
            return
        vis = (self._page == "settings" and self._subbar_open)
        was = sb.isVisible()
        if was == vis:
            for c, b in getattr(self, "_subcat_btns", {}).items():
                b.set_active(c == self._settings_cat)
            return
        self._win.setUpdatesEnabled(False)
        try:
            sb.setVisible(vis)
            for c, b in getattr(self, "_subcat_btns", {}).items():
                b.set_active(c == self._settings_cat)
            self._fixed_win_size = None
        finally:
            self._win.setUpdatesEnabled(True)
        self._apply_page_geometry()

    def _sub_click(self, cat):
        if cat == self._settings_cat:
            return
        self._settings_cat = cat
        for c, b in getattr(self, "_subcat_btns", {}).items():
            b.set_active(c == cat)
        self._populate_settings()
        sc = getattr(self, "_settings_scroll", None)
        if sc is not None:
            sc.verticalScrollBar().setValue(0)

    # ── Tabs  ─────────────────────────────────────
    def _build_tab_row(self):
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        bar = QtWidgets.QFrame()
        bar.setObjectName("tabbar")
        bar.setStyleSheet(
            f"#tabbar{{background:{_TAB_BG}; border-radius:{px(18)}px;}}")
        bar.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                          QtWidgets.QSizePolicy.Fixed)
        bv = QtWidgets.QVBoxLayout(bar)
        bv.setContentsMargins(px(4), px(4), px(4), px(4))
        bv.setSpacing(px(4))
        mr = QtWidgets.QHBoxLayout()
        mr.setContentsMargins(0, 0, 0, 0)
        mr.setSpacing(px(2))
        self._tab_btns = {}
        for key, _icon, label in NAV:
            if key == "about":
                continue
            if key == "settings" and self._cfg is None:
                continue
            tb = TabButton(tr(label), on_click=lambda k=key: self._nav_click(k))
            tb.set_active(self._page == key)
            mr.addWidget(tb, 1)
            self._tab_btns[key] = tb
        bv.addLayout(mr)
        self._subbar = self._build_subbar_row()
        bv.addWidget(self._subbar)
        self._subbar.setVisible(self._page == "settings" and self._subbar_open)
        row.addWidget(bar, 1)
        return row

    def _refresh_tabs(self):
        for key, tb in getattr(self, "_tab_btns", {}).items():
            tb.set_active(self._page == key)

    def _nav_click(self, key):
        if key == "settings" and self._page == "settings":
            self._subbar_open = not self._subbar_open
            if self._subbar_open:
                if not self._settings_cat:
                    self._settings_cat = SETTINGS_CATS[0][0]
                self._populate_settings()
            self._update_subbar()
            return
        if key == self._page:
            return
        if key == "settings":
            self._subbar_open = True
            if not self._settings_cat:
                self._settings_cat = SETTINGS_CATS[0][0]
            self._populate_settings()
        self._select_page(key)

    # ── Pages ──────────────────────────────────────────────────────────────
    def _build_status_page(self):
        page = QtWidgets.QWidget()
        page.setFixedSize(self._PAGE_W, self._PAGE_H)
        lay = QtWidgets.QVBoxLayout(page)
        lay.setContentsMargins(px(6), px(2), px(6), px(4))
        lay.setSpacing(0)

        self._gauge = Gauge()
        lay.addWidget(self._gauge)
        lay.addSpacing(px(4))

        phase_row = QtWidgets.QHBoxLayout()
        phase_row.setSpacing(px(7))
        phase_row.addStretch(1)
        self._phase_dot = Dot(color=_DIM, size=px(9))
        self._phase_lbl = QtWidgets.QLabel(tr("Idle"))
        self._phase_lbl.setStyleSheet(
            f"color:{_DIM}; font-family:'Sora','Segoe UI'; font-size:{fs(13)}px;"
            "font-weight:bold; background:transparent;")
        phase_row.addWidget(self._phase_dot)
        phase_row.addWidget(self._phase_lbl)
        phase_row.addStretch(1)
        lay.addLayout(phase_row)
        lay.addSpacing(px(16))

        cards = QtWidgets.QHBoxLayout()
        cards.setSpacing(px(9))
        cells = (
            ("BOUGHT", "_bought", _IT_GREEN),
            ("SEARCHES", "_searches", _STATUS_VAL),
            ("FAILED", "_fails", _RED_STAT),
        )
        for caption, attr, color in cells:
            card = QtWidgets.QFrame()
            card.setStyleSheet(f"background:{_CARD}; border-radius:{px(16)}px;")
            cl = QtWidgets.QVBoxLayout(card)
            cl.setContentsMargins(px(8), px(11), px(8), px(11))
            cl.setSpacing(px(3))
            cap = QtWidgets.QLabel(tr(caption))
            cap.setAlignment(Qt.AlignCenter)
            cap.setStyleSheet(
                f"color:{_FAINT}; font-family:'Sora','Segoe UI'; font-size:{fs(9)}px;"
                "font-weight:bold; background:transparent;")
            val = QtWidgets.QLabel("0")
            val.setAlignment(Qt.AlignCenter)
            val.setStyleSheet(
                f"color:{color}; font-family:'Sora','Segoe UI'; font-size:{fs(22)}px;"
                "font-weight:bold; background:transparent;")
            cl.addWidget(cap)
            cl.addWidget(val)
            card.setMinimumHeight(px(74))
            cards.addWidget(card, 1)
            self._value_labels[attr] = val
        lay.addLayout(cards)

        lay.addSpacing(px(16))
        self._btn = PillButton(tr("START"), base=_BTN_BG, hover=_BTN_HV, fg=_BTN_FG)
        lay.addWidget(self._btn)

        lay.addStretch(1)
        lay.addSpacing(px(4) + px(6) + px(8))
        start_k = hotkey_label(getattr(self._cfg, "hotkey_start_stop", "<f8>")
                               if self._cfg is not None else "<f8>")
        panic = hotkey_label(getattr(self._cfg, "hotkey_panic", "<f9>")
                             if self._cfg is not None else "<f9>")
        footer = QtWidgets.QLabel(
            f"{start_k}  {tr('start / stop')}      \u00b7      {panic}  {tr('panic / quit')}")
        footer.setObjectName("hotkeyFooter")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet(
            f"color:{_DIM}; font-family:'Sora','Segoe UI'; font-size:{fs(10)}px; background:transparent;")
        self._hotkey_footer = footer
        lay.addWidget(footer, 0, Qt.AlignHCenter)
        lay.addStretch(1)
        return page

    def _page_header(self, lay, title, subtitle):
        t = QtWidgets.QLabel(tr(title))
        t.setStyleSheet(
            f"color:{_PRIMARY}; font-family:'Sora','Segoe UI'; font-size:{fs(26)}px;"
            "font-weight:bold; background:transparent;")
        lay.addWidget(t)
        sub = QtWidgets.QLabel(tr(subtitle) if subtitle else "")
        sub.setWordWrap(True)
        sub.setStyleSheet(
            f"color:{_DIM}; font-family:'Sora','Segoe UI'; font-size:{fs(12)}px; background:transparent;")
        lay.addWidget(sub)
        return sub

    def _build_settings_page(self):
        page = QtWidgets.QWidget()
        page.setFixedSize(self._PAGE_W, self._PAGE_H)
        lay = QtWidgets.QVBoxLayout(page)
        lay.setContentsMargins(px(6), px(2), px(6), px(8))
        lay.setSpacing(px(6))
        self._sec_index = {}
        if self._cfg is None:
            self._settings_sub = self._page_header(lay, "Settings", "")
            msg = QtWidgets.QLabel(tr("Settings unavailable."))
            msg.setStyleSheet(f"color:{_DIM}; font-size:{fs(10)}px;")
            lay.addWidget(msg)
            lay.addStretch(1)
            return page

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea{background:transparent; border:none;}"
            "QScrollBar:vertical{background:transparent; width:0px; margin:0;}"
            "QScrollBar::handle:vertical{background:transparent;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
            "QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{"
            "background:transparent;}")
        self._settings_scroll = scroll
        inner = QtWidgets.QWidget()
        inner.setStyleSheet("background:transparent;")
        il = QtWidgets.QVBoxLayout(inner)
        il.setContentsMargins(0, 0, px(2), 0)
        il.setSpacing(px(9))
        self._settings_inner_lay = il
        self._populate_settings()
        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)
        return page

    def _populate_settings(self):
        il = getattr(self, "_settings_inner_lay", None)
        if il is None:
            return
        while il.count():
            item = il.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._setting_widgets = {}
        self._excl_group = {}
        self._sec_index = {}
        self._autostop_dependent = []

        self._settings_sub = self._page_header(il, "Settings", "")
        il.addSpacing(px(4))

        ordered = []
        secmap = {}
        cur = None
        for spec in SETTINGS_SPEC:
            if isinstance(spec, tuple) and spec[0] == "section":
                cur = (spec[1], [])
                ordered.append(cur)
                secmap[spec[1]] = cur[1]
            else:
                if cur is None:
                    cur = (None, [])
                    ordered.append(cur)
                cur[1].append(spec)

        filtered = bool(self._subbar_open and self._settings_cat)
        if filtered:
            cat_secs = []
            for label, secs in SETTINGS_CATS:
                if label == self._settings_cat:
                    cat_secs = secs
                    break
            plan = [(name, secmap.get(name, [])) for name in cat_secs]
        else:
            plan = ordered

        for name, specs in plan:
            if name is not None:
                il.addWidget(self._settings_section_header(name))
            for sp in specs:
                card = self._settings_card(sp)
                il.addWidget(card)
                if isinstance(sp, dict) and sp.get("key") in (
                        "max_cars", "max_minutes"):
                    self._autostop_dependent.append(card)
        il.addStretch(1)
        self._update_autostop_rows(
            bool(getattr(self._cfg, "auto_stop_enabled", False))
            if self._cfg is not None else False)

    def _update_autostop_rows(self, enabled):
        for card in getattr(self, "_autostop_dependent", []):
            try:
                card.setVisible(bool(enabled))
            except Exception:
                pass

    def _settings_section_header(self, name):
        wrap = QtWidgets.QWidget()
        wrap.setStyleSheet("background:transparent;")
        v = QtWidgets.QVBoxLayout(wrap)
        v.setContentsMargins(px(4), px(8), 0, px(0))
        v.setSpacing(0)
        lbl = QtWidgets.QLabel(tr(name).upper())
        lbl.setStyleSheet(
            f"color:{_DIM}; font-family:'Sora','Segoe UI'; font-size:{fs(11)}px;"
            "font-weight:bold; background:transparent;")
        v.addWidget(lbl)
        return wrap

    def _settings_card(self, spec):
        if spec.get("kind") == "note":
            return self._add_setting_row(spec)
        card = QtWidgets.QFrame()
        card.setObjectName("scard")
        card.setStyleSheet(
            f"#scard{{background:{_CARD}; border-radius:{px(14)}px;}}")
        cl = QtWidgets.QVBoxLayout(card)
        cl.setContentsMargins(px(14), px(12), px(14), px(12))
        cl.setSpacing(0)
        cl.addWidget(self._add_setting_row(spec))
        return card

    def _add_setting_row(self, spec):
        if spec.get("kind") == "note":
            row = QtWidgets.QWidget()
            v = QtWidgets.QVBoxLayout(row)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(px(2))
            if spec.get("label"):
                lab = QtWidgets.QLabel(tr(spec["label"]))
                lab.setStyleSheet(
                    f"color:{_ROG}; font-family:'Sora','Segoe UI'; font-size:{fs(13)}px;"
                    "font-weight:bold; background:transparent;")
                v.addWidget(lab)
            if spec.get("desc"):
                d = QtWidgets.QLabel(tr(spec["desc"]))
                d.setWordWrap(True)
                d.setStyleSheet(
                    f"color:{_DIM}; font-family:'Sora','Segoe UI'; font-size:{fs(12)}px;"
                    " background:transparent;")
                v.addWidget(d)
            return row

        key, kind = spec["key"], spec["kind"]
        cur = getattr(self._cfg, key, None)
        row = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(px(12))

        left = QtWidgets.QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(px(3))
        lab = QtWidgets.QLabel(tr(spec["label"]))
        lab.setWordWrap(True)
        lab.setStyleSheet(
            f"color:{_ROG}; font-family:'Sora','Segoe UI'; font-size:{fs(13)}px;"
            "font-weight:bold; background:transparent;")
        desc = QtWidgets.QLabel(tr(spec["desc"]))
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"color:{_DIM}; font-family:'Sora','Segoe UI'; font-size:{fs(12)}px;"
            " background:transparent;")
        left.addWidget(lab)
        left.addWidget(desc)
        left_box = QtWidgets.QWidget()
        left_box.setLayout(left)
        h.addWidget(left_box, 1)

        slider_w = px(104)
        ctrl_w = px(150)
        control = None

        if kind == "toggle":
            grp = spec.get("exclusive_group")

            def cmd(v, k=key, g=grp):
                if g and v:
                    for ok, (okind, ow) in self._setting_widgets.items():
                        if (okind == "toggle" and ok != k
                                and self._excl_group.get(ok) == g):
                            ow.set(False)
                if k == "overlay_capturable":
                    self._set_capturable(v)
                if k == "auto_stop_enabled":
                    self._update_autostop_rows(v)
                self._autosave()
            tg = ToggleSwitch(value=bool(cur), command=cmd)
            control = tg
            self._setting_widgets[key] = ("toggle", tg)
            if grp:
                self._excl_group[key] = grp

        elif kind == "slider":
            control = self._make_slider_line(key, cur, spec, slider_w, tag="")
            self._setting_widgets[key] = ("slider", self._last_slider)

        elif kind == "range":
            lo_cur, hi_cur = (cur if isinstance(cur, (tuple, list))
                              else (spec["lo"], spec["hi"]))
            box = QtWidgets.QWidget()
            bl = QtWidgets.QVBoxLayout(box)
            bl.setContentsMargins(0, 0, 0, 0)
            bl.setSpacing(px(5))
            sliders = []
            for sub, sval in (("min", lo_cur), ("max", hi_cur)):
                line = self._make_slider_line(
                    key + ":" + sub, sval, spec, slider_w, tag=sub)
                bl.addWidget(line)
                sliders.append(self._last_slider)
            control = box
            self._setting_widgets[key] = ("range", tuple(sliders))

        elif kind == "text":
            ent = QtWidgets.QLineEdit("" if cur is None else str(cur))
            ent.setFixedWidth(ctrl_w)
            ent.setStyleSheet(
                f"background:{_BG}; color:{_TEXT_1}; border:1px solid {_DIVIDER};"
                f"border-radius:{px(6)}px; padding:{px(5)}px; font-family:'Sora','Segoe UI';"
                f"font-size:{fs(13)}px;")
            ent.textEdited.connect(lambda _t: self._autosave_soon())
            ent.editingFinished.connect(self._autosave)
            control = ent
            self._setting_widgets[key] = ("text", ent)

        elif kind == "color":
            default_hex = _COLOR_DEFAULTS.get(key, "#000000")
            btn = ColorButton(
                cur if cur else default_hex,
                on_open=lambda b, k=key, d=default_hex:
                    self._open_color_picker(k, b, d),
                width=ctrl_w)
            control = btn
            self._setting_widgets[key] = ("color", btn)

        elif kind == "keybind":
            btn = KeybindButton(
                cur,
                on_capture=lambda v, k=key: self._on_keybind_captured(k, v),
                on_active=self._on_keybind_capture_active,
                width=ctrl_w)
            control = btn
            self._setting_widgets[key] = ("keybind", btn)

        elif kind == "dropdown":
            opts = spec.get("options")
            if opts == "languages":
                opts = list(locales.available())
            else:
                opts = list(opts or [])
            if key == "language":
                on_change = self._on_language_changed
            elif key == "game_language":
                on_change = self._on_game_language_changed
            else:
                on_change = lambda _v: self._autosave()
            dd = Dropdown(cur, opts, on_change=on_change, width=ctrl_w)
            control = dd
            self._setting_widgets[key] = ("dropdown", dd)

        if control is not None:
            h.addWidget(control, 0, Qt.AlignVCenter)
        return row

    def _make_slider_line(self, vkey, value, spec, slider_w, tag=""):
        cont = QtWidgets.QWidget()
        line = QtWidgets.QHBoxLayout(cont)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(px(6))
        if tag:
            tg = QtWidgets.QLabel(tag)
            tg.setFixedWidth(px(22))
            tg.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            tg.setStyleSheet(
                f"color:{_DIM}; font-size:{fs(10)}px; background:transparent;")
            line.addWidget(tg)
        vlab = QtWidgets.QLabel(_fmt(value, spec["int"]))
        vlab.setFixedWidth(px(40))
        vlab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        vlab.setStyleSheet(
            f"color:{_ROG}; font-family:'Sora','Segoe UI'; font-size:{fs(13)}px;"
            "font-weight:bold; background:transparent;")
        sl = Slider(value, spec["lo"], spec["hi"], spec["step"], spec["int"],
                    slider_w,
                    on_change=lambda v, lb=vlab, i=spec["int"], k=vkey:
                        self._on_slider_change(lb, v, i, k))
        line.addWidget(sl)
        line.addWidget(vlab)
        self._last_slider = sl
        return cont

    def _build_logs_page(self):
        page = QtWidgets.QWidget()
        page.setFixedSize(self._PAGE_W, self._PAGE_H)
        lay = QtWidgets.QVBoxLayout(page)
        lay.setContentsMargins(px(6), px(2), px(6), px(8))
        lay.setSpacing(px(8))
        self._page_header(lay, "Logs", "Safe to share: no keys or personal data.")

        bar = QtWidgets.QHBoxLayout()
        self._log_filter = QtWidgets.QLineEdit()
        self._log_filter.setStyleSheet(
            f"background:{_BG}; color:{_TEXT_1}; border:1px solid {_DIVIDER};"
            f"border-radius:{px(8)}px; padding:{px(5)}px; font-family:'Sora','Segoe UI';"
            f"font-size:{fs(12)}px;")
        self._log_filter.textChanged.connect(self._render_logs)
        bar.addWidget(self._log_filter, 1)
        copy = PillButton(tr("COPY"), height=px(34), command=self._copy_logs,
                          base=_BTN_BG, hover=_BTN_HV, fg=_BTN_FG)
        copy.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                           QtWidgets.QSizePolicy.Fixed)
        copy.setFixedWidth(px(96))
        bar.addWidget(copy)
        lay.addLayout(bar)

        self._log_text = QtWidgets.QPlainTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._log_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._log_text.setStyleSheet(
            f"background:{_CARD}; color:{_DIM}; border-radius:{px(14)}px;"
            f"padding:{px(6)}px; font-family:'Fira Code','Consolas','Courier New';"
            f"font-size:{fs(13)}px;")
        lay.addWidget(self._log_text, 1)
        self._render_logs()
        return page

    def _build_help_page(self):
        page = QtWidgets.QWidget()
        page.setFixedSize(self._PAGE_W, self._PAGE_H)
        outer = QtWidgets.QVBoxLayout(page)
        outer.setContentsMargins(px(6), px(2), px(6), px(8))
        outer.setSpacing(px(2))
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea{background:transparent; border:none;}"
            "QScrollBar:vertical{background:transparent; width:0px; margin:0;}"
            "QScrollBar::handle:vertical{background:transparent;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}")
        inner = QtWidgets.QWidget()
        inner.setStyleSheet("background:transparent;")
        lay = QtWidgets.QVBoxLayout(inner)
        lay.setContentsMargins(0, px(6), px(2), 0)
        lay.setSpacing(px(2))
        self._page_header(lay, "Help", "Quick start and troubleshooting.")
        lay.addSpacing(px(4))
        blocks = [
            ("Step 1 \u2013 Open the Auction House", [
                "Launch Forza Horizon 6 and go to the Auction House on the "
                "festival site.",
            ]),
            ("Step 2 \u2013 Configure the search", [
                "Open Search Auctions and set the filters:",
                "\u2022 Make and Model of the car you want.",
                "\u2022 Maximum buyout price as a safety limit. The bot buys the "
                "first matching car without checking the price, so this is the "
                "most you can spend per car. Set it carefully.",
                "Go back so the screen shows the main Auction House Screen. "
                "That's where the bot expects to start.",
            ]),
            ("Step 3 \u2013 Start the sniper", [
                "Right-click AuctionSniper.exe and run as administrator. A small "
                "overlay will appear in the top-right corner of the screen.",
                "Go back to FH6, press F8 or Start, and let it run.",
                "To stop: press F8 again, F9 for emergency stop, or click STOP "
                "on the overlay.",
            ]),
        ]
        for title, lines in blocks:
            tl = QtWidgets.QLabel(tr(title))
            tl.setStyleSheet(
                f"color:{_ROG}; font-family:'Sora','Segoe UI'; font-size:{fs(14)}px;"
                "font-weight:bold; background:transparent;")
            lay.addSpacing(px(10))
            lay.addWidget(tl)
            for ln in lines:
                if isinstance(ln, tuple):
                    text = tr(ln[0], **ln[1])
                else:
                    text = tr(ln)
                wl = QtWidgets.QLabel(text)
                wl.setWordWrap(True)
                wl.setStyleSheet(
                    f"color:{_DIM}; font-family:'Sora','Segoe UI'; font-size:{fs(13)}px; background:transparent;")
                lay.addWidget(wl)
        lay.addStretch(1)
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)
        return page

    def _build_about_page(self):
        page = QtWidgets.QWidget()
        page.setFixedSize(self._PAGE_W, self._PAGE_H)
        lay = QtWidgets.QVBoxLayout(page)
        lay.setContentsMargins(px(6), px(2), px(6), px(8))
        lay.setSpacing(px(4))
        self._page_header(lay, "Info", "")
        body = QtWidgets.QLabel(tr(
            "This is an updated and improved version of Frosty's FH6 Auction Sniper. " \
            "It is completely unrelated to Frosty's paid V2. " \
            "If you need support or want to contribute to "
            "the tool's development, feel free to join the dedicated Discord server."))
        body.setWordWrap(True)
        body.setStyleSheet(
            f"color:{_DIM}; font-family:'Sora','Segoe UI'; font-size:{fs(13)}px; background:transparent;")
        lay.addWidget(body)
        lay.addSpacing(px(10))
        btn = PillButton(tr("Join the Discord"), height=px(40),
                         base=_BTN_BG, hover=_BTN_HV, fg=_BTN_FG,
                         command=lambda: webbrowser.open("https://discord.gg/4fbQ7yNns8"))
        btn.setFixedWidth(px(220))
        wrap = QtWidgets.QHBoxLayout()
        wrap.addStretch(1)
        wrap.addWidget(btn)
        wrap.addStretch(1)
        lay.addLayout(wrap)
        lay.addSpacing(px(14))
        vt = QtWidgets.QLabel(tr("Version"))
        vt.setStyleSheet(
            f"color:{_ROG}; font-family:'Sora','Segoe UI'; font-size:{fs(14)}px;"
            "font-weight:bold; background:transparent;")
        lay.addWidget(vt)
        vv = QtWidgets.QLabel("V.2.2.0  \u00b7  Created by d1ablo")
        vv.setStyleSheet(
            f"color:{_DIM}; font-family:'Sora','Segoe UI'; font-size:{fs(13)}px; background:transparent;")
        lay.addWidget(vv)
        lay.addStretch(1)
        return page

    # ── Page / section switching ─────────────────────────────────────────
    def _select_page(self, key, refit=True):
        if key not in self._pages:
            return
        same = (key == self._page_in_holder)
        self._page = key
        if not same:
            if self._page_in_holder is not None and \
                    self._page_in_holder in self._pages:
                old = self._pages[self._page_in_holder]
                self._content_lay.removeWidget(old)
                old.hide()
            page = self._pages[key]
            self._content_lay.addWidget(page)
            page.show()
            self._page_in_holder = key
        self._refresh_tabs()
        sb = getattr(self, "_subbar", None)
        if sb is not None:
            vis = (key == "settings" and self._subbar_open)
            if sb.isVisible() != vis:
                sb.setVisible(vis)
                self._fixed_win_size = None
            for c, b in getattr(self, "_subcat_btns", {}).items():
                b.set_active(c == self._settings_cat)
        if key == "logs":
            self._render_logs()
        if refit:
            self._apply_page_geometry()
    def _equalize_wide_pages(self):
        self._wide_h = 0

    def _screen_at(self, point=None):
        if point is None:
            point = self._win.frameGeometry().center()
        s = self._app.screenAt(point)
        return s or self._win.screen() or self._app.primaryScreen()

    def _virtual_rect(self):
        s = self._win.screen() or self._app.primaryScreen()
        return s.virtualGeometry()

    def _clamp_position(self):
        geo = self._screen_at().availableGeometry()
        w, h = self._win.width(), self._win.height()
        g = self._win.geometry()
        x = min(g.left(), geo.right() - w - 8)
        x = max(geo.left() + 8, x)
        y = min(g.top(), geo.bottom() - h - 8)
        y = max(geo.top() + 8, y)
        if x != g.left() or y != g.top():
            self._win.move(int(x), int(y))

    def _apply_page_geometry(self, initial=False):
        if initial or not self._win.isVisible():
            self._geometry_pass(initial=True)
        else:
            QTimer.singleShot(0, lambda: self._geometry_pass(initial=False))

    def _geometry_pass(self, initial=False):
        try:
            self._geometry_pass_impl(initial=initial)
        except Exception:
            logging.getLogger("fh6").exception("geometry pass failed")

    def _geometry_pass_impl(self, initial=False):
        if self._wide_h is None and self._win.isVisible():
            self._equalize_wide_pages()
        self._win.layout().activate()
        cached = getattr(self, "_fixed_win_size", None)
        if cached is None or initial:
            toast = getattr(self, "_toast", None)
            was_vis = toast is not None and toast.isVisible()
            if was_vis:
                toast.hide()
            self._win.layout().activate()
            sh = self._win.sizeHint()
            mh = self._win.minimumSizeHint()
            w = max(sh.width(), mh.width())
            h = max(sh.height(), mh.height())
            if was_vis:
                toast.show()
            cur = self._win.size()
            if (w < px(150) or h < px(150)) and cur.width() > px(150) \
                    and cur.height() > px(150):
                w, h = cur.width(), cur.height()
            self._fixed_win_size = (int(w), int(h))
        w, h = self._fixed_win_size
        if (not initial and self._win.isVisible()
                and self._win.width() == w and self._win.height() == h):
            QTimer.singleShot(0, self._finalize_after_layout)
            return
        was_enabled = self._win.updatesEnabled()
        self._win.setUpdatesEnabled(False)
        self._win.setFixedSize(w, h)
        old = self._win.geometry()
        if initial or not self._win.isVisible():
            screen = self._app.primaryScreen()
        else:
            screen = self._screen_at(old.center())
        geo = screen.availableGeometry()
        if initial or not self._win.isVisible():
            x = geo.right() - w - 24
            y = geo.top() + 24
        else:
            x = old.right() + 1 - w
            y = old.top()
        x = min(x, geo.right() - w - 8)
        x = max(geo.left() + 8, x)
        y = min(y, geo.bottom() - h - 8)
        y = max(geo.top() + 8, y)
        self._win.setGeometry(QRect(int(x), int(y), int(w), int(h)))
        if was_enabled:
            self._win.setUpdatesEnabled(True)
        QTimer.singleShot(0, self._finalize_after_layout)
    def _finalize_after_layout(self):
        try:
            self._clamp_position()
        except Exception:
            logging.getLogger("fh6").exception("finalize layout failed")

    # ── Drag ──────────────────────────────────────────────────────────────
    def _drag_start(self, e):
        self._drag_off = e.globalPosition().toPoint() - self._win.pos()

    def _drag_move(self, e):
        if self._drag_off is None:
            return
        target = e.globalPosition().toPoint() - self._drag_off
        vr = self._virtual_rect()
        w, h = self._win.width(), self._win.height()
        x = max(vr.left(), min(target.x(), vr.right() - w))
        y = max(vr.top(), min(target.y(), vr.bottom() - h))
        self._win.move(int(x), int(y))

    # ── Status / state ────────────────────────────────────────────────────
    def _set_button(self, running, paused=False):
        if running and paused:
            self._btn.set_mode(tr("STOP"), _BTN_PAUSE_BG, _BTN_PAUSE_HV,
                               _BTN_PAUSE_FG)
        elif running:
            self._btn.set_mode(tr("STOP"), _BTN_BG, _BTN_HV, _BTN_FG)
        else:
            self._btn.set_mode(tr("START"), _BTN_BG, _BTN_HV, _BTN_FG)

    def _gauge_fraction(self):
        if self._autostop_done:
            return 1.0
        cfg = self._cfg
        auto = bool(getattr(cfg, "auto_stop_enabled", False)) if cfg else False
        if not self._running:
            if (auto and getattr(self, "_carry_valid", False)
                    and getattr(self, "_bought_n", 0) > 0):
                try:
                    maxc = max(1, int(getattr(cfg, "max_cars", 1)))
                except Exception:
                    maxc = 1
                return max(0.0, min(1.0, self._bought_n / maxc))
            return 0.0
        if not auto:
            return 1.0
        try:
            maxc = max(1, int(getattr(cfg, "max_cars", 1)))
        except Exception:
            maxc = 1
        return max(0.0, min(1.0, self._bought_n / maxc))

    def _retint(self):
        src = (self._status_src or "").lower()
        paused = ("paused" in src)
        self._update_run_clock(self._running, paused)
        if not self._running:
            if self._autostop_done:
                word, color = tr("DONE"), _PRIMARY
                phase = tr("Auto-stop reached")
            else:
                word, color = tr("IDLE"), _DIM
                phase = tr("Idle")
        elif paused:
            word, color = tr("PAUSED"), _SECONDARY
            phase = tr(self._status_src, **self._status_kwargs)
        else:
            word, color = tr("ACTIVE"), _ROG
            phase = tr(self._status_src, **self._status_kwargs)
        if hasattr(self, "_dot"):
            self._dot.set_color(color)
        lg = getattr(self, "_logo_glow", None)
        if lg is not None:
            gc = _qc(color)
            gc.setAlpha(170)
            lg.setColor(gc)
            lg.setEnabled(color != _DIM)
        if getattr(self, "_gauge", None) is not None:
            self._gauge.set_word(word, color)
            if self._running or self._autostop_done:
                accent = color
            elif self._gauge_fraction() > 0.001:
                accent = _DIM
            else:
                accent = _TRACK
            self._gauge.set_accent(accent)
            self._gauge.set_fraction(self._gauge_fraction())
        if hasattr(self, "_phase_dot"):
            self._phase_dot.set_color(color)
        if hasattr(self, "_phase_lbl"):
            self._phase_lbl.setText(phase)
            self._phase_lbl.setStyleSheet(
                f"color:{color}; font-family:'Sora','Segoe UI'; font-size:{fs(13)}px;"
                "font-weight:bold; background:transparent;")
        self._set_button(self._running, paused)

    @QtCore.Slot(str, object)
    def _apply_status(self, msg, kwargs=None):
        self._status_src = msg
        self._status_kwargs = dict(kwargs or {})
        self._retint()

    @QtCore.Slot(bool)
    def _apply_running(self, running):
        was = self._running
        self._running = bool(running)
        self._active = self._running
        cfg = self._cfg
        auto = bool(getattr(cfg, "auto_stop_enabled", False)) if cfg else False
        try:
            maxc = max(1, int(getattr(cfg, "max_cars", 1)))
        except Exception:
            maxc = 1
        if self._running and not was:
            if self._autostop_done or not getattr(self, "_carry_valid", False):
                self._autostop_done = False
                self._bought_base = getattr(self, "_bought_total", 0)
                self._bought_n = 0
            self._started = time.monotonic()
            if getattr(self, "_gauge", None) is not None:
                self._gauge.set_time("00:00")
        elif was and not self._running:
            self._autostop_done = bool(auto and self._bought_n >= maxc)
            self._carry_valid = bool(auto and not self._autostop_done)
        self._retint()

    def _update_run_clock(self, running, paused):
        now = time.monotonic()
        counting = running and not paused
        if running and not self._was_running:
            self._elapsed_base = 0.0
            self._segment_start = now if counting else None
        elif not running:
            if self._segment_start is not None:
                self._elapsed_base += now - self._segment_start
                self._segment_start = None
        else:
            if counting and self._segment_start is None:
                self._segment_start = now
            elif not counting and self._segment_start is not None:
                self._elapsed_base += now - self._segment_start
                self._segment_start = None
        self._was_running = running

    def _active_seconds(self):
        total = self._elapsed_base
        if self._segment_start is not None:
            total += time.monotonic() - self._segment_start
        return int(total)

    def _tick(self):
        if not self._running or getattr(self, "_gauge", None) is None:
            return
        total = self._active_seconds()
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        if h > 0:
            self._gauge.set_time(f"{h:02d}:{m:02d}:{s:02d}")
        else:
            self._gauge.set_time(f"{m:02d}:{s:02d}")

    @QtCore.Slot(int, int, int)
    def _apply_stats(self, searches, bought, fails):
        bought = int(bought)
        if bought < getattr(self, "_bought_base", 0):
            self._bought_base = 0
        self._bought_total = bought
        self._bought_n = max(0, bought - getattr(self, "_bought_base", 0))
        self._value_labels["_searches"].setText(str(searches))
        self._value_labels["_bought"].setText(str(bought))
        self._value_labels["_fails"].setText(str(fails))
        if getattr(self, "_gauge", None) is not None:
            self._gauge.set_fraction(self._gauge_fraction())

    # ── Settings persistence ──────────────────────────────────────────────
    def _on_slider_change(self, label, v, is_int, key=None):
        label.setText(_fmt(v, is_int))
        self._autosave_soon()
        if key == "ui_scale":
            self._scale_soon(v)

    def _collect(self):
        out = {}
        for key, (kind, w) in self._setting_widgets.items():
            if kind == "range":
                out[key] = (kind, (w[0].get(), w[1].get()))
            elif kind == "text":
                out[key] = (kind, w.text())
            else:
                out[key] = (kind, w.get())
        return out

    @staticmethod
    def _apply_collected(cfg, collected):
        for key, (kind, val) in collected.items():
            if kind == "toggle":
                setattr(cfg, key, bool(val))
            elif kind == "slider":
                setattr(cfg, key, val)
            elif kind == "range":
                a, b = val
                lo, hi = (a, b) if a <= b else (b, a)
                setattr(cfg, key, (lo, hi))
            elif kind == "text":
                setattr(cfg, key, str(val).strip())
            elif kind == "color":
                setattr(cfg, key, str(val).strip())
            elif kind == "keybind":
                setattr(cfg, key, str(val).strip())
            elif kind == "dropdown":
                setattr(cfg, key, str(val))

    def _autosave(self):
        if self._cfg is None or not self._ready:
            return
        self._apply_collected(self._cfg, self._collect())
        if self._on_save:
            try:
                self._on_save(self._cfg)
            except Exception:
                pass
        if getattr(self, "_gauge", None) is not None:
            self._gauge.set_fraction(self._gauge_fraction())
        self._show_toast()

    def _on_keybind_captured(self, key, value):
        if self._cfg is not None:
            setattr(self._cfg, key, str(value))
        if self._on_save:
            try:
                self._on_save(self._cfg)
            except Exception:
                pass
        if self._on_hotkeys_changed:
            try:
                self._on_hotkeys_changed(self._cfg)
            except Exception:
                pass
        self._refresh_hotkey_hints()
        self._show_toast(tr("Bound: {label}", label=hotkey_label(value)))

    def set_hotkeys_changed(self, callback):
        self._on_hotkeys_changed = callback

    def set_game_language_changed(self, callback):
        self._on_game_lang_changed = callback

    def _on_game_language_changed(self, _code):
        self._autosave()
        if self._on_game_lang_changed:
            try:
                self._on_game_lang_changed(self._cfg)
            except Exception:
                logging.getLogger("fh6").exception(
                    "reload templates for game language failed")

    def _on_language_changed(self, code):
        if self._cfg is not None:
            setattr(self._cfg, "language", str(code))
        locales.set_language(str(code))
        if self._on_save:
            try:
                self._on_save(self._cfg)
            except Exception:
                pass
        self._rebuild_all()
        self._show_toast()

    def _on_keybind_capture_active(self, active):
        if self._on_capture_active:
            try:
                self._on_capture_active(bool(active))
            except Exception:
                logging.getLogger("fh6").exception(
                    "hotkey suspend/resume failed")

    def set_capture_active_cb(self, callback):
        self._on_capture_active = callback

    def _refresh_hotkey_hints(self):
        if self._cfg is None:
            return
        start = hotkey_label(getattr(self._cfg, "hotkey_start_stop", ""))
        panic = hotkey_label(getattr(self._cfg, "hotkey_panic", ""))
        lbl = None
        page = self._pages.get("status") if hasattr(self, "_pages") else None
        if page is not None:
            try:
                lbl = page.findChild(QtWidgets.QLabel, "hotkeyFooter")
            except Exception:
                lbl = None
        if lbl is None:
            lbl = getattr(self, "_hotkey_footer", None)
        if lbl is not None:
            try:
                lbl.setText(f"{start}  {tr('start / stop')}      \u00b7      "
                            f"{panic}  {tr('panic / quit')}")
            except Exception:
                pass

    def _autosave_soon(self, delay=450):
        if not self._ready:
            return
        if self._autosave_timer is None:
            self._autosave_timer = QTimer(self._win)
            self._autosave_timer.setSingleShot(True)
            self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start(delay)

    def _show_toast(self, text=None):
        if text is None:
            text = tr("Saved \u2713")
        self._toast.setText(text)
        self._toast.show()
        self._toast_timer.start(1300)

    # ── Live UI scale ─────────────────────────────────────────────────────
    def _scale_soon(self, value):
        if self._scale_timer is None:
            self._scale_timer = QTimer(self._win)
            self._scale_timer.setSingleShot(True)
            self._scale_timer.timeout.connect(self._do_scale)
        self._pending_scale = value
        self._scale_timer.start(300)

    def _do_scale(self):
        value = max(UI_SCALE_MIN, min(UI_SCALE_MAX, float(self._pending_scale)))
        if abs(value - _SCALE) < 1e-3:
            return
        if self._cfg is not None:
            setattr(self._cfg, "ui_scale", value)
        _set_scale(value)
        self._wide_h = None
        self._rebuild_all()

    def _rebuild_all(self):
        status_src = self._status_src
        status_kwargs = dict(self._status_kwargs)
        running = self._running
        page = self._page
        scroll_frac = 0.0
        old_scroll = getattr(self, "_settings_scroll", None)
        if old_scroll is not None:
            try:
                sb = old_scroll.verticalScrollBar()
                mx = sb.maximum()
                scroll_frac = (sb.value() / mx) if mx > 0 else 0.0
            except Exception:
                scroll_frac = 0.0
        old_layout = self._win.layout()
        if old_layout is not None:
            trash = QtWidgets.QWidget()
            trash.setLayout(old_layout)
            trash.deleteLater()
        self._settings_scroll = None
        self._setting_widgets = {}
        self._excl_group = {}
        self._sec_index = {}
        self._value_labels = {}
        self._page = page
        self._fixed_win_size = None
        self._build_ui()
        self._apply_running(running)
        self._apply_status(status_src, status_kwargs)
        if self._toggle_cb is not None:
            self._btn.set_command(self._toggle_cb)
        self._select_page(page, refit=False)
        self._apply_page_geometry()
        sc = getattr(self, "_settings_scroll", None)
        if page == "settings" and sc is not None and scroll_frac > 0:
            def _restore(s=sc, fr=scroll_frac):
                try:
                    bar = s.verticalScrollBar()
                    bar.setValue(int(round(fr * bar.maximum())))
                except Exception:
                    pass
            QTimer.singleShot(0, _restore)
        if self._color_popup is not None and self._color_popup.isVisible():
            self._color_popup.raise_()
        if self._on_save and self._cfg is not None:
            try:
                self._on_save(self._cfg)
            except Exception:
                pass

    # ── Live colour theme ─────────────────────────────────────────────────
    def _open_color_picker(self, key, button, default_hex):
        was_open_same = (self._color_popup is not None
                         and self._active_color_key == key)
        if self._color_popup is not None:
            try:
                self._color_popup._dismiss()
            except Exception:
                pass
            self._color_popup = None
            self._active_color_key = None
        if was_open_same:
            return
        self._active_color_key = key
        popup = ColorPickerPopup(
            button.get(), default_hex,
            on_change=lambda c, final, k=key: self._set_role_color(k, c, final),
            parent=self._win)
        self._color_popup = popup
        popup.destroyed.connect(lambda *_: self._clear_popup_ref(popup))
        popup.show_at(button)
        self._apply_capture_affinity(popup)

    def _clear_popup_ref(self, popup):
        if self._color_popup is popup:
            self._color_popup = None
            self._active_color_key = None

    def _set_role_color(self, key, qcolor, final):
        hexs = _color_to_hex(qcolor)
        if self._cfg is not None:
            setattr(self._cfg, key, hexs)
        _apply_theme_from_cfg(self._cfg)
        w = self._setting_widgets.get(key)
        if w and w[0] == "color":
            try:
                w[1].set_color(hexs)
            except Exception:
                pass
        if final:
            if self._theme_timer is not None:
                self._theme_timer.stop()
            self._rebuild_all()
            self._show_toast()
        else:
            self._theme_soon()

    def _theme_soon(self, delay=180):
        if self._theme_timer is None:
            self._theme_timer = QTimer(self._win)
            self._theme_timer.setSingleShot(True)
            self._theme_timer.timeout.connect(self._rebuild_all)
        self._theme_timer.start(delay)

    # ── Logs ────────────────────────────────────────────────────────────────
    @QtCore.Slot(str)
    def _add_log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self._logs.append((ts, str(msg)))
        if self._page != "logs" or not hasattr(self, "_log_text"):
            return
        flt = self._log_filter.text().strip().lower()
        if (flt or getattr(self, "_log_empty", False)
                or len(self._logs) >= self._logs.maxlen):
            self._render_logs()
        else:
            self._append_log_row(ts, str(msg))
            sb = self._log_text.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _log_color(self, msg):
        m = str(msg).lower()
        if m.startswith("run_once outcome:"):
            if "failed" in m:
                return _STATUSRED
            if "bought" in m:
                return _SUCCESS
            return _TEXT_2
        tech = ("wait {", "screen ->", "press ", "time:", "enter_search",
                "recover: reached", "loading templates", "capture worker",
                "results settle", "templates reloaded", "--- run_once")
        if any(t in m for t in tech):
            return _TEXT_2
        if "paused" in m or "pausa" in m:
            return _TEXT_2
        if "auto-stop" in m or "auto stop" in m:
            return _SUCCESS
        red_kw = ("fail", "fallit", "error", "errore", "crash",
                  "lost", "unable", "cannot", "can't", "non pu", "impossib",
                  "gave up", "stop", "ferm", "arrest", "halt")
        green_kw = ("bought", "acquist", "comprat", "success", "collect",
                    "raccolt", "start", "started", "avviat", "avvio",
                    "running")
        if any(k in m for k in red_kw):
            return _STATUSRED
        if any(k in m for k in green_kw):
            return _SUCCESS
        return _TEXT_2

    @staticmethod
    def _html_escape(s):
        return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;"))

    def _render_logs(self):
        if not hasattr(self, "_log_text"):
            return
        flt = self._log_filter.text().strip().lower()
        rows = list(self._logs)
        self._log_text.clear()
        self._log_empty = False
        if not rows:
            self._log_text.appendHtml(
                f"<span style='color:{_DIM}'>&nbsp;&nbsp;"
                f"{self._html_escape(tr('no events yet.'))}</span>")
            self._log_empty = True
            return
        for ts, msg in rows:
            if flt and flt not in f"{ts}  {msg}".lower():
                continue
            self._append_log_row(ts, msg)
        sb = self._log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _append_log_row(self, ts, msg):
        color = self._log_color(msg)
        self._log_text.appendHtml(
            f"<span style='color:{_DIM}'>{self._html_escape(ts)}</span>"
            f"&nbsp;&nbsp;"
            f"<span style='color:{color}'>{self._html_escape(msg)}</span>")

    def _copy_logs(self):
        text = "\n".join(f"{ts}  {msg}" for ts, msg in self._logs)
        QtWidgets.QApplication.clipboard().setText(text)

    # ── Windows: capture exclusion + rounded corners ──────────────────────
    def _hwnd(self):
        try:
            return int(self._win.winId())
        except Exception:
            return 0

    def _set_capturable(self, capturable):
        if not sys.platform.startswith("win"):
            return
        try:
            ctypes.windll.user32.SetWindowDisplayAffinity(
                self._hwnd(), 0x00 if capturable else 0x11)
        except Exception:
            pass

    def _exclude_from_capture(self):
        self._set_capturable(False)

    def _apply_capture_affinity(self, widget):
        if not sys.platform.startswith("win") or not self._hide_from_capture:
            return
        capturable = (bool(getattr(self._cfg, "overlay_capturable", False))
                      if self._cfg is not None else False)
        try:
            ctypes.windll.user32.SetWindowDisplayAffinity(
                int(widget.winId()), 0x00 if capturable else 0x11)
        except Exception:
            pass

    def _round_window_corners(self):
        if not sys.platform.startswith("win"):
            return
        try:
            hwnd = self._hwnd()
            pref = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, ctypes.byref(pref), ctypes.sizeof(pref))
            none_color = ctypes.c_uint(0xFFFFFFFE)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 34, ctypes.byref(none_color), ctypes.sizeof(none_color))
        except Exception:
            pass

    def _on_close_event(self, e):
        try:
            self._app.quit()
        except Exception:
            pass
        e.accept()

    # ── Public API (thread-safe) ──────────────────────────────────────────
    def set_status(self, msg, kwargs=None):
        self._bridge.status.emit(str(msg), dict(kwargs or {}))

    def set_running(self, running):
        self._bridge.running.emit(bool(running))

    def set_stats(self, searches, bought, fails):
        self._bridge.stats.emit(int(searches), int(bought), int(fails))

    def log(self, msg):
        self._bridge.logmsg.emit(str(msg))

    def attach_logging(self, logger=None, level=logging.INFO,
                       fmt="%(message)s"):
        handler = _OverlayLogHandler(self)
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(fmt))
        target = logger if logger is not None else logging.getLogger()
        target.addHandler(handler)
        self._log_handler = handler
        return handler

    def on_toggle(self, callback):
        self._toggle_cb = callback
        self._btn.set_command(callback)

    def set_stats_safe(self, *a):
        self.set_stats(*a)

    def run(self):
        self._win.show()
        if not self._hide_from_capture:
            self._set_capturable(True)
        else:
            self._exclude_from_capture()
        self._round_window_corners()
        QTimer.singleShot(0, lambda: self._apply_page_geometry(initial=True))
        self._app.exec()

    def close(self):
        try:
            self._win.close()
        except Exception:
            pass

    @QtCore.Slot()
    def _do_quit(self):
        try:
            self._win.close()
        except Exception:
            pass
        try:
            self._app.quit()
        except Exception:
            pass

    def request_close(self):
        self._bridge.quit.emit()