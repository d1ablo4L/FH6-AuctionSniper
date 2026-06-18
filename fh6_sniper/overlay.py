from __future__ import annotations
import collections
import ctypes
import logging
import time
import tkinter as tk
import webbrowser

# ── Palette ROG ─────────────────────────────────────────────────────────────
_BORDER   = "#FF0028"
_BG_HDR   = "#020000"
_BG       = "#080000"
_BG_MID   = "#0c0000"
_BG_BOT   = "#160000"
_CARD     = "#0e0000"
_NAV_BG   = "#050000"
_NAV_ACT  = "#170006"

_DIVIDER  = "#2a0000"
_ROG      = "#FF0028"
_ROG_DIM  = "#c40020"
_TEXT     = "#f4f4f6"
_DIM      = "#7a3535"
_FAINT    = "#7a3535"
_AMBER    = "#f0a83c"
_RED_STAT = "#ff4060"
_STOP     = "#b80000"
_STOP_HV  = "#8f0000"
_START_HV = "#cc001e"
_TRACK    = "#3a2222"

# Try: buttons in the rectangle (card) color with ROG text
_BTN_BG   = _CARD
_BTN_HV   = "#2b0005"
_BTN_FG   = _ROG

# Italian flag colors (title + top strip)
_IT_GREEN = "#1aa64b"
_IT_WHITE = "#ffffff"
_IT_RED   = "#e23744"

# ── Geometry ────────────────────────────────────────────────────────────────
UI_SHRINK = 0.8
SIDEBAR_W = round(56 * UI_SHRINK)
CONTENT_W = round(414 * UI_SHRINK)
PAD       = round(18 * UI_SHRINK)
WIDTH     = SIDEBAR_W + CONTENT_W + 2
WIDE_W    = round(800 * 0.9 * UI_SHRINK)
SETTINGS_NAVW = round(184 * UI_SHRINK)
SETTINGS_CTRL_W = round(270 * UI_SHRINK)
SIDEBAR_LABEL_W = round(142 * UI_SHRINK)
SIDEBAR_WIDE_W  = SIDEBAR_W + SIDEBAR_LABEL_W
NAV_ITEM_H = round(48 * UI_SHRINK)
NAV_SUB_H  = round(42 * UI_SHRINK)
NAV_TOP_Y  = round(18 * UI_SHRINK)
UI_SCALING = round(1.3333 * UI_SHRINK, 4)

# ── Settings menu spec ──────────────────────────────────────────
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
     "desc": "How strongly the SOLD stamp must match to skip a sold car. Lower if sold cars slip through; higher if it wrongly marks cars as sold. Recommended ~0.70."},

    ("section", "Match buy"),
    {"key": "match_threshold_auction_options", "label": "Match: Auction options", "kind": "slider",
     "lo": 0.50, "hi": 0.95, "step": 0.01, "int": False,
     "desc": "Threshold for the auction options menu. Recommended ~0.80 (matches strong)."},
    {"key": "match_threshold_player_options", "label": "Match: Player options", "kind": "slider",
     "lo": 0.50, "hi": 0.95, "step": 0.01, "int": False,
     "desc": "Threshold for your own listing menu (sold cars). Recommended ~0.80 (matches strong)."},
    {"key": "match_threshold_buy_out", "label": "Match: Buy Out", "kind": "slider",
     "lo": 0.50, "hi": 0.95, "step": 0.01, "int": False,
     "desc": "Threshold for the Buy Out confirm screen. Moving background = matches WEAK, recommended ~0.60. Higher makes the buyout stall."},
    {"key": "match_threshold_buyout_progress", "label": "Match: Buyout progress", "kind": "slider",
     "lo": 0.50, "hi": 0.95, "step": 0.01, "int": False,
     "desc": "Threshold for the buyout 'in progress' screen. Moving background = matches WEAK, recommended ~0.60."},

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
     "desc": "Before every search, nudges Max Bid by \u00b11 (moves up 2 rows) to refresh the list and avoid already-sold cars. Turning this on switches off Max Buyout."},
    {"key": "jitter_maxbuyout", "label": "Update Max Buyout", "kind": "toggle",
     "exclusive_group": "jitter_field",
     "desc": "Same as above but acts on Max Buyout (moves up 1 row). Turning this on switches off Max Bid. If both are off, the price is not updated."},
    {"key": "collect_after_buyout", "label": "Collect after buyout", "kind": "toggle",
     "desc": "Immediately collects the car you bought (slower but automatic)."},
    {"key": "notify_sound", "label": "Notification sound", "kind": "toggle",
     "desc": "Windows beep on every successful purchase."},
    {"key": "notify_toast", "label": "Windows notification", "kind": "toggle",
     "desc": "Windows toast notification on every purchase."},
    {"key": "overlay_capturable", "label": "Show overlay in captures", "kind": "toggle",
     "desc": "Turn this on ONLY to take screenshots: with this on the overlay becomes visible in captures/screenshots, but it may cover the screen areas the tool reads to work. Keep it off while the sniper is running."},

    ("section", "Safety"),
    {"key": "timeout_results_s", "label": "Results timeout (s)", "kind": "slider",
     "lo": 2, "hi": 30, "step": 0.5, "int": False,
     "desc": "Maximum wait for results after a search."},
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

    ("section", "Key bindings"),
    {"key": "hotkey_start_stop", "label": "Start/stop key", "kind": "text",
     "desc": "Global shortcut, pynput format (e.g. <f8>). Requires restart."},
    {"key": "hotkey_panic", "label": "Panic key", "kind": "text",
     "desc": "Global immediate-stop shortcut (e.g. <f9>). Requires restart."},
]


SECTION_GROUPS = {"Match": ["Match search", "Match buy", "Match collect"]}
_CHILD_TO_GROUP = {c: g for g, cs in SECTION_GROUPS.items() for c in cs}


def _child_label(name: str) -> str:
    for g in SECTION_GROUPS:
        if name.startswith(g + " "):
            return name[len(g) + 1:].capitalize()
    return name


# ── Pure helpers (testable without tkinter) ─────────────────────────────────────
def _slider_value_from_x(x, track_x0, track_w, lo, hi, step, is_int):
    frac = 0.0 if track_w <= 0 else (x - track_x0) / track_w
    frac = max(0.0, min(1.0, frac))
    val = lo + frac * (hi - lo)
    val = round((val - lo) / step) * step + lo
    val = max(lo, min(hi, val))
    return int(round(val)) if is_int else round(val, 4)


def _slider_x_from_value(val, track_x0, track_w, lo, hi):
    frac = 0.0 if hi == lo else (val - lo) / (hi - lo)
    frac = max(0.0, min(1.0, frac))
    return track_x0 + frac * track_w


def _fmt(val, is_int):
    if is_int:
        return str(int(round(val)))
    return f"{val:.2f}".rstrip("0").rstrip(".")


def _blend(c1, c2, t):
    t = max(0.0, min(1.0, t))
    a = (int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16))
    b = (int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16))
    m = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return "#%02x%02x%02x" % m


def _round_pts(x1, y1, x2, y2, r):
    return [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]


# ── Widget: round toggle ────────────────────────────────────────────────────
class ToggleSwitch(tk.Canvas):
    W, H = round(46 * UI_SHRINK), round(26 * UI_SHRINK)

    def __init__(self, parent, value=False, command=None, bg=_BG):
        super().__init__(parent, width=self.W, height=self.H, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._value = bool(value)
        self._command = command
        self._bg = bg
        self._photo = None
        self._cache = {}
        self.bind("<Button-1>", self._on_click)
        self._draw()

    def _on_click(self, _e=None):
        self._value = not self._value
        self._draw()
        if self._command:
            self._command(self._value)

    def get(self):
        return self._value

    def set(self, v):
        self._value = bool(v)
        self._draw()

    def _draw(self):
        self.delete("all")
        track = _ROG if self._value else _TRACK
        key = (self._value, track, self._bg)
        img = self._cache.get(key)
        if img is None:
            img = self._render_aa(track)
            if img is not None:
                self._cache[key] = img
        if img is not None:
            self._photo = img
            self.create_image(self.W / 2, self.H / 2, image=img)
            return
        self._draw_canvas(track)

    def _render_aa(self, track):
        try:
            import cv2
            import numpy as np
        except Exception:
            return None
        tb, bb, wb = _hex_bgr(track), _hex_bgr(self._bg), _hex_bgr("#ffffff")
        if tb is None or bb is None or wb is None:
            return None
        try:
            ss = 4
            W, H = self.W, self.H
            Wp, Hp = W * ss, H * ss
            img = np.empty((Hp, Wp, 3), dtype=np.uint8)
            img[:] = bb
            tb = (int(tb[0]), int(tb[1]), int(tb[2]))
            r = Hp // 2
            cv2.rectangle(img, (r, 0), (Wp - r, Hp), tb, -1)
            cv2.circle(img, (r, r), r, tb, -1, cv2.LINE_AA)
            cv2.circle(img, (Wp - r - 1, r), r, tb, -1, cv2.LINE_AA)
            m = 3 * ss
            d = Hp - 2 * m
            kr = d // 2
            kx = (Wp - m - kr) if self._value else (m + kr)
            cv2.circle(img, (int(kx), int(r)), int(kr),
                       (int(wb[0]), int(wb[1]), int(wb[2])), -1, cv2.LINE_AA)
            small = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)
            return _photo_from_bgr(small, self)
        except Exception:
            return None

    def _draw_canvas(self, track):
        W, H = self.W, self.H
        r = H / 2
        self.create_oval(0, 0, H, H, fill=track, outline="")
        self.create_oval(W - H, 0, W, H, fill=track, outline="")
        self.create_rectangle(r, 0, W - r, H, fill=track, outline="")
        m = 3
        d = H - 2 * m
        kx = (W - d - m) if self._value else m
        self.create_oval(kx, m, kx + d, m + d, fill="#ffffff", outline="")


# ── Widget: modern slider ────────────────────────────────────────────────────
class Slider(tk.Canvas):
    H = round(26 * UI_SHRINK)
    KNOB = round(17 * UI_SHRINK)
    TRACK_W = round(7 * UI_SHRINK)

    def __init__(self, parent, value, lo, hi, step, is_int,
                 width=round(150 * UI_SHRINK), bg=_BG, on_change=None):
        super().__init__(parent, width=width, height=self.H, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._lo, self._hi, self._step, self._int = lo, hi, step, is_int
        self._x0 = self.KNOB // 2 + 1
        self._tw = width - self.KNOB - 2
        self._value = self._coerce(value)
        self._on_change = on_change
        self._bg = bg
        self._knob_img = None
        self.bind("<Button-1>", self._drag)
        self.bind("<B1-Motion>", self._drag)
        self._draw()

    def _coerce(self, v):
        v = max(self._lo, min(self._hi, v))
        return int(round(v)) if self._int else round(v, 4)

    def get(self):
        return self._value

    def _drag(self, e):
        self._value = _slider_value_from_x(
            e.x, self._x0, self._tw, self._lo, self._hi, self._step, self._int)
        self._draw()
        if self._on_change:
            self._on_change(self._value)

    def _draw(self):
        self.delete("all")
        cy = self.H // 2
        self.create_line(self._x0, cy, self._x0 + self._tw, cy,
                         fill=_TRACK, width=self.TRACK_W, capstyle="round")
        kx = _slider_x_from_value(self._value, self._x0, self._tw,
                                  self._lo, self._hi)
        self.create_line(self._x0, cy, kx, cy, fill=_ROG,
                         width=self.TRACK_W, capstyle="round")
        img = _aa_circle_photo(self.KNOB, _ROG, self._bg, master=self)
        if img is not None:
            self._knob_img = img
            self.create_image(int(kx), cy, image=img)
        else:
            r = self.KNOB / 2
            self.create_oval(kx - r, cy - r, kx + r, cy + r,
                             fill=_ROG, outline="")


# ── Widget: animated state bar (smooth scrolling gradient) ──────────────
class StateBar(tk.Canvas):
    H = round(10 * UI_SHRINK)
    BAND = round(230 * UI_SHRINK)
    SPEED = max(4, round(7 * UI_SHRINK))
    FPS_MS = 33

    def __init__(self, parent, width, bg=_BG):
        super().__init__(parent, width=width, height=self.H, bg=bg,
                         highlightthickness=0, bd=0)
        self._cw = int(width)
        self._bg = bg
        self._state = "idle"
        self._accent = _ROG
        self._anim_id = None
        self._alive = True
        self._x = -self.BAND
        self._photo = None
        self._item = None
        self._np_ok = self._prep()

    def _prep(self):
        try:
            import cv2
            import numpy as np
        except Exception:
            return False
        bm, mm = _hex_bgr(self._bg), _hex_bgr(_BG_MID)
        if bm is None or mm is None:
            return False
        try:
            ss = 4
            W, H = self._cw, self.H
            big = np.zeros((H * ss, W * ss), dtype=np.uint8)
            r = (H * ss) // 2
            cv2.rectangle(big, (r, 0), (W * ss - r, H * ss), 255, -1)
            cv2.rectangle(big, (0, r), (W * ss, H * ss - r), 255, -1)
            for cx, cy in ((r, r), (W * ss - r - 1, r),
                           (r, H * ss - r - 1), (W * ss - r - 1, H * ss - r - 1)):
                cv2.circle(big, (cx, cy), r, 255, -1, cv2.LINE_AA)
            alpha = (cv2.resize(big, (W, H), interpolation=cv2.INTER_AREA)
                     .astype(np.float32) / 255.0)
            self._alpha = alpha[..., None]               # H x W x 1
            self._bg_arr = np.array(bm, dtype=np.float32)
            self._mid_arr = np.array(mm, dtype=np.float32)
            self._np = np
            return True
        except Exception:
            return False

    def set_state(self, state):
        if state == self._state:
            return
        self._state = state
        if self._anim_id is not None:
            try:
                self.after_cancel(self._anim_id)
            except Exception:
                pass
            self._anim_id = None
        if state in ("running", "paused"):
            self._accent = _ROG if state == "running" else _AMBER
            self._x = -self.BAND
            self._tickanim()
        else:
            # Idle: invisible bar (disappears).
            self.delete("all")
            self._item = None
            self._photo = None

    def _render(self, gx):
        np = self._np
        W, H = self._cw, self.H
        xs = np.arange(W, dtype=np.float32)
        t = (xs - gx) / float(self.BAND)
        inten = np.clip(1.0 - np.abs(t - 0.5) * 2.0, 0.0, 1.0) ** 1.7
        inten = np.where((t >= 0.0) & (t <= 1.0), inten, 0.0)
        acc = np.array(_hex_bgr(self._accent), dtype=np.float32)
        fill = (self._mid_arr[None, :] * (1.0 - inten[:, None])
                + acc[None, :] * inten[:, None])
        fill = np.repeat(fill[None, :, :], H, axis=0)
        out = (self._bg_arr[None, None, :] * (1.0 - self._alpha)
               + fill * self._alpha)
        out = out.clip(0, 255).astype(np.uint8)[..., ::-1]
        rows = []
        for y in range(H):
            ln = out[y]
            rows.append("{" + " ".join(
                "#%02x%02x%02x" % (int(p[0]), int(p[1]), int(p[2])) for p in ln)
                + "}")
        if self._photo is None:
            self._photo = tk.PhotoImage(master=self, width=W, height=H)
            self._item = self.create_image(0, 0, anchor="nw",
                                           image=self._photo)
        self._photo.put(" ".join(rows))

    def _tickanim(self):
        if not self._alive or self._state not in ("running", "paused"):
            return
        if not self._np_ok:
            self.delete("all")
            self.create_rectangle(0, 0, self._cw, self.H,
                                  fill=self._accent, outline="")
            return
        try:
            self._render(self._x)
        except Exception:
            pass
        self._x += self.SPEED
        if self._x > self._cw:
            self._x = -self.BAND
        self._anim_id = self.after(self.FPS_MS, self._tickanim)

    def destroy(self):
        self._alive = False
        if self._anim_id is not None:
            try:
                self.after_cancel(self._anim_id)
            except Exception:
                pass
        super().destroy()


# ── Widget: rounded pill button ────────────────────────────────────
class PillButton(tk.Canvas):
    def __init__(self, parent, text, command=None, width=round(360 * UI_SHRINK), height=round(46 * UI_SHRINK),
                 bg=_BG_MID, base=_ROG, hover=_START_HV, fg="#ffffff"):
        super().__init__(parent, width=width, height=height, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._cw, self._ch = width, height
        self._text = text
        self._base, self._hover, self._fg = base, hover, fg
        self._cur = base
        self._command = command
        self._anim_id = None
        self._alive = True
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", lambda _e: self._set_color(self._hover))
        self.bind("<Leave>", lambda _e: self._set_color(self._base))
        self._draw()

    def _click(self, _e=None):
        if self._command:
            self._command()

    def set_command(self, cmd):
        self._command = cmd

    def set_mode(self, text, base, hover, fg="#ffffff"):
        prev = self._base
        self._text, self._base, self._hover, self._fg = text, base, hover, fg
        self._pulse(prev, base)

    def _set_color(self, c):
        self._cur = c
        self._draw()

    def _pulse(self, c_from, c_to, n=8, i=0):
        if not self._alive:
            return
        t = i / n
        self._cur = _blend(c_from, c_to, t)
        self._draw()
        if i < n:
            try:
                self._anim_id = self.after(18, self._pulse, c_from, c_to, n, i + 1)
            except RuntimeError:
                pass

    def _draw(self):
        self.delete("all")
        r = self._ch / 2
        pts = _round_pts(1, 1, self._cw - 1, self._ch - 1, r)
        self.create_polygon(pts, smooth=True, fill=self._cur, outline="")
        self.create_text(self._cw / 2, self._ch / 2, text=self._text,
                         fill=self._fg, font=("Segoe UI", 13, "bold"))

    def destroy(self):
        self._alive = False
        super().destroy()


# ── Widget: uniform-size vector icon ───────────────────────────
def _hex_bgr(color):
    c = str(color).lstrip("#")
    if len(c) != 6:
        return None
    try:
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    except ValueError:
        return None
    return (b, g, r)


# ── Shared anti-aliasing (cv2): crisp shapes, no Tk jaggies ───────
_AA_CACHE = {}


def _photo_from_bgr(bgr, master=None):
    import cv2
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    rows = []
    for yy in range(h):
        ln = rgb[yy]
        rows.append("{" + " ".join(
            "#%02x%02x%02x" % (int(ln[xx][0]), int(ln[xx][1]), int(ln[xx][2]))
            for xx in range(w)) + "}")
    photo = (tk.PhotoImage(width=w, height=h, master=master)
             if master is not None else tk.PhotoImage(width=w, height=h))
    photo.put(" ".join(rows))
    return photo


def _aa_rrect_photo(w, h, radius, fill, bg, master=None, ss=4):
    w, h, radius = int(w), int(h), int(radius)
    if w < 1 or h < 1:
        return None
    key = ("rr", w, h, radius, fill, bg)
    if key in _AA_CACHE:
        return _AA_CACHE[key]
    try:
        import cv2
        import numpy as np
    except Exception:
        return None
    f = _hex_bgr(fill)
    b = _hex_bgr(bg)
    if f is None or b is None:
        return None
    try:
        W, H = w * ss, h * ss
        R = min(int(radius * ss), W // 2, H // 2)
        img = np.empty((H, W, 3), dtype=np.uint8)
        img[:] = b
        f = (int(f[0]), int(f[1]), int(f[2]))
        if R <= 0:
            cv2.rectangle(img, (0, 0), (W, H), f, -1)
        else:
            cv2.rectangle(img, (R, 0), (W - R, H), f, -1)
            cv2.rectangle(img, (0, R), (W, H - R), f, -1)
            for cx, cy in ((R, R), (W - R - 1, R),
                           (R, H - R - 1), (W - R - 1, H - R - 1)):
                cv2.circle(img, (cx, cy), R, f, -1, cv2.LINE_AA)
        small = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA)
        photo = _photo_from_bgr(small, master)
        _AA_CACHE[key] = photo
        return photo
    except Exception:
        return None


def _aa_circle_photo(d, fill, bg, master=None, ss=4):
    d = int(d)
    if d < 1:
        return None
    key = ("ci", d, fill, bg)
    if key in _AA_CACHE:
        return _AA_CACHE[key]
    try:
        import cv2
        import numpy as np
    except Exception:
        return None
    f = _hex_bgr(fill)
    b = _hex_bgr(bg)
    if f is None or b is None:
        return None
    try:
        D = d * ss
        img = np.empty((D, D, 3), dtype=np.uint8)
        img[:] = b
        cv2.circle(img, (D // 2, D // 2), D // 2 - max(1, ss),
                   (int(f[0]), int(f[1]), int(f[2])), -1, cv2.LINE_AA)
        small = cv2.resize(img, (d, d), interpolation=cv2.INTER_AREA)
        photo = _photo_from_bgr(small, master)
        _AA_CACHE[key] = photo
        return photo
    except Exception:
        return None


class Icon(tk.Canvas):
    SIZE = 26
    _SS = 6

    def __init__(self, parent, name, color=_DIM, bg=_NAV_BG, size=None,
                 cursor="hand2"):
        s = size or self.SIZE
        super().__init__(parent, width=s, height=s, bg=bg,
                         highlightthickness=0, bd=0, cursor=cursor)
        self._name = name
        self._size = s
        self._bg = bg
        self._color = color
        self._photo = None
        self._cache = {}
        self._draw()

    def set_color(self, color, bg=None):
        self._color = color
        if bg is not None:
            self._bg = bg
            self.config(bg=bg)
        self._draw()

    def _draw(self):
        self.delete("all")
        key = (self._color, self._bg)
        img = self._cache.get(key)
        if img is None:
            img = self._render_aa()
            if img is not None:
                self._cache[key] = img
        if img is not None:
            self._photo = img
            self.create_image(self._size / 2, self._size / 2, image=img)
            if self._name in ("help", "about"):
                ch = "?" if self._name == "help" else "i"
                self.create_text(self._size / 2, self._size / 2 + 1, text=ch,
                                 fill=self._color,
                                 font=("Segoe UI", int(self._size * 0.5), "bold"))
            return
        self._draw_canvas()

    def _render_aa(self):
        try:
            import cv2
            import numpy as np
        except Exception:
            return None
        try:
            col3 = _hex_bgr(self._color)
            bg3 = _hex_bgr(self._bg)
            if col3 is None or bg3 is None:
                return None
            col = (int(col3[0]), int(col3[1]), int(col3[2]))
            bgc = (int(bg3[0]), int(bg3[1]), int(bg3[2]))
            ss = self._SS
            s = self._size
            S = s * ss
            img = np.empty((S, S, 3), dtype=np.uint8)
            img[:] = bgc
            lw = max(1, round(2 * ss))
            m = 4 * ss
            a, b = m, S - m
            cx = cy = S / 2
            AA = cv2.LINE_AA
            name = self._name
            if name == "status":
                cv2.circle(img, (int(cx), int(cy)), int((b - a) / 2), col, lw, AA)
                ext = 2.6 * ss
                cv2.line(img, (int(cx), int(a - ext)),
                         (int(cx), int(b + ext)), col, lw, AA)
                cv2.line(img, (int(a - ext), int(cy)),
                         (int(b + ext), int(cy)), col, lw, AA)
                cv2.circle(img, (int(cx), int(cy)), int(1.9 * ss), col, -1, AA)
            elif name == "settings":
                ys = (m + 2 * ss, cy, b - 2 * ss)
                knobs = (b - 5 * ss, a + 5 * ss, cx + 2 * ss)
                for y, kx in zip(ys, knobs):
                    cv2.line(img, (int(a), int(y)), (int(b), int(y)), col, lw, AA)
                    cv2.circle(img, (int(kx), int(y)), int(2.6 * ss), bgc, -1, AA)
                    cv2.circle(img, (int(kx), int(y)), int(2.6 * ss), col, lw, AA)
            elif name == "logs":
                for y in (m + 2 * ss, cy, b - 2 * ss):
                    cv2.line(img, (int(a), int(y)), (int(b), int(y)), col, lw, AA)
            elif name in ("help", "about"):
                cv2.circle(img, (int(cx), int(cy)), int((b - a) / 2), col, lw, AA)
            else:
                return None
            small = cv2.resize(img, (s, s), interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            rows = []
            for yy in range(s):
                line = rgb[yy]
                rows.append("{" + " ".join(
                    "#%02x%02x%02x" % (int(line[xx][0]), int(line[xx][1]),
                                       int(line[xx][2]))
                    for xx in range(s)) + "}")
            photo = tk.PhotoImage(width=s, height=s)
            photo.put(" ".join(rows))
            return photo
        except Exception:
            return None

    def _draw_canvas(self):
        s = self._size
        c = self._color
        lw = 2
        m = 4
        a, b = m, s - m
        cx = cy = s / 2
        name = self._name
        if name == "status":
            self.create_oval(a, a, b, b, outline=c, width=lw)
            ext = 2.6
            self.create_line(cx, a - ext, cx, b + ext, fill=c, width=lw,
                             capstyle="round")
            self.create_line(a - ext, cy, b + ext, cy, fill=c, width=lw,
                             capstyle="round")
            self.create_oval(cx - 1.9, cy - 1.9, cx + 1.9, cy + 1.9,
                             fill=c, outline="")
        elif name == "settings":
            ys = (m + 2, cy, b - 2)
            knobs = (b - 5, a + 5, cx + 2)
            for y, kx in zip(ys, knobs):
                self.create_line(a, y, b, y, fill=c, width=lw,
                                 capstyle="round")
                self.create_oval(kx - 2.6, y - 2.6, kx + 2.6, y + 2.6,
                                 fill=self._bg, outline=c, width=lw)
        elif name == "logs":
            for y in (m + 2, cy, b - 2):
                self.create_line(a, y, b, y, fill=c, width=lw,
                                 capstyle="round")
        elif name in ("help", "about"):
            self.create_oval(a, a, b, b, outline=c, width=lw)
            ch = "?" if name == "help" else "i"
            self.create_text(cx, cy + 1, text=ch, fill=c,
                             font=("Segoe UI", int(s * 0.5), "bold"))


# ── Widget: rounded-corner panel (hosts other widgets) ─────────────
class RoundedPanel(tk.Canvas):
    def __init__(self, parent, width=round(10 * UI_SHRINK), height=round(10 * UI_SHRINK), radius=round(14 * UI_SHRINK),
                 fill=_CARD, bg=_BG, pad=10):
        super().__init__(parent, width=width, height=height, bg=bg,
                         highlightthickness=0, bd=0)
        self._radius = radius
        self._fill = fill
        self._pad = pad
        self._bg = bg
        self._bg_img = None
        self.inner = tk.Frame(self, bg=fill)
        self._win = self.create_window(pad, pad, window=self.inner, anchor="nw")
        self.bind("<Configure>", self._on_cfg)

    def _on_cfg(self, e):
        self.delete("bg")
        img = _aa_rrect_photo(e.width, e.height, self._radius, self._fill,
                              self._bg, master=self)
        if img is not None:
            self._bg_img = img
            self.create_image(0, 0, anchor="nw", image=img, tags="bg")
        else:
            pts = _round_pts(1, 1, e.width - 1, e.height - 1, self._radius)
            self.create_polygon(pts, smooth=True, fill=self._fill,
                                outline="", tags="bg")
        self.tag_lower("bg")
        p = self._pad
        self.itemconfig(self._win, width=max(1, e.width - 2 * p),
                        height=max(1, e.height - 2 * p))


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


class Overlay:

    NAV = [
        ("status",   "status",   "Status"),
        ("settings", "settings", "Settings"),
        ("logs",     "logs",     "Logs"),
        ("help",     "help",     "Help"),
        ("about",    "about",    "Info"),
    ]

    def __init__(self, cfg=None, on_save=None, hide_from_capture: bool = True):
        _AA_CACHE.clear()
        self._cfg = cfg
        self._on_save = on_save
        self._page = "status"
        self._compact_w = WIDTH
        self._wide_w = WIDE_W + SIDEBAR_LABEL_W
        self._cur_w = WIDTH
        self._w = WIDTH
        self._cw = CONTENT_W
        self._scw = WIDE_W - SIDEBAR_W - 2
        self._sb_w = SIDEBAR_W
        self._setting_widgets = {}
        self._toggle_group = {}
        self._sec_frames = {}
        self._sec_nav = {}
        self._cur_section = None
        self._sec_sidebar = {}
        self._group_sidebar = {}
        self._sidebar_entries = []
        self._group_expanded = {g: False for g in SECTION_GROUPS}
        self._section_names = []
        self._sb_wide = False
        self._sec_expanded = False
        self._align_retry_id = None
        self._status_h = 300
        self._tall_h = 300
        self._settings_sub = None
        self._autosave_id = None
        self._toast = None
        self._toast_id = None
        self._nav = {}
        self._pages = {}
        self._logs = collections.deque(maxlen=300)
        self._ready = False
        self._resize_anim_id = None
        self._holder_w = CONTENT_W
        self._first_resize_done = False

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

        self.root = tk.Tk()
        try:
            self.root.tk.call("tk", "scaling", UI_SCALING)
        except Exception:
            pass
        self.root.withdraw()
        self.root.title("AuctionSniper - V.2")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.configure(bg=_BG)
        self._phase_var    = tk.StringVar(value="IDLE")
        self._status_var   = tk.StringVar(value="ready to start")
        self._bought_var   = tk.StringVar(value="0")
        self._searches_var = tk.StringVar(value="0")
        self._fails_var    = tk.StringVar(value="0")
        self._time_var     = tk.StringVar(value="00:00")
        self._active  = False
        self._started = None
        self._running = False
        self._drag    = (0, 0)
        self._bar     = None
        self._dot_id  = None
        self._build()
        self._pages["status"].pack(fill="both", expand=True)
        self.root.update_idletasks()
        status_h = max(self._pages["status"].winfo_reqheight(), 300)
        self._pages["status"].pack_forget()
        self._status_h = status_h
        self._area_h = status_h
        self._content.configure(width=CONTENT_W, height=status_h)
        self._content.pack_propagate(False)
        self._holder.place(x=0, y=0, width=CONTENT_W, height=status_h)

        tall = status_h
        sp = self._pages.get("settings")
        if sp is not None and self._section_names:
            sp.pack(fill="both", expand=True)
            for _name in self._section_names:
                self._show_section(_name)
                self.root.update_idletasks()
                tall = max(tall, sp.winfo_reqheight())
            sp.pack_forget()
        for _k in ("logs", "help", "about"):
            _pg = self._pages.get(_k)
            if _pg is None:
                continue
            _pg.pack(fill="both", expand=True)
            self.root.update_idletasks()
            tall = max(tall, _pg.winfo_reqheight())
            _pg.pack_forget()
        _n_main = len([k for k, _i, _l in self.NAV
                       if not (k == "settings" and self._cfg is None)])
        _n_sub = len(self._section_names) + len(SECTION_GROUPS)
        _sidebar_need = (NAV_TOP_Y + _n_main * NAV_ITEM_H
                         + _n_sub * NAV_SUB_H + round(24 * UI_SHRINK))
        _bottom_margin = round(34 * UI_SHRINK)
        self._tall_h = max(tall + _bottom_margin, _sidebar_need, status_h)
        self._cur_section = (self._section_names[0]
                             if self._section_names else None)

        self._layout_sidebar()

        self._show_page("status")
        self.root.update_idletasks()
        h = self.root.winfo_reqheight()
        margin = 24
        x = self.root.winfo_screenwidth() - self._w - margin

        for _ww in (self._wide_w, self._compact_w):
            try:
                self.root.geometry(f"{_ww}x{h}+{x}+{margin}")
                self.root.update_idletasks()
            except Exception:
                pass

        self.root.geometry(f"{self._w}x{h}+{x}+{margin}")
        self.root.update_idletasks()
        self.root.deiconify()
        try:
            self.root.update()
        except Exception:
            pass
        self._layout_sidebar()
        if hide_from_capture:
            self._exclude_from_capture()
        self._round_window_corners()
        self._ready = True
        self.root.after(60, self._retry_align)
        self._tick()

    # ── Exclude from capture ──────────────────────────────────────────────
    def _exclude_from_capture(self):
        try:
            user32 = ctypes.windll.user32
            hwnd   = self.root.winfo_id()
            parent = user32.GetParent(hwnd)
            while parent:
                hwnd   = parent
                parent = user32.GetParent(hwnd)
            user32.SetWindowDisplayAffinity(hwnd, 0x11)
        except Exception:
            pass

    def _set_capturable(self, capturable):
        try:
            user32 = ctypes.windll.user32
            hwnd   = self.root.winfo_id()
            parent = user32.GetParent(hwnd)
            while parent:
                hwnd   = parent
                parent = user32.GetParent(hwnd)
            user32.SetWindowDisplayAffinity(hwnd, 0x00 if capturable else 0x11)
        except Exception:
            pass

    # ── Rounded corners (Windows 11) ────────────────────────────────────
    def _round_window_corners(self):
        try:
            user32 = ctypes.windll.user32
            hwnd = self.root.winfo_id()
            parent = user32.GetParent(hwnd)
            while parent:
                hwnd = parent
                parent = user32.GetParent(hwnd)
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = 2
            val = ctypes.c_int(DWMWCP_ROUND)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(val), ctypes.sizeof(val))
        except Exception:
            pass
    def _build(self):
        inner = tk.Frame(self.root, bg=_BG_HDR)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        self._inner = inner
        self._curtain = tk.Frame(self.root, bg=_BG)
        _cflag = tk.Frame(self._curtain, bg=_ROG, height=3)
        _cflag.pack(fill="x")

        flag = tk.Frame(inner, bg=_ROG, height=3)
        flag.pack(fill="x")

        # Header full width
        header = tk.Frame(inner, bg=_BG_HDR)
        header.pack(fill="x", padx=16, pady=(11, 0))
        self._header = header

        self._dot = Icon(header, "status", color=_DIM, bg=_BG_HDR, size=24,
                         cursor="")
        self._dot.pack(side="left", pady=(0, 1))

        title_frame = tk.Frame(header, bg=_BG_HDR)
        title_frame.pack(side="left", padx=(6, 0))
        title_labels = []
        for chunk, color in (("Auction", _DIM),
                             ("Sniper",  _ROG)):
            lbl = tk.Label(title_frame, text=chunk, bg=_BG_HDR, fg=color,
                           font=("Segoe UI", 12, "bold"),
                           bd=0, padx=0, pady=0, highlightthickness=0)
            lbl.pack(side="left")
            title_labels.append(lbl)

        bw, bh = round(30 * UI_SHRINK), round(18 * UI_SHRINK)
        badge = tk.Canvas(header, width=bw, height=bh, bg=_BG_HDR,
                          highlightthickness=0, bd=0)
        badge.create_polygon(
            _round_pts(1, 1, bw - 1, bh - 1, round(6 * UI_SHRINK)),
            smooth=True, fill=_ROG, outline="")
        badge.create_text(bw / 2, bh / 2, text="V2", fill="#ffffff",
                          font=("Segoe UI", 8, "bold"))
        badge.pack(side="left", padx=(8, 0))

        close = tk.Label(header, text="\u2715", bg=_BG_HDR, fg=_DIM,
                         font=("Segoe UI", 15), cursor="hand2")
        close.pack(side="right")
        close.bind("<Button-1>", lambda _e: self.root.destroy())
        close.bind("<Enter>", lambda _e: close.config(fg=_ROG))
        close.bind("<Leave>", lambda _e: close.config(fg=_DIM))

        for w in (header, self._dot, title_frame, inner, badge,
                  *title_labels):
            w.bind("<Button-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)

        tk.Frame(inner, bg=_DIVIDER, height=1).pack(fill="x", pady=(11, 0))

        main = tk.Frame(inner, bg=_BG)
        main.pack(fill="both", expand=True)

        self._sidebar = tk.Frame(main, bg=_NAV_BG, width=SIDEBAR_W)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)
        self._build_sidebar(self._sidebar)
        self._content = tk.Frame(main, bg=_BG, width=CONTENT_W)
        self._content.pack(side="left", fill="both", expand=True)
        self._holder = tk.Frame(self._content, bg=_BG)
        self._holder.place(x=0, y=0, width=CONTENT_W, height=10)
        self._pages["status"]   = self._build_status_page()
        self._pages["settings"] = self._build_settings_page()
        self._pages["logs"]     = self._build_logs_page()
        self._pages["help"]     = self._build_help_page()
        self._pages["about"]    = self._build_about_page()
        self._toast = tk.Label(
            self._header, text="", bg=_IT_GREEN, fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
            padx=round(14 * UI_SHRINK), pady=round(4 * UI_SHRINK))

    # ── Sidebar ────────────────────────────────────────────────────────────
    def _build_sidebar(self, parent):
        for key, icon_name, _label in self.NAV:
            if key == "settings" and self._cfg is None:
                continue
            item = tk.Frame(parent, bg=_NAV_BG, cursor="hand2")
            bar = tk.Frame(item, bg=_NAV_BG, width=3)
            bar.pack(side="left", fill="y")
            holder = tk.Frame(item, bg=_NAV_BG)
            holder.pack(side="left", fill="both", expand=True)
            ic = Icon(holder, icon_name, color=_DIM, bg=_NAV_BG)
            ic.pack(expand=True)
            lbl = tk.Label(holder, text=_label, bg=_NAV_BG, fg=_DIM,
                           font=("Segoe UI", 13, "bold"), anchor="w")
            for w in (item, holder, ic, lbl):
                w.bind("<Button-1>", lambda _e, k=key: self._show_page(k))
                w.bind("<Enter>", lambda _e, k=key: self._nav_hover(k, True))
                w.bind("<Leave>", lambda _e, k=key: self._nav_hover(k, False))
            self._nav[key] = (item, bar, ic, holder, lbl)

        if self._cfg is not None:
            self._section_names = [n for n, _s in self._settings_sections()]
            for name in self._section_names:
                child = name in _CHILD_TO_GROUP
                indent = round((52 if child else 32) * UI_SHRINK)
                si = tk.Frame(parent, bg=_NAV_BG, cursor="hand2")
                sbar = tk.Frame(si, bg=_NAV_BG, width=3)
                sbar.pack(side="left", fill="y")
                slbl = tk.Label(si, text=_child_label(name) if child else name,
                                bg=_NAV_BG, fg=_DIM,
                                font=("Segoe UI", 11, "bold"), anchor="w",
                                justify="left",
                                wraplength=SIDEBAR_WIDE_W - round(40 * UI_SHRINK))
                slbl.pack(side="left", padx=(indent, 0))
                for w in (si, slbl):
                    w.bind("<Button-1>",
                           lambda _e, n=name: self._show_section(n))
                    w.bind("<Enter>",
                           lambda _e, n=name: self._sec_hover(n, True))
                    w.bind("<Leave>",
                           lambda _e, n=name: self._sec_hover(n, False))
                self._sec_sidebar[name] = (si, sbar, slbl)

            for label in SECTION_GROUPS:
                gi = tk.Frame(parent, bg=_NAV_BG, cursor="hand2")
                gbar = tk.Frame(gi, bg=_NAV_BG, width=3)
                gbar.pack(side="left", fill="y")
                glbl = tk.Label(gi, text=label, bg=_NAV_BG, fg=_DIM,
                                font=("Segoe UI", 11, "bold"), anchor="w",
                                justify="left",
                                wraplength=SIDEBAR_WIDE_W - round(40 * UI_SHRINK))
                glbl.pack(side="left", padx=(round(32 * UI_SHRINK), 0))
                for w in (gi, glbl):
                    w.bind("<Button-1>",
                           lambda _e, n=label: self._toggle_nav_group(n))
                    w.bind("<Enter>",
                           lambda _e, n=label: self._group_hover(n, True))
                    w.bind("<Leave>",
                           lambda _e, n=label: self._group_hover(n, False))
                self._group_sidebar[label] = (gi, gbar, glbl)

            self._sidebar_entries = []
            seen = set()
            for name in self._section_names:
                g = _CHILD_TO_GROUP.get(name)
                if g is None:
                    self._sidebar_entries.append(("section", name))
                elif g not in seen:
                    seen.add(g)
                    self._sidebar_entries.append(("group", g))

    def _layout_sidebar(self):
        keys = [k for k, _icn, _lbl in self.NAV
                if not (k == "settings" and self._cfg is None)]
        for _n, (si, _b, _l) in self._sec_sidebar.items():
            si.place_forget()
        for _lbl, (gi, _b, _l) in self._group_sidebar.items():
            gi.place_forget()

        if not self._sb_wide:
            n = len(keys)
            item_h = 42
            top_y = 28
            btn_cy = None
            try:
                if (self._btn.winfo_ismapped()
                        and self._btn.winfo_height() > 1):
                    sb_top = self._sidebar.winfo_rooty()
                    btn_cy = (self._btn.winfo_rooty()
                              + self._btn.winfo_height() / 2 - sb_top)
            except Exception:
                btn_cy = None
            if btn_cy is not None and btn_cy > top_y:
                bottom_y = btn_cy
            else:
                bottom_y = self._area_h - 60
                if (getattr(self, "_ready", False)
                        and self._align_retry_id is None):
                    self._align_retry_id = self.root.after(30, self._retry_align)
            bottom_y = max(top_y + 1, bottom_y)
            for i, k in enumerate(keys):
                cy = top_y if n <= 1 else top_y + (bottom_y - top_y) * i / (n - 1)
                item = self._nav[k][0]
                item.place(x=0, y=int(round(cy - item_h / 2)),
                           width=self._sb_w, height=item_h)
            return

        y = NAV_TOP_Y
        for k in keys:
            self._nav[k][0].place(x=0, y=y, width=self._sb_w, height=NAV_ITEM_H)
            y += NAV_ITEM_H
            if k == "settings" and self._sec_expanded:
                for entry in self._sidebar_entries:
                    if entry[0] == "section":
                        si = self._sec_sidebar[entry[1]][0]
                        si.place(x=0, y=y, width=self._sb_w, height=NAV_SUB_H)
                        y += NAV_SUB_H
                    else:
                        label = entry[1]
                        gi = self._group_sidebar[label][0]
                        gi.place(x=0, y=y, width=self._sb_w, height=NAV_SUB_H)
                        y += NAV_SUB_H
                        if self._group_expanded.get(label):
                            for child in SECTION_GROUPS[label]:
                                ci = self._sec_sidebar[child][0]
                                ci.place(x=0, y=y, width=self._sb_w,
                                         height=NAV_SUB_H)
                                y += NAV_SUB_H

    def _retry_align(self):
        self._align_retry_id = None
        self._layout_sidebar()

    def _set_sidebar_wide(self, wide):
        self._sb_wide = wide
        self._sb_w = SIDEBAR_WIDE_W if wide else SIDEBAR_W
        try:
            self._sidebar.config(width=self._sb_w)
        except Exception:
            pass
        for _k, (item, bar, ic, holder, lbl) in self._nav.items():
            ic.pack_forget()
            lbl.pack_forget()
            if wide:
                ic.pack(side="left",
                        padx=(round(14 * UI_SHRINK), round(8 * UI_SHRINK)))
                lbl.pack(side="left")
            else:
                ic.pack(expand=True)
        self._layout_sidebar()

    def _nav_hover(self, key, on):
        if key == self._page:
            return
        _item, _bar, ic, _holder, lbl = self._nav[key]
        ic.set_color(_ROG if on else _DIM)
        lbl.config(fg=_ROG if on else _DIM)

    def _set_nav_active(self, key):
        for k, (item, bar, ic, holder, lbl) in self._nav.items():
            active = (k == key)
            bgc = _NAV_ACT if active else _NAV_BG
            item.config(bg=bgc)
            holder.config(bg=bgc)
            bar.config(bg=_ROG if active else _NAV_BG)
            ic.set_color(_ROG if active else _DIM, bg=bgc)
            lbl.config(fg=_ROG if active else _DIM, bg=bgc)

    def _show_page(self, key):
        if key not in self._pages:
            return
        wide = (key != "status")
        self._sec_expanded = (key == "settings")
        if (not self._sec_expanded
                and not getattr(self, "_clearing_subnav", False)):
            _need = False
            for _n, (_si, _b, _l) in self._sec_sidebar.items():
                try:
                    if _si.winfo_ismapped():
                        _need = True
                        break
                except Exception:
                    pass
            if _need:
                self._clearing_subnav = True
                try:
                    self._layout_sidebar()
                    self.root.update()
                except Exception:
                    pass
                finally:
                    self._clearing_subnav = False
        self._area_h = self._tall_h if wide else self._status_h
        try:
            self._content.configure(height=self._area_h)
        except Exception:
            pass
        self._set_sidebar_wide(wide)
        target_w = self._wide_w if wide else self._compact_w
        page_w = self._scw if wide else CONTENT_W
        self._holder_w = page_w

        ready = getattr(self, "_ready", False)
        will_animate = ready and (target_w != self._cur_w)
        first_snap = will_animate and not self._first_resize_done
        shrinking = target_w < self._cur_w
        animate = will_animate and not first_snap and shrinking

        if animate:
            try:
                self._holder.place_forget()
            except Exception:
                pass

        for k, frame in self._pages.items():
            frame.pack_forget()
        self._pages[key].pack(fill="both", expand=True)
        self._page = key
        self._set_nav_active(key)
        if key == "settings" and self._section_names:
            name = (self._cur_section if self._cur_section in self._sec_frames
                    else self._section_names[0])
            self._show_section(name)
        if key == "logs":
            self._render_logs()

        if not ready:
            try:
                self._holder.place_configure(width=page_w, height=self._area_h)
            except Exception:
                pass
            self._cur_w = target_w
            self._w = target_w
            self._fit()
            return

        if animate:
            self._transition(target_w)
        else:
            if first_snap:
                self._first_resize_done = True
            try:
                self._holder.place_configure(width=page_w, height=self._area_h)
            except Exception:
                pass
            self._cur_w = target_w
            self._w = target_w
            self._fit()
            self._reveal()

    def _transition(self, target_w):
        if self._resize_anim_id is not None:
            try:
                self.root.after_cancel(self._resize_anim_id)
            except Exception:
                pass
            self._resize_anim_id = None
        self.root.update_idletasks()
        h1 = self.root.winfo_reqheight()
        try:
            w0 = self.root.winfo_width()
            h0 = self.root.winfo_height()
            x0 = self.root.winfo_x()
            y0 = self.root.winfo_y()
        except Exception:
            w0, h0, x0, y0 = self._cur_w, h1, 24, 24
        self._cur_w = target_w
        self._w = target_w
        x1 = (x0 + w0) - target_w
        x1, y1 = self._clamp_pos(x1, y0, target_w, h1)
        if w0 == target_w and h0 == h1 and x0 == x1 and y0 == y1:
            self._reveal()
            return
        self._show_curtain()
        self._anim_resize(w0, target_w, x0, x1, y0, y1, h0, h1, 0, 12)

    def _show_curtain(self):
        try:
            self._inner.pack_forget()
            self._curtain.place(x=0, y=0, relwidth=1, relheight=1)
            self._curtain.lift()
        except Exception:
            pass

    def _reveal(self):
        try:
            if not self._inner.winfo_ismapped():
                self._inner.pack(fill="both", expand=True, padx=1, pady=1)
            self._curtain.place_forget()
        except Exception:
            pass
        try:
            self._holder.place(x=0, y=0, width=self._holder_w,
                               height=self._area_h)
        except Exception:
            pass
        self._layout_sidebar()
        self._round_window_corners()
        try:
            self.root.update_idletasks()
        except Exception:
            pass

    def _anim_resize(self, w0, w1, x0, x1, y0, y1, h0, h1, step, n):
        t = step / n
        ease = 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2
        w = int(round(w0 + (w1 - w0) * ease))
        h = int(round(h0 + (h1 - h0) * ease))
        x = (x0 + w0) - w
        y = int(round(y0 + (y1 - y0) * ease))
        try:
            self.root.geometry(f"{w}x{h}+{x}+{y}")
            self.root.update_idletasks()
        except Exception:
            self._reveal()
            return
        if step < n:
            self._resize_anim_id = self.root.after(
                13, self._anim_resize, w0, w1, x0, x1, y0, y1, h0, h1,
                step + 1, n)
        else:
            self._resize_anim_id = None
            try:
                self.root.geometry(f"{w1}x{h1}+{x1}+{y1}")
                self.root.update_idletasks()
            except Exception:
                pass
            self._reveal()

    # ── STATUS page ───────────────────────────────────────────────────────
    def _build_status_page(self):
        page = tk.Frame(self._holder, bg=_BG)
        head = tk.Frame(page, bg=_BG)
        head.pack(fill="x", padx=PAD, pady=(14, 0))
        line = tk.Frame(head, bg=_BG)
        line.pack(fill="x")
        self._phase = tk.Label(line, textvariable=self._phase_var, bg=_BG,
                               fg=_DIM, font=("Segoe UI", 15, "bold"))
        self._phase.pack(side="left")
        tk.Label(line, text="  /  ", bg=_BG, fg=_DIVIDER,
                 font=("Segoe UI", 12)).pack(side="left")
        tk.Label(line, textvariable=self._status_var, bg=_BG, fg=_DIM,
                 font=("Segoe UI", 10)).pack(side="left")

        self._bar = StateBar(page, width=CONTENT_W - 2 * PAD, bg=_BG)
        self._bar.pack(fill="x", padx=PAD, pady=(10, 0))

        grid = tk.Frame(page, bg=_BG)
        grid.pack(fill="x", padx=PAD, pady=(14, 0))
        cells = (
            ("BOUGHT", self._bought_var,   _IT_GREEN),
            ("SEARCHES",   self._searches_var, _ROG),
            ("FAILED",    self._fails_var,     _RED_STAT),
            ("ACTIVE TIME", self._time_var,      _ROG),
        )
        grid.columnconfigure(0, weight=1, uniform="cards")
        grid.columnconfigure(1, weight=1, uniform="cards")
        grid.rowconfigure(0, minsize=92)
        grid.rowconfigure(1, minsize=92)
        for i, (caption, var, color) in enumerate(cells):
            r, c = divmod(i, 2)
            card = RoundedPanel(grid, width=round(10 * UI_SHRINK), height=round(88 * UI_SHRINK), radius=round(16 * UI_SHRINK),
                                fill=_CARD, bg=_BG, pad=14)
            card.grid(row=r, column=c, sticky="nsew",
                      padx=(0 if c == 0 else 9, 0),
                      pady=(0 if r == 0 else 9, 0))
            tk.Label(card.inner, textvariable=var, bg=_CARD, fg=color,
                     font=("Segoe UI", 21, "bold")).pack(anchor="w")
            tk.Label(card.inner, text=caption, bg=_CARD, fg=_FAINT,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 0))

        btn_wrap = tk.Frame(page, bg=_BG)
        btn_wrap.pack(fill="x", padx=PAD, pady=(15, 0))
        self._btn = PillButton(btn_wrap, text="START",
                               width=CONTENT_W - 2 * PAD, height=round(46 * UI_SHRINK), bg=_BG,
                               base=_BTN_BG, hover=_BTN_HV, fg=_BTN_FG)
        self._btn.pack(fill="x")

        footer = tk.Frame(page, bg=_BG)
        footer.pack(fill="x", pady=(12, 14))
        tk.Label(footer, text="F8  start / stop      \u00b7      F9  panic",
                 bg=_BG, fg=_DIM, font=("Segoe UI", 10)).pack()
        return page

    # ── SETTINGS page (sub-sections) ────────────────────────────────
    def _settings_sections(self):
        sections, cur = [], None
        for spec in SETTINGS_SPEC:
            if isinstance(spec, tuple) and spec[0] == "section":
                cur = (spec[1], [])
                sections.append(cur)
            else:
                if cur is None:
                    cur = ("General", [])
                    sections.append(cur)
                cur[1].append(spec)
        return sections

    def _build_settings_page(self):
        page = tk.Frame(self._holder, bg=_BG)
        if self._cfg is None:
            tk.Label(page, text="Settings unavailable.", bg=_BG,
                     fg=_DIM, font=("Segoe UI", 9)).pack(padx=PAD, pady=PAD)
            return page

        tk.Label(page, text="Settings", bg=_BG, fg=_ROG,
                 font=("Segoe UI", 24, "bold")).pack(anchor="w", padx=PAD,
                                                     pady=(14, 0))
        self._settings_sub = tk.Label(
            page, text="", bg=_BG, fg=_DIM, font=("Segoe UI", 10),
            anchor="w", justify="left", wraplength=self._scw - 2 * PAD)
        self._settings_sub.pack(anchor="w", padx=PAD, pady=(2, 36))

        body = tk.Frame(page, bg=_BG)
        body.pack(fill="both", expand=True, padx=PAD, pady=(0, 0))

        self._sec_w = self._scw - 2 * PAD

        sections = self._settings_sections()
        for name, specs in sections:
            sf = tk.Frame(body, bg=_BG)
            for spec in specs:
                self._add_setting_row(sf, spec)
            self._sec_frames[name] = sf

        if sections:
            self._show_section(sections[0][0])
        return page

    def _sec_hover(self, name, on):
        if name == self._cur_section:
            return
        si, sbar, slbl = self._sec_sidebar[name]
        slbl.config(fg=_ROG if on else _DIM)

    def _group_hover(self, label, on):
        gi, gbar, glbl = self._group_sidebar[label]
        hot = on or self._group_expanded.get(label, False) or \
            self._cur_section in SECTION_GROUPS.get(label, [])
        glbl.config(fg=_ROG if hot else _DIM)

    def _toggle_nav_group(self, label):
        self._group_expanded[label] = not self._group_expanded.get(label, False)
        if self._group_expanded[label]:
            children = SECTION_GROUPS.get(label, [])
            if children:
                self._show_section(children[0])
        else:
            self._refresh_group_buttons()
        self._layout_sidebar()

    def _refresh_group_buttons(self):
        for label, (gi, gbar, glbl) in self._group_sidebar.items():
            parent_of_cur = self._cur_section in SECTION_GROUPS.get(label, [])
            expanded = self._group_expanded.get(label, False)
            bgc = _NAV_ACT if parent_of_cur else _NAV_BG
            gi.config(bg=bgc)
            gbar.config(bg=_ROG if parent_of_cur else _NAV_BG)
            glbl.config(fg=_ROG if (parent_of_cur or expanded) else _DIM, bg=bgc)

    def _show_section(self, name):
        if name not in self._sec_frames:
            return
        for _n, sf in self._sec_frames.items():
            sf.pack_forget()
        self._sec_frames[name].pack(fill="both", expand=True)
        self._cur_section = name
        if self._settings_sub is not None:
            try:
                self._settings_sub.config(text=name)
            except Exception:
                pass
        for _n, (si, sbar, slbl) in self._sec_sidebar.items():
            active = (_n == name)
            bgc = _NAV_ACT if active else _NAV_BG
            si.config(bg=bgc)
            sbar.config(bg=_ROG if active else _NAV_BG)
            slbl.config(fg=_ROG if active else _DIM, bg=bgc)
        self._refresh_group_buttons()

    def _add_setting_row(self, parent, spec):
        key, kind = spec["key"], spec["kind"]
        cur = getattr(self._cfg, key, None)
        ctrl_w = SETTINGS_CTRL_W
        left_wrap = max(150, self._sec_w - ctrl_w - 26)

        row = tk.Frame(parent, bg=_BG)
        row.pack(fill="x", pady=(0, 16))

        ctrl = tk.Frame(row, bg=_BG)
        ctrl.pack(side="right", anchor="n")

        left = tk.Frame(row, bg=_BG)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text=spec["label"], bg=_BG, fg=_ROG,
                 font=("Segoe UI", 12, "bold"), anchor="w").pack(anchor="w")
        tk.Label(left, text=spec["desc"], bg=_BG, fg=_DIM,
                 font=("Segoe UI", 10), anchor="w", justify="left",
                 wraplength=left_wrap).pack(anchor="w", pady=(2, 0))

        if kind == "toggle":
            grp = spec.get("exclusive_group")

            def cmd(v, k=key, g=grp):
                if g and v:
                    for ok, (okind, ow) in self._setting_widgets.items():
                        if (okind == "toggle" and ok != k
                                and self._toggle_group.get(ok) == g):
                            ow.set(False)
                if k == "overlay_capturable":
                    self._set_capturable(v)
                self._autosave()
            tg = ToggleSwitch(ctrl, value=bool(cur), command=cmd, bg=_BG)
            tg.pack(pady=(2, 0))
            self._setting_widgets[key] = ("toggle", tg)
            if grp:
                self._toggle_group[key] = grp

        elif kind == "slider":
            val_var = tk.StringVar(value=_fmt(cur, spec["int"]))
            line = tk.Frame(ctrl, bg=_BG)
            line.pack()
            tk.Label(line, textvariable=val_var, bg=_BG, fg=_ROG,
                     font=("Segoe UI", 12, "bold"), width=5,
                     anchor="e").pack(side="left")
            sl = Slider(line, value=cur, lo=spec["lo"], hi=spec["hi"],
                        step=spec["step"], is_int=spec["int"],
                        width=ctrl_w - 112, bg=_BG,
                        on_change=lambda v, var=val_var, i=spec["int"]:
                            self._on_slider_change(var, v, i))
            sl.pack(side="left", padx=(8, 6))
            tk.Label(line, text="", bg=_BG, font=("Segoe UI", 10),
                     width=3).pack(side="left")
            self._setting_widgets[key] = ("slider", sl)

        elif kind == "range":
            lo_cur, hi_cur = (cur if isinstance(cur, (tuple, list))
                              else (spec["lo"], spec["hi"]))
            sliders = []
            for sub, sval in (("min", lo_cur), ("max", hi_cur)):
                line = tk.Frame(ctrl, bg=_BG)
                line.pack(pady=1)
                vv = tk.StringVar(value=_fmt(sval, spec["int"]))
                tk.Label(line, textvariable=vv, bg=_BG, fg=_ROG,
                         font=("Segoe UI", 12, "bold"), width=5,
                         anchor="e").pack(side="left")
                s = Slider(line, value=sval, lo=spec["lo"], hi=spec["hi"],
                           step=spec["step"], is_int=spec["int"],
                           width=ctrl_w - 112, bg=_BG,
                           on_change=lambda v, var=vv, i=spec["int"]:
                               self._on_slider_change(var, v, i))
                s.pack(side="left", padx=(8, 6))
                tk.Label(line, text=sub, bg=_BG, fg=_DIM,
                         font=("Segoe UI", 10), width=3,
                         anchor="w").pack(side="left")
                sliders.append(s)
            self._setting_widgets[key] = ("range", tuple(sliders))

        elif kind == "text":
            ent = tk.Entry(ctrl, bg=_CARD, fg=_ROG, insertbackground=_ROG,
                           relief="flat", font=("Segoe UI", 11), width=30,
                           highlightthickness=1, highlightbackground=_DIVIDER,
                           highlightcolor=_ROG)
            ent.insert(0, "" if cur is None else str(cur))
            ent.pack(pady=(2, 0), ipady=4)
            ent.bind("<KeyRelease>", lambda _e: self._autosave_soon())
            ent.bind("<FocusOut>", lambda _e: self._autosave_soon(0))
            self._setting_widgets[key] = ("text", ent)

    def _collect(self):
        out = {}
        for key, (kind, w) in self._setting_widgets.items():
            if kind == "range":
                out[key] = (kind, (w[0].get(), w[1].get()))
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

    def _on_slider_change(self, var, v, is_int):
        var.set(_fmt(v, is_int))
        self._autosave_soon()

    def _autosave(self):
        if self._cfg is None or not getattr(self, "_ready", False):
            return
        self._apply_collected(self._cfg, self._collect())
        if self._on_save:
            try:
                self._on_save(self._cfg)
            except Exception:
                pass
        self._show_toast("Saved \u2713")

    def _autosave_soon(self, delay=450):
        if not getattr(self, "_ready", False):
            return
        if self._autosave_id is not None:
            try:
                self.root.after_cancel(self._autosave_id)
            except Exception:
                pass
        self._autosave_id = self.root.after(delay, self._autosave_now)

    def _autosave_now(self):
        self._autosave_id = None
        self._autosave()

    def _show_toast(self, text="Saved \u2713"):
        if not getattr(self, "_toast", None):
            return
        try:
            self._toast.config(text=text)
            self._toast.place(relx=0.5, rely=0.5, anchor="center")
            self._toast.lift()
        except Exception:
            return
        if self._toast_id is not None:
            try:
                self.root.after_cancel(self._toast_id)
            except Exception:
                pass
        self._toast_id = self.root.after(1300, self._hide_toast)

    def _hide_toast(self):
        self._toast_id = None
        try:
            self._toast.place_forget()
        except Exception:
            pass

    # ── LOGS page ─────────────────────────────────────────────────────────
    def _build_logs_page(self):
        page = tk.Frame(self._holder, bg=_BG)
        self._page_title(page, "Logs",
                         "Safe to share: no keys or personal data.")

        bar = tk.Frame(page, bg=_BG)
        bar.pack(fill="x", padx=PAD, pady=(2, 0))
        self._log_filter = tk.Entry(bar, bg=_CARD, fg=_ROG,
                                    insertbackground=_ROG, relief="flat",
                                    font=("Segoe UI", 11), highlightthickness=1,
                                    highlightbackground=_DIVIDER,
                                    highlightcolor=_ROG)
        self._log_filter.pack(side="left", fill="x", expand=True, ipady=3)
        self._log_filter.bind("<KeyRelease>", lambda _e: self._render_logs())

        def mkbtn(parent, text, cmd):
            b = tk.Button(parent, text=text, font=("Segoe UI", 10, "bold"),
                          relief="flat", bd=0, highlightthickness=0,
                          cursor="hand2", padx=10, pady=4,
                          bg=_CARD, fg=_BTN_FG,
                          activebackground=_BG_MID,
                          activeforeground=_BTN_FG, command=cmd)
            b.pack(side="left", padx=(6, 0))
            return b

        mkbtn(bar, "COPY", self._copy_logs)

        box = RoundedPanel(page, radius=14, fill=_CARD, bg=_BG, pad=8)
        box.pack(fill="both", expand=True, padx=PAD, pady=(10, 14))
        self._log_text = tk.Text(box.inner, bg=_CARD, fg=_DIM, relief="flat",
                                 font=("Consolas", 11), height=6, wrap="none",
                                 highlightthickness=0, bd=0, padx=6, pady=4)
        self._log_text.pack(fill="both", expand=True)
        self._log_text.config(state="disabled")
        return page

    def _render_logs(self):
        if not hasattr(self, "_log_text"):
            return
        flt = self._log_filter.get().strip().lower()
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        rows = list(self._logs)
        if not rows:
            self._log_text.insert("end", "  no events yet.\n")
        for ts, msg in rows:
            line = f"{ts}  {msg}"
            if flt and flt not in line.lower():
                continue
            self._log_text.insert("end", line + "\n")
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def _add_log(self, msg):
        self._logs.append((time.strftime("%H:%M:%S"), str(msg)))
        if self._page == "logs":
            self._render_logs()

    def _copy_logs(self):
        text = "\n".join(f"{ts}  {msg}" for ts, msg in self._logs)
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        except Exception:
            pass

    # ── HELP page ───────────────────────────────────────────────────────
    def _build_help_page(self):
        page = tk.Frame(self._holder, bg=_BG)
        self._page_title(page, "Help", "Quick start and troubleshooting.")
        blocks = [
            ("Quick start", [
                "1. Open the game and go to Search Auctions.",
                "2. Check that the status is ready.",
                "3. Press START or the F8 key.",
            ]),
            ("If cars are being missed",
             ["Lower the Poll interval and the Delay between loops in "
              "Settings. If the recognition threshold is too high, "
              "reduce it until the screens get detected."]),
        ]
        for title, lines in blocks:
            tk.Label(page, text=title, bg=_BG, fg=_ROG,
                     font=("Segoe UI", 14, "bold")).pack(
                         anchor="w", padx=PAD, pady=(12, 2))
            for ln in lines:
                tk.Label(page, text=ln, bg=_BG, fg=_DIM,
                         font=("Segoe UI", 13), anchor="w", justify="left",
                         wraplength=self._scw - 2 * PAD).pack(
                             anchor="w", padx=PAD)
        return page

    # ── INFO page ────────────────────────────────────────────────────────
    def _build_about_page(self):
        page = tk.Frame(self._holder, bg=_BG)
        self._page_title(page, "Info", "")
        tk.Label(page,
                 text="This is an updated version of CecchinoDelleAste, adapted to work with the English version of the game. " \
                 "It is completely unrelated to Frosty's paid V2. If you need support or want to contribute to the tool's development, feel free to join the dedicated Discord server.",
                 bg=_BG, fg=_DIM, font=("Segoe UI", 13), anchor="w",
                 justify="left", wraplength=self._scw - 2 * PAD).pack(
                     anchor="w", padx=PAD, pady=(4, 0))
        _discord_url = "https://discord.gg/4fbQ7yNns8"

        def _open_discord():
            try:
                webbrowser.open(_discord_url)
            except Exception:
                pass

        PillButton(page, text="Join the Discord", command=_open_discord,
                   width=round(220 * UI_SHRINK), height=round(40 * UI_SHRINK),
                   bg=_BG, base=_BTN_BG, hover=_BTN_HV, fg=_BTN_FG).pack(
                       anchor="center", pady=(10, 0))
        tk.Label(page, text="Version", bg=_BG, fg=_ROG,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=PAD,
                                                     pady=(14, 2))
        tk.Label(page, text="V.2.0.2 Beta  \u00b7  Created by d1ablo", bg=_BG,
                 fg=_DIM, font=("Segoe UI", 13)).pack(anchor="w", padx=PAD)
        return page

    # ── Page util ────────────────────────────────────────────────────────
    def _page_title(self, parent, title, subtitle):
        tk.Label(parent, text=title, bg=_BG, fg=_ROG,
                 font=("Segoe UI", 24, "bold")).pack(anchor="w", padx=PAD,
                                                     pady=(14, 0))
        if subtitle:
            tk.Label(parent, text=subtitle, bg=_BG, fg=_DIM,
                     font=("Segoe UI", 10), anchor="w", justify="left",
                     wraplength=self._scw - 2 * PAD).pack(anchor="w", padx=PAD,
                                                          pady=(2, 20))

    def _current_monitor_rect(self):
        try:
            user32 = ctypes.windll.user32
            hwnd = self.root.winfo_id()
            p = user32.GetParent(hwnd)
            while p:
                hwnd = p
                p = user32.GetParent(hwnd)
            MONITOR_DEFAULTTONEAREST = 2
            hmon = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)

            class RECT(ctypes.Structure):
                _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                            ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_ulong), ("rcMonitor", RECT),
                            ("rcWork", RECT), ("dwFlags", ctypes.c_ulong)]

            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                r = mi.rcWork
                if r.right > r.left and r.bottom > r.top:
                    return (r.left, r.top, r.right, r.bottom)
        except Exception:
            pass
        try:
            return (0, 0, self.root.winfo_screenwidth(),
                    self.root.winfo_screenheight())
        except Exception:
            return (0, 0, 1920, 1080)

    def _clamp_pos(self, x, y, w, h, margin=8):
        left, top, right, bottom = self._current_monitor_rect()
        x = max(left + margin, min(int(x), right - int(w) - margin))
        y = max(top + margin, min(int(y), bottom - int(h) - margin))
        return x, y

    def _fit(self):
        self.root.update_idletasks()
        h = self.root.winfo_reqheight()
        try:
            x, y = self.root.winfo_x(), self.root.winfo_y()
        except Exception:
            x, y = 24, 24
        x, y = self._clamp_pos(x, y, self._cur_w, h)
        self.root.geometry(f"{self._cur_w}x{h}+{x}+{y}")

    # ── Drag ───────────────────────────────────────────────────────────────
    def _drag_start(self, e):
        self._drag = (e.x_root - self.root.winfo_x(),
                      e.y_root - self.root.winfo_y())

    def _drag_move(self, e):
        x = e.x_root - self._drag[0]
        y = e.y_root - self._drag[1]
        self.root.geometry(f"+{x}+{y}")

    # ── START/STOP button ───────────────────────────────────────────────
    def _set_button(self, running: bool):
        if running:
            self._btn.set_mode("STOP", _BTN_BG, _BTN_HV, _BTN_FG)
        else:
            self._btn.set_mode("START", _BTN_BG, _BTN_HV, _BTN_FG)

    # ── Status ──────────────────────────────────────────────────────────────
    def _retint(self):
        """Phase, colors and animated bar based on the real state + text."""
        detail = self._status_var.get().lower()
        if not self._running:
            phase, color, bar = "IDLE", _DIM, "idle"
        elif "paused" in detail:
            phase, color, bar = "PAUSED", _AMBER, "paused"
        else:
            phase, color, bar = "ACTIVE", _ROG, "running"
        self._phase_var.set(phase)
        self._phase.config(fg=color)
        self._dot.set_color(color)
        if self._bar is not None:
            self._bar.set_state(bar)

    def _apply_status(self, text: str):
        self._status_var.set(text)
        self._retint()

    def _apply_running(self, running: bool):
        self._running = bool(running)
        self._set_button(self._running)
        self._active = self._running
        if self._running and self._started is None:
            self._started = time.monotonic()
            self._time_var.set("00:00")
        self._retint()

    def _apply_stats(self, searches: int, bought: int, fails: int):
        self._searches_var.set(str(searches))
        self._bought_var.set(str(bought))
        self._fails_var.set(str(fails))

    def _tick(self):
        if self._active and self._started is not None:
            m, s = divmod(int(time.monotonic() - self._started), 60)
            self._time_var.set(f"{m:02d}:{s:02d}")
        try:
            self.root.after(1000, self._tick)
        except RuntimeError:
            pass

    # ── Public API ───────────────────────────────────────────────────────
    def set_status(self, text: str):
        try:
            self.root.after(0, self._apply_status, text)
        except RuntimeError:
            pass

    def set_running(self, running: bool):
        try:
            self.root.after(0, self._apply_running, running)
        except RuntimeError:
            pass

    def set_stats(self, searches: int, bought: int, fails: int):
        try:
            self.root.after(0, self._apply_stats, searches, bought, fails)
        except RuntimeError:
            pass

    def log(self, msg: str):
        try:
            self.root.after(0, self._add_log, msg)
        except RuntimeError:
            pass

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
        self._btn.set_command(callback)

    def run(self):
        self.root.mainloop()

    def close(self):
        try:
            self.root.destroy()
        except Exception:
            pass