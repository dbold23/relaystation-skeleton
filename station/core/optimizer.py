"""
Gain Optimizer for RelayStation v2
Auto-calibrates SDR gain based on noise floor (no tag needed)
"""
import numpy as np
import time
import logging
from typing import Optional, Dict, List, Tuple
MEASUREMENT_DURATION = 10
SETTLE_TIME = 1.0
MAX_CLIP_FRACTION = 0.001
CLIP_LEVEL = 0.98
MAX_INITIAL_THRESHOLD_DB = 8.0

class GainOptimizer:
    """Optimizes SDR gain based on noise floor characteristics"""

    def __init__(self, sdr, config, progress_callback=None):
        """
        Initialize optimizer

        Args:
            sdr: RtlSdr instance (already opened)
            config: Config instance
            progress_callback: Optional callback for progress updates
        """
        ...

    def _report_progress(self, data: dict):
        """Report calibration progress to callback"""
        ...

    def measure_noise_at_gain(self, gain: float, duration: float=MEASUREMENT_DURATION) -> Dict:
        """
        Measure noise floor characteristics at a specific gain

        Args:
            gain: SDR gain in dB
            duration: How long to measure

        Returns:
            Dict with noise statistics
        """
        ...

    def find_optimal_gain(self, gain_values: List[float]=None) -> Tuple[float, Dict]:
        """
        Sweep through gain values and find optimal setting

        Optimal = lowest noise floor with lowest variance (cleanest signal)

        Args:
            gain_values: List of gains to test (default: GAIN_VALUES)

        Returns:
            Tuple of (optimal_gain, full_results_dict)
        """
        ...

    def run_calibration(self, save_to_config: bool=True) -> float:
        """
        Run full calibration and optionally save results

        Args:
            save_to_config: Whether to save optimal gain to config

        Returns:
            Optimal gain value
        """
        ...

class AdaptiveThreshold:
    """Continuously adapts detection threshold based on signal statistics"""

    def __init__(self, config):
        ...

    def record_detection(self, signal_db: float, noise_floor_db: float):
        """
        Record a confirmed detection's signal strength

        Args:
            signal_db: Signal power during detection
            noise_floor_db: Current noise floor
        """
        ...

    def _adapt_threshold(self):
        """Deliberately does NOT raise the threshold from detection strength.

        The previous implementation did, and it taught a station to go deaf. It
        computed:

            signal_above_noise = signal_db - noise_floor_db
            new_threshold = max(median(signals) * 0.5, calibrated_floor, 10.0)

        Three compounding errors:

        1. `signal_db` is `change_db`, a RELATIVE rise over the channel's own
           rolling baseline, while `noise_floor_db` is an ABSOLUTE dBFS median.
           Subtracting one from the other is dimensionally meaningless: a +35 dB
           change against a -56 dBFS floor produced 91.
        2. It derived a detection threshold from SIGNAL strength. A threshold
           exists to sit above the NOISE. Halving a signal magnitude inverts the
           logic, so the louder the tag, the deafer the station.
        3. The 10.0 dB "absolute minimum" contradicted the boot calibration,
           which sets 3.0-4.5 dB and CAPS at MAX_INITIAL_THRESHOLD_DB = 8.0. The
           runtime path could therefore only ever overrule calibration upward.

        Observed on pi3 on 2026-07-24/25 with a test tag three feet from the
        antenna: `3.0 -> 39.0`, then 38.5, 35.0, and 31.0 dB, each written to
        config.ini via save() so it survived every restart. The station had
        quietly raised its own detection threshold above almost any real signal
        while continuing to report itself healthy -- the same failure shape as
        the five defects fixed the day before.

        Signal strength carries no information about the right threshold, so
        there is nothing to salvage in the calculation. Boot calibration already
        derives it correctly, from the robust spread of the noise (MAD) with a
        hard cap. Statistics are still collected for observability via
        get_stats(); they simply no longer steer the detector.
        """
        ...

    def get_stats(self) -> Dict:
        """Get adaptation statistics"""
        ...
