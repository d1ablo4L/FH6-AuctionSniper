from __future__ import annotations
import csv
import datetime as dt
import threading
from pathlib import Path


def log_purchase(log_path, outcome: str, loop_seconds: float,
                 total: int) -> None:
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(
                ["timestamp", "outcome", "loop_seconds", "total_bought"])
        writer.writerow([
            dt.datetime.now().isoformat(timespec="seconds"),
            outcome, f"{loop_seconds:.1f}", total,
        ])


def notify_success(car_count: int, sound: bool, toast: bool) -> None:
    def _run() -> None:
        if sound:
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass
        if toast:
            try:
                from win11toast import toast as show_toast
                show_toast("FH6 Sniper",
                           f"Car bought ({car_count} this session)")
            except Exception:
                pass

    threading.Thread(target=_run, name="fh6-notify", daemon=True).start()
