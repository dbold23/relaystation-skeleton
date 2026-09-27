"""
Tag Detector for RelayStation v2
Multi-channel detection with adaptive thresholds and pattern validation
"""
import time
import logging
import numpy as np
from collections import deque
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime
from core.survey_dsp import scipy_welch, HAS_SCIPY, welch_psd, segment_spectrogram, _norm_isf, gamma_isf_scaled, SURVEY_LOOKS_FACTOR, SURVEY_NULL_POOL, SURVEY_NULL_MIN, survey_gate, survey_gate_from_pool, _parabolic, SAMPLES_PER_READ, SURVEY_NPERSEG, SURVEY_BIN_HZ, survey_nperseg, STAGE_KEYS
from core.pattern_validator import MAX_SKIPPED_PULSES, FrequencyChannel, DetectedTag, PatternValidator
from core.detection_loop import DetectionLoop
PULSE_COOLDOWN_PER_CHANNEL = 0.5
LOCK_DEGRADE_DB = 10.0
SURVEY_CLICK_RATIO = 10.0
SURVEY_CLICK_MAX_CONC = 0.2
SURVEY_GATE_EXCESS_WARN_DB = 3.0
DC_GUARD_HZ = 1500.0
MF_TARGET_BASEBAND_HZ = 16000.0
MF_MIN_BASEBAND_HZ = 8000.0
CARRIER_MIN_SECONDS = 4.0
CARRIER_MIN_FRAMES = 6
CARRIER_RELEARN_SECONDS = 120.0
LOCK_MIN_PULSES = 10
LOCK_MIN_CONFIDENCE = 0.9
LOCK_EXPIRY_SECONDS = 1800
LOCK_MIN_SIGNAL_DB = 3.0

class MultiChannelDetector:
    """
    Multi-frequency tag detector using FFT channelization.
    Divides SDR bandwidth into N channels and tracks each independently.
    """

    def __init__(self, config):
        """
        Initialize detector from config

        Args:
            config: Config instance
        """
        ...

    def _init_mf(self):
        """Build the matched-filter front end if enabled and usable.

        Deliberately fails soft. Every path that cannot produce a working MF
        leaves `self._mf` as None, which makes `process_samples` behave exactly as
        it did before this module existed. A field station is reachable only over
        cellular, so an exception here must never be able to stop it detecting.
        """
        ...

    def _create_channels(self):
        """Create frequency channel definitions.

        When a known-frequency whitelist is configured, place one channel
        *centered on each known tag frequency* instead of using a blind
        uniform comb. A uniform comb tiles the band at fixed boundaries, so a
        tag that happens to land on a channel seam is split across two windows
        — its true peak is never measured, and the CW-bandwidth check (which
        needs that peak to reject razor-thin carriers) is defeated. That is
        exactly how a continuous carrier sitting on the 151.360/151.380 seam
        masqueraded as a 151.370 MHz "tag". Centering each known frequency
        guarantees no tag sits on a seam and makes the per-channel peak /
        bandwidth measurement accurate.

        Non-whitelisted frequencies are rejected downstream by
        _is_frequency_whitelisted(), so replacing the comb loses no operational
        capability when a whitelist exists. Fall back to the comb only when no
        known frequencies are configured (backwards compatible / discovery).
        """
        ...

    def process_samples(self, samples: np.ndarray, t_read_start: float=None) -> List[Dict]:
        """
        Process IQ samples and detect pulses across all frequency channels.

        Args:
            samples: Complex IQ samples from SDR

        Returns:
            List of detected pulse events
        """
        ...

    @property
    def _survey_z_pool(self):
        ...

    def _survey_pool(self):
        """The filled part of the null ring (order is irrelevant to the fit)."""
        ...

    def _survey_push(self, z):
        ...

    def _survey_stft(self, samples, S, power_spectrum, abs_freqs, t_read_start):
        """Pulse-matched survey statistic with a per-frame CFAR gate.

        For every channel: a sliding mean over k consecutive segments (k = the
        pulse length in hops, 19 for a 19 ms pulse at the 1 ms hop) is taken
        PER BIN, and the statistic is its maximum over (bin, window). That is
        a matched filter in the time-frequency plane at 500 Hz resolution: the
        pulse's energy is collected over its own duration in its own bin
        instead of being averaged with 108 ms of silence and 39 empty bins.
        The reference is the frame's own remaining cells (rows outside +/-k
        of the peak, bins outside +/-2), thousands of them, so the noise mean
        and its spread are measured every frame with no history lag. The gate
        follows from the measured spread (k_eff = mean^2/var), the number of
        looks, and survey_pfa. Same stage buckets, same carrier guard, same
        cooldown, same bandwidth and whitelist gates as the Welch engine.
        """
        ...

    def _mf_fold_tick(self, now=None):
        """Run the fold when due. Returns tag-shaped dicts for confirmations.

        Folded evidence REPORTS a tag but does not lock it by default: it says
        "something periodic is here at this period", which is a weaker and
        differently-shaped claim than "these individual pulses were detected".
        """
        ...

    def _merge_adjacent_pulses(self, pulses: List[Dict]) -> List[Dict]:
        """Merge pulses from adjacent channels, keeping only the strongest"""
        ...

    def _is_frequency_whitelisted(self, frequency_hz: float) -> bool:
        """
        Frequency whitelist check — reject pulses not near a known tag frequency.

        Checked at pulse level (before pattern validation) to prevent noise on
        non-tag frequencies from accumulating validator state. Tolerance is ±2 kHz,
        matching tRackIT's standard for VHF tag identification by frequency.

        Args:
            frequency_hz: Detected frequency in Hz

        Returns:
            True if the frequency is allowed, False if it should be rejected
        """
        ...

    def _frequency_provenance(self, frequency_hz: float) -> str:
        """Where the claim that this frequency matters came from."""
        ...

    def _check_signal_bandwidth(self, power_spectrum: np.ndarray, abs_freqs: np.ndarray, channel_mask: np.ndarray) -> Tuple[bool, float]:
        """
        Change 4: Validate signal bandwidth to reject false positives.

        A tag pulse is keyed CW, so its 3 dB bandwidth is set by the pulse
        DURATION (~0.886/T: about 47 Hz for a 19 ms pulse), not by any fixed
        channel width. The measured width therefore collapses to one or two FFT
        bins whenever the analysis resolution is coarser than that, which is why
        the narrow-side bound is expressed in bin widths rather than Hz.
        - Signals spanning a single bin are artefacts (spurs, DC leakage).
        - Signals wider than 15 kHz are broadband noise or wideband interference.

        Args:
            power_spectrum: Full FFT power spectrum (linear power, not dB)
            abs_freqs: Absolute frequencies corresponding to each FFT bin
            channel_mask: Boolean mask for bins within the current channel

        Returns:
            Tuple of (is_valid, bandwidth_hz).
            If bandwidth cannot be determined, returns (True, 0.0) to avoid
            blocking legitimate detections on edge cases.
        """
        ...

    def _new_validator(self, ghost_threshold=1.0):
        """Build a PatternValidator from config rather than hardcoded numbers.

        Every call site used literals, which is why the [PatternValidation]
        section had no effect on anything.
        """
        ...

    def _process_pulse_pattern(self, pulse: Dict) -> Optional[Dict]:
        """
        Process pulse through pattern validator

        Args:
            pulse: Detected pulse event

        Returns:
            Validated tag dict or None
        """
        ...

    def get_active_tags(self, max_age_seconds: float=120.0) -> List[Dict]:
        """Get list of currently active tags.

        Locked tags show until they expire (LOCK_EXPIRY_SECONDS).
        Unlocked tags are filtered by age.
        """
        ...

    def cleanup_stale_tags(self, max_age_seconds: float=300.0):
        """Remove stale tags. Locked tags expire after LOCK_EXPIRY_SECONDS (2 hours)."""
        ...

    def remove_tag_by_frequency(self, frequency_mhz: float) -> bool:
        """Remove a tag by its frequency (used for 'Retrieved' button)

        Args:
            frequency_mhz: Frequency in MHz to remove

        Returns:
            True if tag was found and removed, False otherwise
        """
        ...

    def get_noise_floor(self) -> Optional[float]:
        """Get average noise floor across all channels"""
        ...

    def drain_stage_counts(self) -> Dict[str, int]:
        """Return the stage counters since the last drain, and reset them.

        Deltas, not lifetime totals: over a cellular link only the change is
        worth the bytes, and a delta answers "what is happening now" while a
        running total is dominated by whatever the station did last week.
        """
        ...

    def get_stats(self) -> Dict:
        """Get detector statistics"""
        ...
