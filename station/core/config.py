"""
Centralized Configuration Management for RelayStation v2
Handles loading, saving, and runtime state management
"""
import configparser
import logging
import os
import stat
import threading
from datetime import datetime, timedelta
from pathlib import Path

class Config:
    """Centralized configuration with thread-safe access"""
    _instance = None

    def __new__(cls, config_path=None):
        """Singleton pattern - only one config instance"""
        ...

    def __init__(self, config_path=None):
        ...

    def _load_defaults(self):
        """Load default configuration values"""
        ...

    def load(self):
        """Load configuration from file"""
        ...

    def _migrate(self):
        ...

    def save(self):
        """Save current configuration to file, atomically.

        Written to a temp file in the same directory, fsynced, then renamed
        over config.ini, so a power cut mid-save (a field Pi on a battery)
        leaves the old file or the new one, never a truncated one. The old
        open(path, 'w') truncated first; a station that lost power there
        booted with no [Central] api_key and could not reach Central at all.
        The file's mode and owner are kept, and a symlinked config.ini stays a symlink.
        """
        ...

    @property
    def station_id(self):
        ...

    @property
    def location(self):
        ...

    @property
    def frequency(self):
        ...

    @property
    def sample_rate(self):
        ...

    @property
    def gain(self):
        ...

    @gain.setter
    def gain(self, value):
        ...

    @property
    def spectrum_survey_enabled(self):
        """Continuous band-power waterfall for the ML dataset. Default off."""
        ...

    @property
    def capture_review_enabled(self):
        """Save a tiny spectrogram per approved pulse for the /review page
        (human yes/no labeling -> FP-discriminator training data). Hard-capped
        (40/hr, 2000 total, 30 MB) — see core/pulse_capture.py. Default off."""
        ...

    @property
    def candidate_confirm_cellular(self):
        """On a tag lock / unlisted detection, upload a small confirmation
        thumbnail to Central over WiFi *or* NB-IoT (so a cellular-only field
        station's real detections reach the Review gallery — 'confirm it's a
        real tag before driving out to retrieve it'). Default on."""
        ...

    @property
    def candidate_thumb(self):
        """Confirmation-thumbnail size WxH (e.g. '32x20' ~0.9 KB — one NB-IoT
        POST). Full-res capture stays local for training either way."""
        ...

    @property
    def candidate_confirm_max_per_hour(self):
        """Safety cap on confirmation uploads per hour (bounds cellular data /
        modem power if locks flap). Dedup per (freq, reason) applies first."""
        ...

    @property
    def change_threshold(self):
        ...

    @change_threshold.setter
    def change_threshold(self, value):
        ...

    def _mf(self, key, default):
        ...

    def _fold(self, key, default):
        ...

    @property
    def mf_enabled(self):
        ...

    @property
    def mf_track_gate_db(self):
        """Lowered per-pulse gate inside fold-predicted arrival windows.
        0 or negative disables the tracking gate."""
        ...

    @property
    def mf_track_window_ms(self):
        ...

    @property
    def mf_decimate_factor(self):
        ...

    @property
    def mf_pulse_width_ms(self):
        ...

    @property
    def mf_pulse_gate_db(self):
        ...

    @property
    def mf_max_tracked(self):
        ...

    @property
    def mf_stride(self):
        ...

    @property
    def mf_carrier_search_hz(self):
        ...

    @property
    def mf_frame_budget_ms(self):
        ...

    @property
    def fold_enabled(self):
        ...

    @property
    def fold_gate_mode(self):
        """'auto' (self-calibrating from a surrogate null) or 'fixed'."""
        ...

    @property
    def fold_target_fa_per_hour(self):
        ...

    @property
    def fold_sigma_floor(self):
        ...

    @property
    def fold_confirm_votes(self):
        ...

    @property
    def fold_confirm_window(self):
        ...

    @property
    def fold_period_tol_sec(self):
        """Half-width of the period band the acquisition fold searches."""
        ...

    @property
    def fold_null_surrogates(self):
        ...

    @property
    def fold_clip_sigma(self):
        ...

    @property
    def fold_bin_ms(self):
        ...

    @property
    def fold_window_sec(self):
        ...

    @property
    def fold_decision_sec(self):
        ...

    @property
    def fold_async(self):
        ...

    @property
    def fold_confirm_spacing_sec(self):
        ...

    @property
    def mf_impulse_spike_ratio(self):
        ...

    @property
    def fold_period_prior_sec(self):
        ...

    @property
    def fold_period_min_sec(self):
        ...

    @property
    def fold_period_max_sec(self):
        ...

    @property
    def fold_sigma_gate(self):
        ...

    @property
    def fold_min_folds(self):
        ...

    @property
    def fold_min_coverage(self):
        ...

    @property
    def fold_confirm_lock(self):
        ...

    @property
    def pulse_widths_ms_by_freq(self):
        """Per-frequency pulse widths from [TagTemplates] (freq_mhz = width_ms)."""
        ...

    def _pv(self, key, default):
        ...

    @property
    def pattern_min_pulses(self):
        ...

    @property
    def pattern_min_interval(self):
        """Shortest interval counted as a real gap between beacons."""
        ...

    @property
    def pattern_max_interval(self):
        """Longest plausible beacon period at this site.

        Tightening this is the operator's lever against discovery-mode false
        alarms: measured on pi3, phantom tags arrive with 4-10 s intervals at
        +3 to +5 dB, while the tag family beats every 1-2 s. The default stays
        wide (30 s) because a slow tag must not be silently excluded.
        """
        ...

    @property
    def pattern_max_interval_variation(self):
        ...

    @property
    def pattern_reset_timeout(self):
        ...

    @property
    def survey_engine(self):
        ...

    @property
    def survey_pulse_ms(self):
        ...

    @property
    def survey_pfa(self):
        ...

    @property
    def whitelist_tolerance_hz(self):
        ...

    @property
    def power_threshold_db(self):
        ...

    @property
    def use_dual_mode(self):
        ...

    @property
    def multi_tag_enabled(self):
        ...

    @property
    def freq_min(self):
        ...

    @property
    def freq_max(self):
        ...

    @property
    def channel_width(self):
        ...

    @property
    def discovery_policy(self):
        """What a survey-only hit on a NON-whitelisted frequency may do.

        report    - create a tag record, as it always has. THE DEFAULT, because
                    a hunting station (pi2 searching for otter tags at 164 MHz)
                    has no whitelist by design and gating it would silence it.
        flag      - create the tag but mark it unconfirmed.
        candidate - log it and stop. The frequency is still surfaced, but a guess
                    does not enter the tag table as though it were a detection.

        Whitelisted frequencies are unaffected by every setting: pi1 has a
        whitelist and reports zero false alarms on the same code that produced
        22 phantoms of 23 on a station with none.
        """
        ...

    @property
    def known_frequencies(self):
        """Parse known_frequencies from comma-separated MHz values to list of Hz floats.

        Config format: '151.192, 151.223, 151.231'  (MHz values)
        Returns: [151192000.0, 151223000.0, 151231000.0]  (Hz floats)
        Returns empty list if not specified or empty.
        Skips malformed entries with a warning.
        """
        ...

    @property
    def telegram_bot_token(self):
        ...

    @property
    def telegram_chat_id(self):
        ...

    @property
    def telegram_configured(self):
        ...

    @property
    def heartbeat_interval_hours(self):
        ...

    @property
    def alert_on_error(self):
        ...

    @property
    def command_poll_minutes(self):
        ...

    @property
    def auto_optimize_on_boot(self):
        ...

    @property
    def continuous_adaptation(self):
        ...

    @property
    def min_detections_before_adapt(self):
        ...

    @property
    def tag_timeout_hours(self):
        ...

    @property
    def central_enabled(self):
        ...

    @property
    def central_server_url(self):
        ...

    @property
    def nbiot_server_url(self):
        ...

    @property
    def central_api_key(self):
        ...

    @property
    def central_batch_interval(self):
        ...

    @property
    def clock_sync_from_server(self):
        ...

    @property
    def locked_report_interval_seconds(self):
        """Seconds between locked-tag ('k') reports per frequency. Read live by
        the offline queue, so a set_config takes effect without a restart."""
        ...

    @property
    def tag_window_fields(self):
        """Attach the per-tag window summary to 'k' reports. Read live by the
        central client on every locked report."""
        ...

    @property
    def spectrogram_enabled(self):
        ...

    @property
    def spectrogram_freq_min(self):
        ...

    @property
    def spectrogram_freq_max(self):
        ...

    @property
    def spectrogram_center_freq(self):
        ...

    @property
    def spectrogram_fft_size(self):
        ...

    @property
    def spectrogram_time_decimation(self):
        ...

    @property
    def spectrogram_output_dir(self):
        ...

    @property
    def spectrogram_hourly_png(self):
        ...

    @property
    def spectrogram_hourly_hdf5(self):
        ...

    @property
    def spectrogram_max_storage_gb(self):
        ...

    @property
    def spectrogram_retention_days(self):
        ...

    @property
    def connectivity_monitoring_enabled(self):
        ...

    @property
    def connectivity_signal_check_interval(self):
        ...

    @property
    def connectivity_test_transmission_enabled(self):
        ...

    @property
    def connectivity_test_interval(self):
        ...

    @property
    def connectivity_log_csv(self):
        ...

    @property
    def connectivity_csv_retention_days(self):
        ...

    @property
    def connectivity_bandwidth_test_mode(self):
        ...

    @property
    def nbiot_mode(self):
        ...

    @nbiot_mode.setter
    def nbiot_mode(self, value):
        ...

    @property
    def nbiot_reduced_heartbeat_interval(self):
        ...

    @property
    def nbiot_reduced_command_poll_interval(self):
        ...

    @property
    def slowest_heartbeat_seconds(self):
        """The longest gap this station may legitimately go without checking in.

        THE single source of truth for "how quiet is normal here". Three
        separate things have to agree with it or a data-saving station looks
        broken: the watchdog's uplink-freshness window, its last-resort cold
        reboot, and Central's offline threshold. Each used to carry its own
        hardcoded copy, which is fine at 60 s and catastrophic at 12 h - a
        station checking in twice a day would trip a 4 h blackout reboot four
        times a day, forever, and read as failing hardware.

        On WiFi the station always heartbeats every 60 s (it is free), so this
        is the CELLULAR cadence: the reduced interval when the station is in
        reduced mode, 60 s otherwise. It is the worst case, not the current
        one, because a threshold has to hold when the WiFi drops.
        """
        ...

    def get(self, section, key, fallback=None):
        """ConfigParser-style read of a raw setting.

        Config wraps a ConfigParser but exposed no generic reader, so
        `config.get('Monitoring', 'last_resort_reboot', fallback='true')` in
        health/watchdog.py raised AttributeError into a bare except and left
        the last-resort cold reboot permanently enabled - the documented way to
        turn it off did nothing at all. Anything with a dedicated property
        should use the property; this is for settings that do not have one.
        """
        ...

    def get_state(self, key, default=None):
        """Get runtime state value"""
        ...

    def set_state(self, key, value):
        """Set runtime state value"""
        ...

    def record_detection(self, freq_mhz, signal_db=None):
        """Record a tag detection"""
        ...

    def should_alert_tag(self, freq_mhz):
        """Check if we should send alert for this tag (de-duplication)"""
        ...

    def record_alert(self, freq_mhz):
        """Record that we sent an alert for this tag"""
        ...

    def get_uptime_hours(self):
        """Get station uptime in hours"""
        ...

    def get_status_summary(self):
        """Get status summary for reporting"""
        ...
_config = None

def get_config(config_path=None):
    """Get the global config instance"""
    ...
