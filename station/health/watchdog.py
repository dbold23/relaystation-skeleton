"""
Health Watchdog for RelayStation v2
Monitors system health, SDR status, and manages auto-recovery
"""
import os
import time
import psutil
import threading
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable

class HealthWatchdog:
    """
    System health monitor with auto-recovery capabilities.

    Monitors:
    - Detector process running
    - SDR connected and responding
    - Memory/CPU usage
    - Disk space
    - Network connectivity
    - Last successful detection time
    """

    def __init__(self, config):
        """
        Initialize watchdog

        Args:
            config: Config instance
        """
        ...

    def start(self):
        """Start the watchdog in a background thread"""
        ...

    def stop(self):
        """Stop the watchdog"""
        ...

    def _check_loop(self):
        """Background health check loop"""
        ...

    def check_health(self) -> Dict:
        """
        Perform comprehensive health check

        Returns:
            Dictionary with health status and details
        """
        ...

    def _check_network(self, timeout: float=5.0) -> bool:
        """
        Check network connectivity

        Args:
            timeout: Request timeout in seconds

        Returns:
            True if network is available
        """
        ...
    modem_present = True

    def _check_nbiot_health(self) -> Optional[Dict]:
        """Check NB-IoT modem health and attempt recovery if needed."""
        ...
    CLOCK_STEP_TOLERANCE_S = 120.0
    REBOOT_MIN_INTERVAL_S = 3600
    REBOOT_BACKOFF_MAX_S = 86400
    max_reboots_per_day = 4

    def _raw_blackout_seconds(self) -> float:
        """Seconds since the last successful uplink on ANY transport, read from
        an ON-DISK timestamp so it survives process restarts. Process-memory
        uplink time (uplink_status) resets on every systemd/OTA restart, so a
        naive check would never fire during a real multi-day blackout. Falls
        back to system boot time (/proc/uptime) when no uplink was ever recorded,
        so a fresh station is not rebooted before it has had a chance to attach."""
        ...

    def _blackout_seconds(self) -> float:
        """The blackout clock, with wall-clock STEPS discounted.

        A field station has no NTP and is disciplined by Central's server_time
        (comms/clock_sync.py) or, on a clock that is implausible on its face,
        by the modem. Each of those moves the wall clock, and this number is
        wall-clock arithmetic: without this, a 7 h correction reads as a 7 h
        blackout and triggers the cold reboot tier on a station whose uplink
        is seconds old. That is exactly what happened to elkhorn-radio-shack-2
        on 2026-09-11. The monotonic clock cannot be stepped, so any growth
        beyond the monotonic elapsed time is a step, not silence."""
        ...

    def _reboot_cap(self):
        """Cold reboots allowed per rolling 24 h. Config-backed and bounded.

        The floor of 1 keeps the last-resort tier alive at all (0 would be a
        silent way to disable it, and there is already an explicit
        last_resort_reboot flag for that). The ceiling of 24 is one an hour,
        which reboot_min_interval_s enforces anyway.
        """
        ...

    def _maybe_last_resort_reboot(self):
        """Cold-reboot the Pi as the final recovery tier when no uplink has
        landed on any transport for a long time — a soft-stuck USB/serial/modem/
        band-scan state a modem-level QCRST cannot clear. Threshold is set well
        above a full multi-band NB-IoT scan so a legitimately-searching modem is
        never rebooted; the on-disk rate cap survives the reboot so it can't
        boot-loop."""
        ...

    def check_sdr_connected(self) -> bool:
        """
        Check if RTL-SDR is connected

        Returns:
            True if SDR is detected
        """
        ...

    def get_system_info(self) -> Dict:
        """
        Get detailed system information

        Returns:
            Dictionary with system details
        """
        ...

    def restart_detector(self, delay_sec: float=0) -> bool:
        """
        Attempt to restart the detector service.

        `delay_sec` > 0 schedules the restart in a detached shell and returns
        at once, so the caller's command can be recorded and acked before
        the process dies (a synchronous restart inside a command handler
        killed the process first and Central redelivered the command).

        Returns:
            True if restart was successful (or scheduled)
        """
        ...
