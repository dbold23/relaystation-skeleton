"""
Continuous band-power waterfall for environmental characterization + ML
background modeling.

Every SURVEY_INTERVAL_SEC, downsamples the detector's full-band power spectrum
to N_BINS and appends one quantized (int8 dBFS) row to spectrum/waterfall.jsonl.
The frequency axis + dB scale are written once to spectrum/axis.json, so the
whole night reconstructs to a (time x freq) matrix in a couple of lines:

    axis = json.load(open('spectrum/axis.json'))
    rows = [json.loads(l) for l in open('spectrum/waterfall.jsonl')]
    Z = np.array([r['db'] for r in rows]) * axis['scale'] + axis['offset']

Compact: N_BINS int8 + ts per row (~0.5 KB), ~30 s cadence -> ~1 MB/night.
Exception-guarded; the survey must never break detection.
"""
import json
import os
import time
import logging
import numpy as np
SURVEY_INTERVAL_SEC = 30
N_BINS = 512
BAND_LO_HZ = 151100000.0
BAND_HI_HZ = 151500000.0
DB_OFFSET = -120.0

def maybe_log(power_spectrum, abs_freqs):
    """Called every read; actually writes at most once per SURVEY_INTERVAL_SEC."""
    ...
