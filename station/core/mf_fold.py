"""Period-folded integration for core.mf_frontend: PulseFolder (the
self-calibrating fold of one locked tag), fold2d and BankFolder (the
acquisition fold across every carrier bin of the bank).

Split out of core/mf_frontend.py on 2026-09-23 with no change to any line of code:
every OTA file must stay under the server's 128 KB per-file limit, and
mf_frontend.py had reached 105 KB of it. core/mf_frontend.py re-exports every name
defined here, so `from core.mf_frontend import X` keeps working for every X it
ever offered. tests/test_ota_file_budget.py holds each file to a budget below
the limit so the next split happens with room to spare, not at the cliff.

The design notes for the whole chain are in core/mf_frontend.py's docstring.
"""
import time
import numpy as np
from core.mf_dsp import _smooth, autocorr_period, fold

class PulseFolder:
    """Rolling period-folded integrator for one tag.

    Holds a window of the binned detection statistic and, on request, searches a
    narrow band of trial periods for a coherent phase cell.

    The period is FITTED, never assumed. Measurements of this tag span
    1.7151-1.7172 s; 2.1 ms of period error accumulates 74 ms of phase over 35
    periods, which is four pulse widths, so an assumed period smears the fold
    peak away to nothing.

    On `bin_sec`: 16 ms, not the 4 ms first assumed. Measured on pi3 with a
    strong tag, the pulse arrival residual about a fitted straight line is
    ~6 ms rms, dominated by when Python regains control after `read_samples()`
    returns rather than by the tag (which is crystal controlled). A bin finer
    than the timing uncertainty just splits one pulse across neighbouring cells.
    16 ms is also exactly 256 samples at the 16 kHz decimated rate.

    On `sigma_gate`: the fixed gate is 11.0 in the statistic's own units (the
    smoothed fold has unit variance under noise; the earlier 6.5 was the same
    gate in a convention that divided the 3-cell sum by 3 instead of sqrt(3)).
    Against IDEAL Exp(1) noise the measured null peak sits around 5-7, and a
    Gumbel fit puts the gate for 1 false alarm per hour well below 11 (see
    tests/test_mf_frontend.py::test_calibrate_sigma_gate_for_one_false_alarm_per_hour).
    The fixed default therefore carries several dB of headroom, deliberately.

    Do NOT lower it on the strength of that number. Real z on real RF has a far
    heavier tail than Exp(1): impulsive interference, a drifting noise floor and
    co-channel carriers all break the model, and this project already has the
    scar for trusting a synthetic null -- offline weak-pulse mining scored AUC
    0.51, pure noise, until a self-calibrated reality gate was added. The gate
    must be set from the measured false-alarm rate on the real tag-free captures,
    at which point up to ~4.7 dB is available to claim. That is what
    `gate_mode='auto'` now does, continuously, on the station itself.

    On `gate_mode`: 'fixed' applies `sigma_gate` as shipped. 'auto' measures the
    null on the station's OWN statistic, every decision, and derives the gate
    from that measurement and a target false-alarm rate. The measurement is a
    block-shuffled surrogate: the observed series is cut into blocks of
    `period_min` and each block is circularly rolled by an independent random
    offset. That keeps every sample, the marginal distribution, the heavy tail
    and any burst shorter than a block, and destroys only the one thing a
    beacon has -- phase coherence across periods. Running the surrogate through
    the identical search (autocorrelation, both scan stages, smoothing, the
    maximum over cells) yields one draw from the null of the maximum statistic,
    for THIS noise, under THIS search. A pool of those draws, fitted with a
    Gumbel (the right family for a maximum over many light-tailed cells), gives
    the gate at the target Pfa per decision. `sigma_floor` and the largest
    pooled null value are hard floors under the fit, because the fit is an
    extrapolation and real RF grows a heavier tail than any 300 draws show.

    A real signal contaminates the surrogate UPWARD, never downward: after
    rolling, its pulses land in random cells, so a strong tag lifts the null by
    a few sigma while its own coherent fold sits tens of sigma higher. A weak
    tag (the regime that sets range) lifts it by less than the noise spread.
    The bias is therefore in the safe direction and only visible when it does
    not matter. `clip_z` bounds a single sample's contribution to the fold so
    one impulsive click cannot lift either the real peak or the null.
    """

    def __init__(self, bin_sec=0.016, window_sec=60.0, period_prior=1.7155, period_min=0.8, period_max=3.0, period_trials=41, sigma_gate=11.0, min_folds=8, min_coverage=0.25, smooth_bins=3, bin_mu=1.0, bin_var=1.0, gate_mode='fixed', target_fa_per_hour=1.0, decision_sec=10.0, sigma_floor=5.0, n_surrogates=2, null_pool_size=300, null_min_pool=30, clip_sigma=9.0, seed=0, auto_moments=False, confirm_votes=2, confirm_window=3, confirm_spacing_sec=None):
        ...

    @property
    def _idx(self):
        ...

    @property
    def _z(self):
        ...

    def add(self, bins, z):
        """Append values at explicit absolute bin indices.

        Indices are explicit, not implied by position, because the receiver only
        listens ~87% of the time (measured) and so the binned series genuinely
        has holes. Treating it as contiguous would slide every later sample
        earlier and destroy the phase coherence the fold depends on.

        `bins` may also be a scalar first index, in which case `z` is taken as
        contiguous from there.
        """
        ...

    def reset(self):
        """Forget the buffered series and the last decision (not the null)."""
        ...

    @property
    def n_samples(self):
        ...

    def _dense(self):
        """The buffered series on a dense bin grid: ``(lo_i, dense, mask)``."""
        ...

    def _dense_from(self, idx, z):
        ...

    def _search(self, lo_i, dense, mask, period_hint=None):
        """The whole search on one dense series. Returns the best dict or None.

        Shared by the real decision and by every surrogate, which is the point:
        a null draw is only a null draw for THIS statistic if it went through
        exactly the same autocorrelation, scan stages, smoothing and maximum.
        """
        ...

    def _surrogate(self, dense, mask, rng=None):
        """Block-shuffled copy: each `period_min` block rolled independently.

        Rolling is circular WITHIN a block, so nothing is discarded and a burst
        shorter than a block survives intact; only the phase relation between
        blocks is destroyed, which is exactly what a beacon has and noise does
        not. Observed and unobserved bins roll together so the airtime pattern
        of the surrogate matches the real series.
        """
        ...

    def _gate_from_pool(self):
        """Gate at the target Pfa per decision, from the pooled null maxima.

        Three rules, each pinned by a measurement:

        * While the pool is shallower than `null_min_pool` the fixed gate
          stands, but never BELOW what the null has already been seen to
          reach. Every false alarm measured on heavy-tailed noise came in the
          first fifteen decisions, when the pool already held maxima of 7.6-8.4
          and the fixed 6.5 was still in force.
        * Once deep, a Gumbel by moments gives the quantile at the target
          Pfa, widened by two standard errors of that quantile
          (se ~ scale*sqrt(33/n) at p ~ 3e-4). An extrapolation from 300
          draws to a 1-in-3600 event is only honest with its uncertainty on.
        * Never below the seen maximum plus one scale unit, because on a
          heavy tail the moment fit under-reads; that floor is what measured 0
          false alarms where the fixed gate measured 71 per hour.
        """
        ...

    def decide(self, period_hint=None):
        """Search for a folded periodic signal. Returns a dict or None.

        ``decide()`` is ``apply(compute(prepare()))``: `prepare` snapshots the
        series on the caller's thread, `compute` is the whole search plus the
        surrogates and touches no shared state (it may run on a worker
        thread), and `apply` folds the result into the null pool, the gate
        and the persistence vote back on the caller's thread. Measured:
        eight tags' decisions back to back cost 0.5 to 0.9 s every 10 s
        inside the detection loop, during which the SDR streams into
        nothing; off the loop they cost airtime nothing.
        """
        ...

    def prepare(self, period_hint=None):
        """Snapshot for one decision, or None while the series is too short.
        Counts ROWS: the bank folder's series is 2-D and its element count
        passed the four-period guard after three rows."""
        ...

    def compute(self, job):
        """The search and its surrogates on a snapshot. Thread-safe: reads
        only the job and the folder's fixed parameters."""
        ...

    def apply(self, res):
        """Fold a computed result into the folder's state. Returns the
        decision dict when the source is confirmed and stable, else None. A
        result from before a reset() is dropped."""
        ...

    def _scan(self, idx, z, trials, ac_score, span_sec, best=None):
        ...

def fold2d(bin_index, Z, bin_sec, period_sec, mu=1.0, var=1.0):
    """Epoch-fold every column of `Z` (time bins x carrier bins) at once.

    Returns ``(G, counts)`` with ``G[cell, f]`` normalised exactly as `fold`
    normalises its one column: mean 0, variance 1 per cell under noise of
    per-bin mean `mu` and variance `var`. Rows are grouped by cell with one
    sort and one `add.reduceat`, so the cost is one pass over the matrix per
    trial period regardless of how many carrier bins there are.
    """
    ...

class BankFolder(PulseFolder):
    """Period fold over the whole carrier bank: the acquisition detector.

    Why it exists: a matched filter needs the carrier to within ~20 Hz or a
    19 ms pulse adds up out of phase (measured: a 97 Hz error left the pulses
    at z = 1.5, invisible). The single-pulse acquisition gate needs one pulse
    at z > 15 to find that carrier, which a tag at range never provides. So
    the two things a weak tag CAN provide, a known period and many pulses, are
    used to find the carrier instead: fold every carrier bin of the STFT bank
    at the beacon period and take the maximum over (phase, carrier). Measured
    on the front end's own bank output: where the 1-D max-over-bins statistic
    folded to 2.1 sigma, this reached 18.7 sigma against a null maximum of
    6.2, read the carrier to within 13 Hz, and still reached 7.6 sigma two
    amplitude steps lower. The cost is a bounded search: `period_tol_sec`
    around `period_prior` (the tag family's measured spread is 2 ms), plus,
    when the bank's row-maximum series shows strong autocorrelation, trials
    around that period too, so an unfamiliar period is still found if it is
    strong enough to show up in the 1-D statistic.

    Shares the surrogate-null gate with `PulseFolder`; the surrogate rolls
    whole rows, so every carrier bin is de-phased together.
    """

    def __init__(self, n_bins, period_tol_sec=0.003, max_trials=15, smooth_bins=2, **kw):
        ...

    def add(self, bins, rows):
        ...

    def _dense_from(self, idx, z):
        ...

    def _trials(self, span_sec, dense, mask):
        """Period trials: the prior band, plus the 1-D autocorrelation seed."""
        ...

    def _search(self, lo_i, dense, mask, period_hint=None):
        ...
