"""Pulse-train validation for core.detector: the per-channel state
(FrequencyChannel), the reported tag (DetectedTag) and PatternValidator,
which folds pulse intervals onto the beacon period and decides validity.

Split out of core/detector.py on 2026-09-23 with no change to any line of code:
every OTA file must stay under the server's 128 KB per-file limit, and
detector.py had reached 109 KB of it. core/detector.py re-exports every name
defined here, so `from core.detector import X` keeps working for every X it
ever offered. tests/test_ota_file_budget.py holds each file to a budget below
the limit so the next split happens with room to spare, not at the cliff.

PatternValidator.add_pulse() falls back to time.time() only when called
without a timestamp; the detector always passes one, so a virtual clock
patched onto core.detector.time (testing/bench_range.py) still governs it.
"""
import time
import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Tuple
from datetime import datetime
MAX_SKIPPED_PULSES = 6.0

@dataclass
class FrequencyChannel:
    """Represents a single frequency channel for tag detection"""
    center_freq: float
    index: int
    power_db: float = -100.0
    baseline_db: float = -100.0
    last_pulse_time: float = 0.0
    hot_run: int = 0
    hot_run_start: float = 0.0

@dataclass
class DetectedTag:
    """Represents a detected and validated tag"""
    frequency_hz: float
    frequency_mhz: float
    pulse_interval: float
    confidence: float
    signal_strength_db: float
    peak_signal_db: float
    first_detected: datetime
    last_seen: datetime
    pulse_count: int
    is_locked: bool = False
    weak_streak: int = 0

    def to_dict(self) -> Dict:
        ...

class PatternValidator:
    """
    Validates pulse sequences using pulse counting with ghost filtering.

    Our channel-power architecture samples ~125ms windows every ~475ms,
    creating inherent timing jitter that makes strict interval validation
    unreliable. Instead, we rely on the upstream filters (power floor,
    change threshold, whitelist, bandwidth) to reject non-tag signals,
    and use simple pulse counting to confirm a repeating source.

    Ghost filtering handles double-detections where the same tag pulse
    lands in adjacent sample windows.
    """

    def __init__(self, min_pulses: int=5, min_interval: float=0.5, max_interval: float=30.0, reset_timeout: float=60.0, ghost_threshold: float=1.0):
        ...

    def add_pulse(self, timestamp: float=None) -> Tuple[bool, float, Dict]:
        """Record a pulse and validate by counting"""
        ...

    def reset(self):
        ...
