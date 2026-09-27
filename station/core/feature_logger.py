"""
Feature logger for ML training data collection.

Hooks into the existing detection pipeline to log per-read feature vectors
alongside pipeline decisions. This produces "self-labeled" training data:
the existing pipeline provides labels, and the feature vectors provide inputs.

Usage:
    from core.feature_logger import FeatureLogger

    logger = FeatureLogger(output_dir='/Volumes/Relay-ml/real_data')

    # In your detection loop, after process_samples():
    logger.log_read(detector, validated_tags, timestamp)

Data format: SQLite database with one row per channel per read.
"""
import os
import time
import sqlite3
import threading
import logging
from typing import List, Dict, Optional
from datetime import datetime

class FeatureLogger:
    """
    Logs per-channel features from each SDR read for ML training.

    Captures the same 8 features per channel that the ML model uses:
      - power_db, baseline_db, change_db, bandwidth_hz
      - peak_to_mean_ratio, spectral_kurtosis, is_whitelisted
      - pipeline_detected (label from existing pipeline)

    Thread-safe: uses a write queue with periodic flush.
    """

    def __init__(self, output_dir: str='/Volumes/Relay-ml/real_data', flush_interval: int=100, max_buffer: int=10000):
        """
        Args:
            output_dir: directory for SQLite database
            flush_interval: flush to disk every N reads
            max_buffer: max buffered rows before forced flush
        """
        ...

    def _init_db(self):
        """Create database and tables."""
        ...

    def log_read(self, detector, validated_tags: List[Dict], timestamp: Optional[float]=None):
        """
        Log features from one SDR read.

        Call this after detector.process_samples() returns.

        Args:
            detector: The MultiChannelDetector instance
            validated_tags: Return value from process_samples()
            timestamp: Unix timestamp (auto if None)
        """
        ...

    def _flush(self):
        """Write buffered rows to database."""
        ...

    def close(self):
        """Flush remaining data and close."""
        ...

    def get_stats(self) -> Dict:
        """Return logging statistics."""
        ...

def _is_near_known_freq(freq_hz: float, tolerance_hz: float=2000.0) -> bool:
    """Check if frequency is near a known tag frequency."""
    ...
