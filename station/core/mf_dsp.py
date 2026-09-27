"""Matched-filter DSP for core.mf_frontend: FFT-crop decimation, the boxcar
matched filter and its STFT bank, Exp(1) noise normalisation, peak picking,
impulse detection, the autocorrelation period search and the 1-D fold.

Split out of core/mf_frontend.py on 2026-09-23 with no change to any line of code:
every OTA file must stay under the server's 128 KB per-file limit, and
mf_frontend.py had reached 105 KB of it. core/mf_frontend.py re-exports every name
defined here, so `from core.mf_frontend import X` keeps working for every X it
ever offered. tests/test_ota_file_budget.py holds each file to a budget below
the limit so the next split happens with room to spare, not at the cliff.

The design notes for the whole chain are in core/mf_frontend.py's docstring.
"""
import numpy as np

def crop_decimate(iq, offsets_hz, sample_rate, dec, spectrum=None, t0=0):
    """Mix each offset to DC and decimate by `dec`, via one shared FFT.

    `iq` must be a whole multiple of `dec` long. Returns
    ``{offset_hz: complex64 array of len(iq)//dec}``.

    This is `build_dataset3.decimate_all` reduced to a single block. Taking the
    FFT once and cropping it per carrier costs one transform regardless of how
    many tags are tracked, which is what makes tracking 8 frequencies affordable
    inside a 128 ms read.

    `t0` is the absolute sample index of `iq[0]`. It matters because an FFT crop
    mixes with a phase reference LOCAL TO THE BLOCK: a tone at the crop centre
    comes out with the phase it had at `iq[0]`, so concatenating blocks that each
    reset to zero phase yields a stream with a phase jump at every boundary. That
    would make a pulse straddling a read boundary add incoherently, defeating the
    whole point of carrying samples over, and it puts a discontinuity at the read
    rate -- a periodic artefact, in a detector that integrates periodically.
    Rotating by the phase the mixer would have accumulated up to `t0` removes it.

    The crop is still CIRCULAR, so the block ends wrap. Callers wanting a
    gap-free timeline should use `OverlapDecimator`, which discards that edge.
    """
    ...

class OverlapDecimator:
    """Overlap-save wrapper around `crop_decimate` for a continuous stream.

    An FFT crop convolves circularly with a brick wall, which is NON-CAUSAL, so
    it contaminates BOTH ends of every block with the opposite end. A guard on
    the leading edge alone leaves an error of about 25% of rms in the last dozen
    outputs of every read -- measured. That is a defect at the read rate, in a
    detector whose entire premise is integrating anything periodic, so it is
    exactly the artefact that must not exist.

    Therefore guard symmetrically: decimate ``[prev_tail | read | next_head]``
    and emit only the middle. That costs ONE READ of latency (128 ms), which is
    nothing against a 1.7 s beacon, and it is why `process()` returns the
    PREVIOUS read's samples together with their absolute start index rather than
    the samples just handed in. Call `flush()` at the end of a stream.
    """

    def __init__(self, offsets_hz, sample_rate, dec, overlap=None, aux_offsets_hz=None):
        ...

    def set_offsets(self, offsets_hz):
        """Retune. Drops buffered state, so the next emit has a contaminated edge."""
        ...

    def set_aux_offsets(self, offsets_hz):
        """Re-point the click slices. Needs no buffered state."""
        ...

    def _empty(self):
        ...

    def _decimate_pending(self, next_head):
        """Decimate `_pending` with guards on both sides; return (start, dict)."""
        ...

    def process(self, iq):
        """Feed one read. Returns ``(start_index, {offset: samples})``.

        `start_index` is in DECIMATED samples from the start of the stream, and
        the returned samples belong to the PREVIOUS read (one-read latency). The
        first call returns an empty result.
        """
        ...

    def flush(self):
        """Emit the final buffered read, zero-padding its trailing guard."""
        ...

    @property
    def decimated_rate(self):
        ...

def boxcar_mf_power(base, n_pulse):
    """Matched-filter output POWER for a DC rectangular pulse, via cumsum.

    Returns ``|sum(base[n:n+n_pulse]) / sqrt(n_pulse)|**2`` for every n, length
    ``len(base) - n_pulse + 1``.

    The sqrt(n_pulse) normalisation is what makes the output scale-free: for
    complex noise of per-sample power s the window sum has power n_pulse*s, so
    dividing by sqrt(n_pulse) leaves mean power exactly s no matter how long the
    pulse is. That in turn is what lets one threshold serve every pulse width.

    Accumulates in float64. A sliding sum from a cumulative sum loses precision
    when the running total dwarfs the window total, and mixing the carrier to DC
    deliberately puts signal at DC, so the running total is not small.
    """
    ...

def stft_mf_bank(base, n_pulse, hop=None, zero_pad=2):
    """Matched-filter power across a BANK of carrier offsets, for acquisition.

    Returns ``(offsets_hz_normalised, power[frame, bin])`` where the offsets are
    in cycles/sample (multiply by the decimated rate to get Hz).

    A DFT of an n_pulse-long rectangular segment IS the matched filter evaluated
    at every frequency offset simultaneously: |X[k]|**2 / n_pulse is the same
    statistic `boxcar_mf_power` produces, but for offset k instead of DC. One
    small transform per frame therefore searches the whole +/-2 kHz crystal
    tolerance at once, which is how a tag is found before its carrier is known.

    `zero_pad=2` halves the bin spacing and caps worst-case scalloping loss at
    about 0.9 dB (a rectangular window's worst case is 3.92 dB at half-bin);
    `hop=n_pulse//4` caps time-straddle loss at about 1.2 dB. Both losses vanish
    once the carrier is known and the DC cumsum path takes over.
    """
    ...

def parabolic_refine(y, i):
    """Sub-bin peak offset in bins from a 3-point log-parabolic fit.

    Gives roughly 5 Hz precision from 500 Hz bins, which is what lets the crop be
    re-centred accurately enough that the coherent loss is negligible. From
    `Relay-Hybrid/core/detector.py:_refine_peak_freq`.
    """
    ...

def _os_scale(q):
    ...
LOWER_HALF_MEAN_EXP1 = 0.3068528194400547

def noise_from_pool(pool):
    """Unbiased, pulse-robust noise power from a pool of INDEPENDENT MF draws.

    A sample QUANTILE is the obvious estimator and the wrong one here. Successive
    matched-filter outputs overlap by all but one sample, so a 2048-sample block
    holds only about 2048/n_pulse = 7 independent draws, and the median of 7
    draws from a skewed distribution is biased enough to matter: it measured
    mean(z) = 1.2 instead of 1.0, i.e. every quoted false-alarm rate wrong by
    0.8 dB. Pooling independent draws across reads and using a lower-half MEAN
    fixes both the small-sample bias and the pulse sensitivity.
    """
    ...

def cfar_noise(power, n_pulse, q=0.5, guard=None):
    """Order-statistic noise-power estimate with a guard region round the peak.

    The matched-filter output stays elevated for about 2*n_pulse samples around a
    pulse, which is a large fraction of a short window, so a plain median is
    biased upward by the very signal it is meant to sit beneath. Excluding a
    guard band around the peak removes most of that bias; the caller should also
    smooth across frames, because at ~1% duty cycle a cross-frame median is
    essentially pulse-free.
    """
    ...

def blanked_peaks(z, threshold, n_pulse, max_peaks=3):
    """Indices of up to `max_peaks` peaks over `threshold`, blanking +/-n_pulse.

    A single pulse produces a correlation lobe about 2*n_pulse wide, so without
    blanking one pulse reports as many detections and the pattern validator sees
    a burst of impossible sub-millisecond intervals.

    `threshold` may be a scalar or an array the same length as `z`. The array
    form is what the predicted-arrival tracking gate uses: once the fold has
    measured a tag's period and phase, the gate is lowered only inside the
    short windows where the next pulses are due, so the extra sensitivity is
    bought with a few hundred looks per period instead of sixteen thousand.
    """
    ...

def impulse_ratio(iq):
    """max/median instantaneous power. Broadband clicks (ignition noise, relay
    chatter, a switching supply) hit every matched filter at once, so a very
    peaky window is interference rather than a tag. Darwin uses a ratio of 25."""
    ...

def autocorr_period(z, bin_sec, p_min, p_max, clip_sigma=15.0, mask=None):
    """Coarse beacon period from the autocorrelation of the binned statistic.

    `z` must be DENSE in bin index (zero-filled where unobserved) with `mask`
    marking the observed bins. Passing only the observed values and letting their
    array positions stand in for time is wrong and quietly biases the answer low:
    the receiver listens ~87% of the time, so a values-only array is compressed
    against real time and the recovered period comes out short. Measured on a
    synthetic tag: 1.656 s for a true 1.7155 s, a 3.5% error, which no amount of
    later refinement can walk back. Normalising by the mask's own
    autocorrelation corrects for the varying overlap at each lag.

    Returns ``(period_sec, score)`` where score is the peak height in units of
    the far-lag standard deviation; `listen_analyze.py` declares a periodic
    signal above about 6. Clipping first keeps one strong pulse from dominating
    the correlation.

    `p_min` should sit above the tag's power-on burst period (0.223 s for this
    tag family). That burst only fires when the tag is switched on, and a
    deployed tag is switched on before it goes out, so a station never sees it --
    but a search window that reaches down to it will happily lock a harmonic.
    """
    ...

def bin_series(z, samples_per_bin, method='mean'):
    """Reduce the per-sample statistic to one value per fold bin.

    Returns ``(binned, n_bins)``, dropping any partial final bin.

    `mean` is the right default and `max` is a trap. The maximum of k Exp(1)
    draws is Gumbel-distributed with mean H_k, so max-binning silently changes
    both the mean and the shape the fold normalisation depends on, and the quoted
    false-alarm rate stops being true. A mean keeps the mean at 1 and only
    shrinks the variance, which `calibrate_bin_noise` measures.
    """
    ...

def calibrate_bin_noise(z_noise, samples_per_bin, method='mean'):
    """Measure ``(mu, var)`` of a binned NOISE series. Do not assume them.

    Consecutive matched-filter outputs overlap by all but one sample, so the
    number of INDEPENDENT draws inside a bin is set by the pulse length, not by
    the bin length: at the measured operating point (19 ms pulse, ~16 ms bin)
    it is about one, and mean-binning therefore lands near mu = 1, var = 1. That
    is a coincidence of this configuration, not a law -- change the bin width or
    the pulse width and it moves. Measuring it is what keeps the fold's
    false-alarm arithmetic honest.
    """
    ...

def fold(bin_index, z, bin_sec, period_sec, mu=1.0, var=1.0):
    """Epoch-fold `z` at `period_sec`. Returns ``(g, sums, counts)``.

    ``g[c] = (sum[c] - count[c]*mu) / sqrt(count[c]*var)``, which has mean 0 and
    variance 1 per cell under noise of per-bin mean `mu` and variance `var`,
    regardless of how many samples landed in the cell.

    PER-CELL COUNTS ARE THE POINT. An interval the receiver never observed
    contributes to neither sum nor count, so the normalisation stays exact and
    missed pulses cost only sqrt(N_observed) instead of producing a cliff. That
    is the same principle as the folded-interval CV fix in the pattern validator:
    never let the detector be punished for its own duty cycle.

    `mu` and `var` default to the Exp(1) values, which are correct when `z` is
    subsampled rather than averaged. Pass measured values from
    `calibrate_bin_noise` whenever the series was binned by averaging.
    """
    ...

def _smooth(x, w):
    """Circular boxcar, the matched filter for a pulse in fold space.

    Normalised by sqrt(w), NOT by w, so that under white noise the output has
    unit variance whatever the width. The earlier version divided by w, which
    silently shrank the statistic by sqrt(w): a "6.5 sigma" gate on a 3-cell
    mean was really 11.3 sigma of the smoothed statistic, and a fold with a
    different width was not comparable to it at all. Works along axis 0 of a
    2-D array, which is what the carrier-bank fold needs.
    """
    ...
