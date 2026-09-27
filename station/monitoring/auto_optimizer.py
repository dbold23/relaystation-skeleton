"""
Auto-Optimizer for Spectrogram Logger
Automatically finds optimal SDR settings for tag detection

Features:
- Gain sweep (find best gain for SNR without saturation)
- FFT size optimization (balance time vs frequency resolution)
- Noise floor characterization
- Interference detection
"""
import logging
import time
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class OptimizationResult:
    """Results from optimization sweep"""
    optimal_gain: float
    optimal_fft_size: int
    noise_floor_db: float
    dynamic_range_db: float
    interference_detected: bool
    interference_frequencies: List[float]
    snr_db: float
    recommendations: List[str]

class SpectrogramOptimizer:
    """Optimize spectrogram settings for tag detection"""

    def __init__(self, sdr, config):
        """
        Initialize optimizer

        Args:
            sdr: RTL-SDR instance
            config: Config instance
        """
        ...

    def run_full_optimization(self, duration_per_test: int=10) -> OptimizationResult:
        """
        Run complete optimization suite

        Args:
            duration_per_test: Seconds per test setting

        Returns:
            OptimizationResult with optimal settings
        """
        ...

    def sweep_gain(self, duration: int=10) -> Dict:
        """
        Sweep through gain settings to find optimal

        Tests gains from 15 to 45 dB in 5 dB steps
        Measures noise floor, dynamic range, and saturation

        Args:
            duration: Test duration in seconds per gain

        Returns:
            Dict with optimal gain and metrics
        """
        ...

    def test_fft_sizes(self, gain: float, duration: int=10) -> Dict:
        """
        Test different FFT sizes for optimal resolution

        Args:
            gain: Gain to use for testing
            duration: Test duration per FFT size

        Returns:
            Dict with optimal FFT size and metrics
        """
        ...

    def detect_interference(self, gain: float, threshold_db: float=10) -> Dict:
        """
        Scan for interference sources (constant carriers)

        Args:
            gain: Gain to use
            threshold_db: Power threshold above noise floor

        Returns:
            Dict with interference info
        """
        ...

    def _generate_recommendations(self, gain_results: Dict, fft_results: Dict, interference: Dict) -> List[str]:
        """Generate optimization recommendations"""
        ...

    def _print_results(self, result: OptimizationResult):
        """Print optimization summary"""
        ...
