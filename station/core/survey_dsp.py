"""Survey DSP for core.detector: the Welch and segment spectrograms, the
survey's CFAR gate (model and pooled), and the constants that fix the
survey's resolution and stage partition.

Split out of core/detector.py on 2026-09-23 with no change to any line of code:
every OTA file must stay under the server's 128 KB per-file limit, and
detector.py had reached 109 KB of it. core/detector.py re-exports every name
defined here, so `from core.detector import X` keeps working for every X it
ever offered. tests/test_ota_file_budget.py holds each file to a budget below
the limit so the next split happens with room to spare, not at the cliff.
"""
import numpy as np

def welch_psd(samples, fs, nperseg):
    """Welch power spectrum, using scipy when available and numpy otherwise.

    The two paths MUST agree. The old numpy fallback took a single windowed FFT
    over the whole read, giving 7.8 Hz bins instead of Welch's 500 Hz — a 64x
    resolution change that silently inverted the detector's bandwidth gate (a
    19 ms CW pulse is only ~47 Hz wide, so at fine resolution every real pulse
    measured "too narrow" and was thrown away as CW interference). Detection
    then depended on whether scipy happened to be installed. Matching nperseg
    here is what makes the fallback safe, so any change to the scipy call must
    be mirrored below.

    Mirrors scipy.signal.welch(window='hamming', noverlap=nperseg//2,
    return_onesided=False, scaling='spectrum'), including the two details that
    are easy to miss: scipy's 'hamming' is the PERIODIC window (np.hamming is
    symmetric), and welch detrends each segment by its mean.
    """
    ...

def segment_spectrogram(samples, fs, nperseg):
    """Per-segment power spectra, the pieces Welch averages.

    Returns ``(freqs, S)`` with ``S[j, b]`` the power of segment j in bin b,
    windowed, detrended and scaled exactly as `welch_psd`'s numpy path, so
    ``S.mean(axis=0)`` IS the Welch spectrum. Kept in numpy on purpose: this
    is what the survey detector's pulse-matched statistic is built from, and
    it must not depend on whether scipy is installed.
    """
    ...

def _norm_isf(p):
    """Standard normal upper-tail quantile (Acklam), numpy only."""
    ...

def gamma_isf_scaled(p, shape):
    """Upper quantile of Gamma(shape) with mean 1, by Wilson-Hilferty.

    Measured against scipy over shape 3..40 and p 1e-3..1e-9: within +7% at
    the worst corner (shape 3, p 1e-9) and within +1% for shape >= 10, always
    on the conservative side. Numpy only, for the same reason as above.
    """
    ...
SURVEY_LOOKS_FACTOR = 40.0
SURVEY_NULL_POOL = 4000
SURVEY_NULL_MIN = 500

def survey_gate(pfa, k_eff, n_looks):
    """Model CFAR gate for the pulse-matched survey statistic, as a ratio to
    the reference mean.

    The statistic is the mean of k overlapping segment powers, which under
    noise is close to Gamma(k_eff) with mean 1 where k_eff is MEASURED from
    the reference cells as mean^2/var; the maximum over the channel-frame
    exceeds the gate with probability about looks * P(one exceeds), so the
    gate is the Gamma quantile at pfa/looks. Derived from the look count and
    a target false-alarm rate, never from a number that worked elsewhere,
    and used only until `survey_gate_from_pool` has enough of the station's
    own maxima to fit.
    """
    ...

def survey_gate_from_pool(pool, pfa):
    """Gate from the station's own channel-frame maxima (normalised by each
    channel's reference mean, so they pool across channels and across noise
    levels). Gumbel by robust moments: location from the median, scale from
    the interquartile range, so a tag pulsing in one channel of twenty-five,
    or one channel held by a carrier, cannot move the fit. Returns None when
    the pool is shallow."""
    ...

def _parabolic(y, i):
    """Sub-bin peak offset (bins) from a 3-point log-parabolic fit."""
    ...
SURVEY_NPERSEG = 4096

def survey_nperseg(sample_rate: float) -> int:
    """FFT segment length giving SURVEY_BIN_HZ bins at this sample rate,
    even (the hop is half a segment) and never below 64. Exactly
    SURVEY_NPERSEG at 2.048 Msps."""
    ...
