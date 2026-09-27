"""What a tag's pulse train says about the animal, from the station's windows.

Since Relay-Cellular d4f95ca a station attaches a pulse-accounting summary to
every locked-tag report ('k'): pulses heard against pulses the beacon period
predicts, the signal spread and its pulse-to-pulse change, the arrival
spacing as heard (before validation) and the measured carrier. One report
covers the minute since the previous one, so the windows tile time.
Database.store_events keeps each one as a tag_windows row; this module turns
a run of rows into three readings and one verdict.

    presence  heard / expected. Near 1: the tag is in the open and in range.
              A fraction: pulses are being lost, which for a marine animal
              is usually the tag under water (seawater absorbs VHF) or the
              animal at the edge of range. Shown, not alerted on.
    movement  median pulse-to-pulse change in signal, dB. A resting animal's
              tag holds its level, a moving one swings it by several dB (the
              activity measure automated telemetry has used since Kays et al.
              2011). Relative within one tag and one station only: it also
              grows as signal falls toward the noise.
    spacing   base arrival spacing, ms, against the tag's own baseline.

    rate state  'normal', 'fast' (spacing near half the baseline: the pulse
              rate doubled, which is how most VHF mortality sensors signal),
              'slow' (near double), or 'changed' (any other sustained shift).
              It needs RATE_MIN_WINDOWS consecutive windows that agree, each
              with enough arrivals to trust its spacing, so one noisy minute
              cannot raise it.

Nothing here has been checked against a tag that really switched mode: the
station change and this module were written together on 2026-09-23 from the
arithmetic of the validator's ghost filter, which hides a doubled rate (see
Relay-Cellular tests/test_tag_window.py). The alert it drives is therefore
dashboard-only (tier 2) until a bench test with a mortality-mode tag says
otherwise.
"""
from statistics import median
from typing import Dict, List, Optional
NOMINAL_SPACING_MS = 1715.5
MIN_ARRIVALS_FOR_SPACING = 8
RATE_MIN_WINDOWS = 3
BASELINE_WINDOWS = 10
FAST_BAND = (0.42, 0.58)
SLOW_BAND = (1.75, 2.25)
NORMAL_BAND = (0.93, 1.07)

def presence(row: Dict) -> Optional[float]:
    ...

def _trusted(rows: List[Dict]) -> List[Dict]:
    ...

def baseline_spacing(rows: List[Dict]) -> float:
    """The tag's usual spacing: median of its oldest trusted windows that sit
    near the nominal period, else the nominal period itself. Taken from the
    oldest windows so a tag that switched mode long ago does not teach the
    baseline its new rate."""
    ...

def classify_ratio(ratio: float) -> str:
    ...

def rate_state(rows: List[Dict]) -> Dict:
    """The tag's current rate state from rows in time order (oldest first).

    Returns {'state', 'ratio', 'baseline_ms', 'since', 'windows'}; 'state' is
    'unknown' until RATE_MIN_WINDOWS trusted windows exist.
    """
    ...

def series(rows: List[Dict]) -> List[Dict]:
    """Per-window readings for a chart, oldest first."""
    ...

def summary(rows: List[Dict]) -> Dict:
    """Headline numbers over the rows given (oldest first)."""
    ...
