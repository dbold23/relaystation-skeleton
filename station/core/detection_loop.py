"""DetectionLoop: the SDR read loop that feeds a MultiChannelDetector,
reports status and drains the stage partition.

Split out of core/detector.py on 2026-09-23 with no change to any line of code:
every OTA file must stay under the server's 128 KB per-file limit, and
detector.py had reached 109 KB of it. core/detector.py re-exports every name
defined here, so `from core.detector import X` keeps working for every X it
ever offered. tests/test_ota_file_budget.py holds each file to a budget below
the limit so the next split happens with room to spare, not at the cliff.

Two consequences of the move. The logger keeps the name core.detector, so
log lines and anything filtering on them read exactly as before. And this
module has its own `time`: a test that swaps core.detector.time for a
virtual clock does not reach the loop (none does today; the benchmark
drives MultiChannelDetector directly).
"""
from __future__ import annotations
import time
import logging
from typing import TYPE_CHECKING, Callable, Optional
from core.survey_dsp import SAMPLES_PER_READ, STAGE_KEYS

class DetectionLoop:
    """Main detection loop manager"""

    def __init__(self, sdr, config, detector: MultiChannelDetector):
        """
        Initialize detection loop

        Args:
            sdr: RtlSdr instance
            config: Config instance
            detector: MultiChannelDetector instance
        """
        ...
    TX_BLANK_GUARD_S = 0.05

    def _read_overlaps_tx(self, t0: float, t1: float) -> bool:
        ...

    def run(self):
        """Run the detection loop"""
        ...

    def stop(self):
        """Stop the detection loop"""
        ...

    def _status_update(self):
        """Periodic status logging"""
        ...
