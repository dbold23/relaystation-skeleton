"""Narrowband matched-filter front end with period-folded integration.

Why this exists
---------------
`core.detector.MultiChannelDetector.process_samples()` is a wideband power-change
detector: it means the Welch PSD over a 20 kHz channel and looks for a few dB of
rise over a rolling median. That fights a 19 ms pulse using 20 kHz of noise
bandwidth. A matched filter on the same pulse needs about 53 Hz. On a realistic
1.6 km link the 20 kHz channel yields roughly -2 dB SNR where a 53 Hz matched
filter yields +32 dB, so the detector, not the antenna or the gain, sets the
range.

This module supplies the two things that close that gap:

  1. A per-tag NARROWBAND matched filter. Expected gain ~20 dB. (Not the 26 dB
     the raw 20 kHz -> 53 Hz bandwidth ratio suggests: the matched filter makes
     roughly 9x more independent decisions per second, so at equal false-alarm
     rate it must run a higher threshold in relative terms and pays about 5 dB
     back.)
  2. PERIOD-FOLDED integration across the pulse train. Expected gain ~13 dB at
     N = 35 pulses: non-coherent integration of N looks buys 5*log10(N) = 7.7 dB,
     not 10*log10(N) (that is the high-per-pulse-SNR limit, which is by
     definition not the regime that sets range), plus about 5 dB from collapsing
     the search from thousands of independent looks per minute down to ~90 phase
     cells times ~40 period trials.

Everything here is pure numpy. scipy is used opportunistically for its faster
single-precision FFT and is never required, because
`scripts/safe_update.py::_import_check()` imports the detector BEFORE applying an
over-the-air update: a hard scipy dependency would make OTA refuse to apply on
any station lacking it, which is precisely the station you need to fix remotely.

Design notes worth not rediscovering
------------------------------------
* The template is a BOXCAR, not a Hann window. A tag pulse mixed to DC is a
  rectangular CW burst, so a normalised boxcar IS its matched filter. Using
  `np.hanning` instead costs 10*log10(2/3) = 1.76 dB, because
  |<hann,rect>|^2 / (||hann||^2 ||rect||^2) = (M/2)^2 / ((3M/8) * M) = 2/3.
* Decimation is an FFT crop, not a FIR. Selecting the crop centred on the
  carrier bin mixes to DC *and* decimates in one step: no mixer, no filter taps,
  no scipy, and no filter-transition loss.
* Once the carrier is at DC the matched filter is a sliding sum, computable from
  a cumulative sum in O(N) with NO FFT and, unlike an STFT, with zero scalloping
  loss in frequency and zero straddle loss in time.
* The detection statistic is normalised so that under noise it is Exp(1) with
  mean exactly 1.0. That is what makes a false-alarm probability quotable, and
  `mean(z)` is therefore the single most valuable runtime health metric here: if
  it is not 1.00 +/- 0.02 the false-alarm arithmetic is wrong and every gate
  derived from it is meaningless.

Ported from verified references (see tests, which diff against them directly):
`RELAY/datasets/home_ladder_20260724/build_dataset3.py` (`decimate_all`,
`cw_template`, `matched_filter`, `medfilt1`, `characteristic_periods`),
`RELAY/datasets/listen_test/listen_analyze.py` (autocorrelation period search and
epoch fold), `RELAY/darwin-relay/core/detector.py` (carrier-offset EMA
discipline, impulse veto, peak blanking).
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from core.mf_dsp import _fft, _ifft, HAS_SCIPY_FFT, crop_decimate, OverlapDecimator, boxcar_mf_power, stft_mf_bank, parabolic_refine, _os_scale, LOWER_HALF_MEAN_EXP1, noise_from_pool, cfar_noise, blanked_peaks, impulse_ratio, autocorr_period, bin_series, calibrate_bin_noise, fold, _smooth
from core.mf_fold import PulseFolder, fold2d, BankFolder

class _Done:
    """A finished 'future' for the inline path: runs the call at once."""

    def __init__(self, fn, *args):
        ...

    def done(self):
        ...

    def result(self):
        ...

class TrackedTag:
    """Per-tag state: carrier estimate, MF continuity, fold ring."""

    def __init__(self, freq_hz, channel_index, pulse_width_ms, drate, folder_kwargs=None):
        ...

    @property
    def nu(self):
        ...

class MFFrontEnd:
    """Narrowband matched filter + fold for a set of tracked frequencies.

    Call `process(iq, t_read_start)` once per SDR read and `fold_decisions(now)`
    on a slower cadence.

    `t_read_start` must be the WALL-CLOCK time of the first sample in this read.
    Measured on pi3: reads are not contiguous (median 19.9 ms gap, 86.6%
    airtime), so a cumulative sample counter runs 13% slow and its error
    accumulates -- over 10 minutes it reported the beacon period as 1.4795 s
    instead of 1.7155 s. Anchoring every read independently to the wall clock
    recovered 1.715155 s over the same span, because that error is bounded by
    scheduling jitter instead of accumulating.

    The crop stays centred on each tag's NOMINAL frequency and the measured
    carrier error is removed by a small residual mix in the decimated domain.
    Re-tuning the crop instead would reset the overlap-save buffers on every
    update, and the crop grid is 7.8 Hz, so there is nothing to gain by it.
    """

    def __init__(self, sample_rate, center_freq, dec=128, pulse_width_ms=19.0, pulse_gate_db=11.5, cfar_q=0.5, max_tracked=8, stride=1, carrier_search_hz=2500.0, carrier_ema_alpha=0.3, carrier_min_prominence=6.0, carrier_lock_hits=3, acq_pfa=0.001, impulse_spike_ratio=25.0, max_peaks=3, nu_history=100, frame_budget_ms=45.0, fold_enabled=True, folder_kwargs=None, pulse_cooldown_sec=0.5, track_gate_db=None, track_window_sec=0.025, wide_period_tol_sec=0.003, fold_async=False):
        ...
    CLICK_GUARD_SEC = 0.06
    CLICK_MAX_SEC = 0.005
    CLICK_SLICES = 3
    CLICK_INBAND_DOMINANCE = 100.0

    def _pick_click_slices(self, offsets_hz):
        """Passband offsets for the click detector: one crop width each, far
        from DC and from every tracked carrier, spread across the band.

        The click statistic used to be max/median of the raw read decimated
        by plain subsampling, which folds the whole passband onto itself: a
        strong tag's OWN 19 ms pulse then cleared the 25x ratio and vetoed
        itself, so the matched filter went deaf to any tag above about
        +24 dB in-channel, i.e. to a tag held near the antenna, which is
        exactly how a station is checked. Read the impulse off slices that
        contain no tag instead: a broadband click is in every slice at the
        same instant and at the same ratio to the slice's own noise; a tag
        pulse is in none of them.
        """
        ...

    def _click_mask(self, n_dec):
        """Boolean mask over the emitted block's decimated samples marking
        those within CLICK_GUARD_SEC of a broadband click, or None when there
        is none. Computed once per read (the slices are shared by every tag)
        from the decimator's out-of-band slices of the guarded block, so a
        click in the 8 ms guard on either side of the read, which the crop
        rings into the block's edges, is seen as well."""
        ...

    def _click_instants(self, n_dec):
        """Find the click instants for this read and cache
        (key, mask, instants, slice_power): instants in block coordinates,
        slice_power the median across slices of the power at each."""
        ...

    def _mask_from_instants(self, inst, n_dec):
        ...

    def _tag_click_mask(self, tag, base):
        """This tag's click mask: the read's click instants minus those the
        tag's own in-band power dominates (its keying transients). Judged on
        the untrimmed block so an instant in the 8 ms guard on either side,
        where a straddling pulse continues, is judged too."""
        ...
    NU_WARMUP = 64
    UNLOCK_AFTER_WINDOWS = 3.0

    def set_tracked(self, entries):
        """`entries` is an iterable of (freq_hz, channel_index[, width_ms])."""
        ...

    @property
    def active(self):
        ...

    def process(self, iq, t_read_start):
        """Returns a list of MF pulse dicts (may be empty)."""
        ...

    def _process_tag(self, tag, base, start_dec, emitted):
        ...

    def _threshold_for(self, tag, t):
        """Per-sample gate: the full gate, lowered where a pulse is predicted.

        Predictions come from the fold's last CONFIRMED decision and are used
        only while it is fresh (younger than the fold window). The fold's
        phase is a cell on the bin grid anchored at the epoch, so a predicted
        arrival is epoch + n*P + (cell + 0.5)*bin, and the window is widened by
        one bin to cover the cell's own width.
        """
        ...

    def _bank(self, tag, base):
        """STFT matched-filter bank over the carrier search band.

        Returns ``(band_hz, power, starts)`` with `power[frame, bin]` restricted
        to |offset| <= carrier_search_hz, or None. One transform per unlocked
        tag per read; both acquisition routes read from it.
        """
        ...

    def _wide_feed(self, tag, bank, t_start):
        """Feed the carrier bank into the acquisition fold, one row per bin.

        Each 16 ms bin gets the mean over its frames of the normalised bank
        power across the whole carrier band, so the fold can integrate every
        carrier hypothesis at once. The frame time is the WINDOW START, the
        same convention as the narrow statistic, so a phase found here
        predicts arrivals there.
        """
        ...

    def _lock_from_wide(self, tag, d, now):
        """Lock the narrow filter on the carrier the acquisition fold found."""
        ...

    def _acquire(self, tag, bank, t_start):
        """STFT bank -> parabolic refine -> prominence-gated EMA."""
        ...

    def _fold_feed(self, tag, z, t):
        """Bin z onto the absolute wall-clock bin grid and hand it to the fold."""
        ...

    def _pool(self):
        ...

    def close(self):
        """Stop the fold worker. Pending results are dropped."""
        ...

    def _fold_submit(self, now, force=False):
        """Start a decision for every tag that is due and not in flight.
        `force` makes every tag due now (tests and one-off diagnostics)."""
        ...

    def _fold_collect(self, now, wait=False):
        """Apply every finished decision (every decision, with `wait`).
        Returns confirmations."""
        ...

    def fold_decisions(self, now=None, force=False, wait=False):
        """Advance the fold scheduler: apply finished decisions, start the
        ones that are due. Call once per read; it is cheap when nothing is
        due. Returns confirmations. Inline (fold_async=False) the decision
        started on this call is also returned on this call; `wait` does the
        same for the worker path by blocking on it; `force` makes every tag
        due now."""
        ...

    def _note_frame(self, dt):
        ...

    def stats(self):
        ...
