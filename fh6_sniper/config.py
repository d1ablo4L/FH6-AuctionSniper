from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("config.json")


@dataclass
class Config:
    window_title: str = "Forza Horizon 6"
    match_threshold: float = 0.80
    key_hold_ms: tuple = (10, 20)
    between_keys_ms: tuple = (10, 20)
    poll_interval_ms: tuple = (15, 30)
    buyout_select_delay_ms: int = 0
    buyout_confirm_window_s: float = 0.35
    buyout_open_wait_s: float = 2.5
    collect_claim_wait_s: float = 1.0
    collect_unknown_wait_s: float = 1.0
    timeout_results_s: float = 12.0
    timeout_outcome_s: float = 25.0
    timeout_claim_s: float = 30.0
    timeout_generic_s: float = 20.0
    loop_pace_s: float = 0.10
    auto_stop_enabled: bool = True
    max_cars: int = 1
    max_minutes: float = 180.0
    collect_after_buyout: bool = True
    notify_sound: bool = True
    notify_toast: bool = True
    overlay_capturable: bool = False
    search_jitter_enabled: bool = True
    search_jitter_steps: int = 1
    maxbid_rows_above_confirm: int = 2
    jitter_maxbid: bool = False
    jitter_maxbuyout: bool = False
    hotkey_start_stop: str = "<f8>"
    hotkey_panic: str = "<f9>"


_TUPLE_FIELDS = {
    name for name, f in Config.__dataclass_fields__.items()
    if isinstance(f.default, tuple)
}


def load_config(path=DEFAULT_CONFIG_PATH) -> Config:
    path = Path(path)
    if not path.exists():
        cfg = Config()
        save_config(cfg, path)
        return cfg
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in _TUPLE_FIELDS:
        if key in data and isinstance(data[key], list):
            data[key] = tuple(data[key])
    known = set(Config.__dataclass_fields__)
    cfg = Config(**{k: v for k, v in data.items() if k in known})
    for key, value in data.items():
        if key not in known:
            setattr(cfg, key, value)
    if not known.issubset(data.keys()):
        save_config(cfg, path)
    return cfg


def save_config(cfg: Config, path=DEFAULT_CONFIG_PATH) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(cfg)
    declared = set(Config.__dataclass_fields__)
    for key, value in cfg.__dict__.items():
        if key not in declared:
            data[key] = value
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
