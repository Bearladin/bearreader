import re
from typing import Callable

ImportProgressCallback = Callable[[str, int], None]
_COUNTER_SUFFIX = re.compile(r"\s+\d+\s*/\s*\d+(?:\s+bytes)?$")


def progress_phase_key(phase: str) -> str:
    return _COUNTER_SUFFIX.sub("", phase).strip()


def map_progress(start: int, end: int, current: int, total: int) -> int:
    if total <= 0:
        return start
    bounded = max(0, min(current, total))
    return start + ((end - start) * bounded) // total


def should_persist_progress(
    previous_percent: int,
    previous_phase: str,
    percent: int,
    phase: str,
) -> bool:
    target = max(previous_percent, min(99, percent))
    return (
        progress_phase_key(phase) != progress_phase_key(previous_phase)
        or target == 99
        or target - previous_percent >= 2
    )
