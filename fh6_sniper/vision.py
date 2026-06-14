from __future__ import annotations
from enum import Enum, auto
from pathlib import Path
import cv2
import numpy as np


class Screen(Enum):
    UNKNOWN = auto()
    SEARCH_CONFIG = auto()
    RESULTS_HAS_CARS = auto()
    RESULTS_EMPTY = auto()
    AUCTION_OPTIONS = auto()
    PLAYER_OPTIONS = auto()
    BUY_OUT = auto()
    BUYOUT_PROGRESS = auto()
    BUYOUT_SUCCESS = auto()
    BUYOUT_FAILED = auto()
    CLAIM_CAR = auto()
    AH_LANDING = auto()


TEMPLATE_SCREENS: dict[str, Screen] = {
    "search.png": Screen.SEARCH_CONFIG,
    "auction_details.png": Screen.RESULTS_HAS_CARS,
    "no_auctions.png": Screen.RESULTS_EMPTY,
    "auction_options.png": Screen.AUCTION_OPTIONS,
    "player_options.png": Screen.PLAYER_OPTIONS,
    "buy_out.png": Screen.BUY_OUT,
    "buy_out_bgoff.png": Screen.BUY_OUT,
    "buy_out_progress.png": Screen.BUYOUT_PROGRESS,
    "buy_out_progress_bgoff.png": Screen.BUYOUT_PROGRESS,
    "buyout_successful.png": Screen.BUYOUT_SUCCESS,
    "buyout_failed.png": Screen.BUYOUT_FAILED,
    "claim_car.png": Screen.CLAIM_CAR,
    "ah_landing.png": Screen.AH_LANDING,
}


# ── Template matching ─────────────────────────────────────────────────────────
def _gray(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def match_template(scene: np.ndarray, template: np.ndarray) -> float:
    s, t = _gray(scene), _gray(template)
    if t.shape[0] > s.shape[0] or t.shape[1] > s.shape[1]:
        return 0.0
    result = cv2.matchTemplate(s, t, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return float(max_val)


_DOWNSCALED_TEMPLATES: dict[int, np.ndarray] = {}


def _small(tmpl: np.ndarray) -> np.ndarray:
    key = id(tmpl)
    cached = _DOWNSCALED_TEMPLATES.get(key)
    if cached is None:
        cached = _downscale(tmpl)
        _DOWNSCALED_TEMPLATES[key] = cached
    return cached


def load_templates(template_dir) -> dict:
    out = {}
    for name in TEMPLATE_SCREENS:
        if _has_bgoff_variant(name):
            continue
        path = Path(template_dir) / name
        img = cv2.imread(str(path))
        if img is None:
            raise FileNotFoundError(f"template mancante: {path}")
        gray = _gray(img)
        out[name] = gray
        _DOWNSCALED_TEMPLATES[id(gray)] = _downscale(gray)
    return out


def _has_bgoff_variant(name: str) -> bool:
    if name.endswith("_bgoff.png"):
        return False
    sibling = name[:-len(".png")] + "_bgoff.png"
    return sibling in TEMPLATE_SCREENS


_RESULTS_PRIORITY = ("auction_details.png", "no_auctions.png")
_MATCH_SCALE = 0.5


def _downscale(img: np.ndarray) -> np.ndarray:
    return cv2.resize(img, None, fx=_MATCH_SCALE, fy=_MATCH_SCALE,
                      interpolation=cv2.INTER_AREA)


TEMPLATE_REGIONS = {
    "search.png":                (472, 223, 1448, 471),
    "auction_details.png":       (889,  64, 1920, 294),
    "no_auctions.png":           (700, 410, 1780, 720),
    "auction_options.png":       (546, 276, 1374, 526),
    "player_options.png":        (580, 230, 1340, 486),
    "buy_out.png":               (520, 470, 1400, 620),
    "buy_out_bgoff.png":         (520, 470, 1400, 620),
    "buy_out_progress.png":      (520, 470, 1400, 620),
    "buy_out_progress_bgoff.png":(520, 470, 1400, 620),
    "buyout_successful.png":     (539, 334, 1374, 612),
    "buyout_failed.png":         (546, 378, 1374, 631),
    "claim_car.png":             (538, 359, 1374, 615),
    "ah_landing.png":            (16,   89,  387, 291),
}

_FULL_RES_TEMPLATES = {
    "buy_out.png", "buy_out_bgoff.png",
    "buy_out_progress.png", "buy_out_progress_bgoff.png",
}


def screen_scores(scene_bgr, templates: dict, targets=None) -> dict:
    if targets is not None:
        wanted = set(_RESULTS_PRIORITY)
        wanted |= {n for n, scr in TEMPLATE_SCREENS.items() if scr in targets}
        templates = {n: t for n, t in templates.items() if n in wanted}
    gray = _gray(scene_bgr)
    h, w = gray.shape[:2]
    scores = {}
    for name, tmpl in templates.items():
        region = TEMPLATE_REGIONS.get(name)
        if region:
            x1, y1, x2, y2 = region
            crop = gray[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        else:
            crop = gray
        if name in _FULL_RES_TEMPLATES:
            scores[name] = match_template(crop, tmpl)
        else:
            scores[name] = match_template(_downscale(crop), _small(tmpl))
    return scores


def identify_screen(scene_bgr, templates: dict, threshold: float,
                    targets=None) -> Screen:
    scores = screen_scores(scene_bgr, templates, targets=targets)
    for name in _RESULTS_PRIORITY:
        if scores.get(name, 0.0) >= threshold:
            return TEMPLATE_SCREENS[name]
    best_screen, best_score = Screen.UNKNOWN, threshold
    for name, score in scores.items():
        if score >= best_score:
            best_screen, best_score = TEMPLATE_SCREENS[name], score
    return best_screen


# ── Confirm button detection ──────────────────────────────────────────────────
CONFIRM_ROW = (548, 714, 1372, 772)
_CONFIRM_V_THRESH = 130
_CONFIRM_V_COUNT = 500


def is_confirm_highlighted(scene_bgr, region=CONFIRM_ROW) -> bool:
    x1, y1, x2, y2 = region
    crop = scene_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return False
    v = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)[:, :, 2]
    _, bright = cv2.threshold(v, _CONFIRM_V_THRESH, 255, cv2.THRESH_BINARY)
    return int(cv2.countNonZero(bright)) > _CONFIRM_V_COUNT


# ── SOLD stamp detection ──────────────────────────────────────────────────────
SOLD_STAMP_REGION = (90, 185, 300, 295)

_SOLD_H_LO = 24
_SOLD_H_HI = 50
_SOLD_S_THRESH = 100
_SOLD_V_THRESH = 100
_SOLD_PIXEL_COUNT = 700

SOLD_STAMP_REGIONS = (
    SOLD_STAMP_REGION,
    (90, 387, 300, 497),
    (90, 589, 300, 699),
    (90, 791, 300, 901),
)

_SOLD_STRIP = (90, 185, 300, 901)


def _lime_mask(hsv: np.ndarray) -> np.ndarray:
    return cv2.inRange(
        hsv,
        np.array([_SOLD_H_LO, _SOLD_S_THRESH, _SOLD_V_THRESH], np.uint8),
        np.array([_SOLD_H_HI, 255, 255], np.uint8))


def is_card_sold(scene_bgr, region=SOLD_STAMP_REGION) -> bool:
    x1, y1, x2, y2 = region
    crop = scene_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    return int(cv2.countNonZero(_lime_mask(hsv))) > _SOLD_PIXEL_COUNT


def sold_slots(scene_bgr) -> tuple:
    sx1, sy1, sx2, sy2 = _SOLD_STRIP
    h, w = scene_bgr.shape[:2]
    strip = scene_bgr[max(0, sy1):min(h, sy2), max(0, sx1):min(w, sx2)]
    if strip.size == 0:
        return (False, False, False, False)
    mask = _lime_mask(cv2.cvtColor(strip, cv2.COLOR_BGR2HSV))
    out = []
    for (x1, y1, x2, y2) in SOLD_STAMP_REGIONS:
        sub = mask[y1 - sy1:y2 - sy1, x1 - sx1:x2 - sx1]
        out.append(int(cv2.countNonZero(sub)) > _SOLD_PIXEL_COUNT)
    return tuple(out)


def first_buyable_slot(scene_bgr) -> int:
    for i, sold in enumerate(sold_slots(scene_bgr), start=1):
        if not sold:
            return i
    return 0
