"""Per-tag pulse accounting between two locked-tag reports.

A locked tag is heard on every pulse (about 35 a minute) but reports once a
minute: one 'k' event carrying the signal of whichever pulse happened to be
due. The other 34 pulses were thrown away, and with them everything Central
could have learnt about the animal rather than the tag:

- how many pulses were heard against how many the beacon period predicts
  (presence ratio: a diving or hauled-out marine animal, or a tag at the edge
  of range, shows as a fraction; a tag in the open shows as ~1),
- how much the signal moves from pulse to pulse (a resting animal's tag
  holds its level, a moving one swings it by several dB; the activity
  measure automated telemetry has used since Kays et al. 2011),
- the spacing of arrivals as heard, before any validation (a tag whose
  mortality sensor has doubled its pulse rate is otherwise invisible: the
  validator's ghost filter drops every pulse under 1.5 s apart and keeps
  reporting 1.7155 s),
- the measured carrier (a crystal drifts with temperature, so this tracks
  the tag's temperature for free).

TagWindows accumulates those per tag on the detection thread and hands back
a small dict of extra 'k' fields when the queue emits a report. Nothing here
changes what is detected or when a report is sent.

Wire fields (all ints, about 55 bytes on the wire):
    w   seconds the window covers
    n   distinct pulse arrivals heard in it
    x   arrivals the beacon period predicts for w
    sp  [p10, p50, p90] of per-pulse signal, tenths of a dB
    sd  median |change| in signal between consecutive arrivals, tenths of a dB
    pi  base arrival spacing as heard, ms (0 when fewer than 3 arrivals)
    hz  median measured carrier minus the event's f * 1000, Hz
"""
import threading
from typing import Dict, List, Optional
SAME_PULSE_SEC = 0.3
SAME_TAG_KHZ = 3
DEFAULT_PERIOD_SEC = 1.7155
MAX_WINDOW_SEC = 3600.0
MAX_ARRIVALS = 4096
MAX_TAGS = 64

def _percentile(sorted_vals: List[float], q: float) -> float:
    """Linear-interpolated percentile of an already sorted list."""
    ...

def base_spacing(times: List[float]) -> float:
    """The regular spacing of a pulse train with pulses missing from it.

    Gaps are multiples of the true period, so the shortest regular gap is the
    period. A single stray arrival would make the plain minimum wrong, so the
    base is the median of the gaps near the lower quartile. Returns 0.0 when
    there are fewer than two gaps.
    """
    ...

class _Window:

    def __init__(self, start: float):
        ...

class TagWindows:
    """Pulse accounting per tag, drained each time a 'k' report goes out."""

    def __init__(self, default_period_sec: float=DEFAULT_PERIOD_SEC):
        ...

    def _key(self, table: Dict[int, object], khz: int) -> Optional[int]:
        ...

    def add(self, frequency_mhz: float, signal_db: float, now: float) -> None:
        """Record one reported pulse. Cheap; runs on the detection thread."""
        ...

    def drain(self, frequency_khz: int, now: float, period_sec: Optional[float]=None) -> Dict:
        """The window for the tag at frequency_khz, as 'k' fields, and reset.

        Returns {} when nothing was recorded for that tag, so the report goes
        out exactly as before.
        """
        ...

def summarise(start: float, arrivals: List[float], signals: List[float], freqs_hz: List[float], frequency_khz: int, now: float, period_sec: float) -> Dict:
    """Turn one window's arrivals into the wire fields listed in the module doc."""
    ...
