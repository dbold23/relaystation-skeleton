"""
Analytical / ML-grade pulse capture — with two-sided time context.

When the detector approves a pulse, saves a self-describing training record:
  - img       : uint8 log-power spectrogram (human review on /review)
  - iq         : narrowband complex64 snippet, mixed to baseband at the channel
                 freq and decimated to ~IQ_RATE_HZ. Lossless enough to recompute
                 ANY feature or train a CNN on the real signal later.
  - feats      : engineered feature vector (see FEATURE_NAMES) for tabular ML.
  - meta json  : freq, snr, power, baseline, noise floor, whitelisted, sample_rate,
                 iq_rate, db scale — everything to interpret it.

CONTEXT: a detection can land anywhere in a 128 ms read, so a single read clips
the pulse against the top/bottom of the waterfall. We buffer reads and frame
each capture as [tail of previous read | the pulse's read | head of next read]
(~256 ms), so the detection is always centred with lead-in AND trail-out — never
cut off. This defers a capture by one read: the detector calls context_tick()
once per read (flushes the prior read's captures with trailing context, rotates
the buffer), and context_flush() at shutdown for the final read.

Storage stays cheap: img ~5 KB + iq (~32 KB) + json. Hard caps below.
Everything is exception-guarded — capture must never break detection.
"""
import json
import os
import time
import logging
import numpy as np
MAX_PER_HOUR = 150
MAX_TOTAL = 4000
N_TIME = 128
HALF_BW_HZ = 10000
IQ_RATE_HZ = 16000
CONTEXT_FRAC = 0.5

def _under_budget():
    ...

def _narrowband_iq(samples, sample_rate, offset_hz):
    """Mix `offset_hz` to baseband and decimate to ~IQ_RATE_HZ (anti-aliased)."""
    ...

def _features(band_db, inst_power, meta):
    """Engineered features (real-RF, recomputable from iq later too)."""
    ...

def _render_and_save(samples, sample_rate, sdr_center_hz, channel_hz, meta):
    """Render one (already context-framed) sample window and persist it."""
    ...

def save_capture(samples, sample_rate, sdr_center_hz, channel_hz, meta):
    """Queue a capture for the pulse just detected in THIS read. It is rendered
    on the NEXT context_tick(), framed with lead-in from the previous read and
    trail-out from the next — so the detection is never clipped. Returns None
    (the actual write is deferred by one read)."""
    ...

def _flush(cur):
    """Render every pending capture, framing it with `cur` as trailing context."""
    ...

def context_tick(cur_samples):
    """Call once per read, at the START of processing. Flushes the previous
    read's captures (now that this read supplies their trail-out) and rotates
    the lead-in buffer. Cheap: one copy + the deferred renders."""
    ...

def context_flush():
    """Flush any captures still pending (e.g. at shutdown) with no trail-out."""
    ...
