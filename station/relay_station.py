"""
RelayStation v2 - Main Entry Point
Consolidated radio tag detection and monitoring system

Usage:
    python3 relay_station.py [--config CONFIG_FILE]

This is the single entry point that:
- Auto-calibrates SDR gain on startup
- Runs multi-channel tag detection
- Reports to central server and web dashboard
- Polls for remote commands
- Monitors system health
"""
import os
import sys
import time
import signal
import logging
import argparse
from pathlib import Path

def main():
    """Main entry point"""
    ...
import re as _re

def _lora_pin(v):
    """set_config caster for a LoRa mode pin: a BCM number, or 'none' for a
    HAT whose mode is fixed by jumper caps (USB-attached gateway HAT)."""
    ...

def _lora_map_ok(v) -> bool:
    ...

class RelayStation:
    """Main orchestrator for the relay station"""

    def __init__(self, config, skip_calibration=False):
        """
        Initialize relay station

        Args:
            config: Config instance
            skip_calibration: Skip auto-calibration on startup
        """
        ...

    def run(self):
        """Run the relay station"""
        ...

    def stop(self):
        """Stop all components"""
        ...

    def _init_sdr(self) -> bool:
        """Initialize RTL-SDR"""
        ...

    def _run_calibration(self):
        """Run auto-calibration"""
        ...

    def _init_detector(self):
        """Initialize multi-channel detector"""
        ...

    def _init_central_client(self):
        """Initialize central server client for multi-station setup"""
        ...

    def _lora_role(self) -> str:
        ...

    def _lora_config(self):
        """[LoRa] as the running Config holds it (so a set_config that was
        saved before this restart is what the radio is opened with), over
        comms.lora_radio.DEFAULTS."""
        ...

    def _init_lora_client(self):
        ...

    def _init_lora_gateway(self):
        """Start the LoRa receiver next to the normal Central client. A
        failure here is logged and leaves the station's own reporting alone:
        a gateway that cannot open its HAT is still a working station."""
        ...
    STAGE_REPORT_EVERY = 10

    def _mf_heartbeat_block(self, stats):
        """The 'mf' sub-dict of the heartbeat's 'st' block, or None.

        Sent whenever the matched filter is CONFIGURED, i.e. the detector's
        stats carry any mf_ key (get_stats merges MFFrontEnd.stats() only
        when the front end was built). It used to be gated on mf_tracked
        being non-zero, and the governor's shed path clears the tracked set
        (MFFrontEnd._note_frame: tags.clear()), so a station whose MF had
        been shed for CPU sent no block at all and looked identical on
        Central to a station with no whitelist. That is the silent-failure
        shape this system keeps producing: the one moment the block matters
        most was the one moment it went missing. Now 'on' says so instead.

        Every stat is read with a default so a front end that does not emit a
        key yet (or ever) can never raise on the detection thread.
        """
        ...

    def _config_fingerprint(self) -> str:
        """md5 over the settings that decide WHAT this station listens to.

        Deliberately not the whole file: mutable runtime noise (last gain,
        cached state) would make it churn and cry wolf. Just the fields an
        operator pushes and expects to take effect, so a mismatch against what
        Central last sent means the push genuinely did not land.
        """
        ...

    def _content_fingerprint(self) -> str:
        """md5 over sorted 'path:filehash' of the SAME allowlisted set the
        server's update manifest covers. Matching the server's value means
        'running exactly what the server would deploy' — git HEAD can't say
        that, because safe_update applies files without moving it. Rides in
        heartbeats as 'fw' for the dashboard's version badge."""
        ...
    MODEM_BOOTSTRAP_MIN_YEAR = 2024

    def _sync_clock_from_modem(self):
        """Bootstrap an implausible system clock from the modem's network time.

        This is a LAST resort, not the station's clock source. Central stamps
        `server_time` on every reply and comms/clock_sync.py disciplines the
        clock from it with the round trip as an error bar. AT+CCLK has no
        error bar and its timezone semantics vary by modem and network: on
        elkhorn-radio-shack-2 (SIM7028 R2110) it put the clock 7 h FORWARD of
        a clock Central had just corrected, and health.watchdog cold-rebooted
        the Pi four seconds later (2026-09-11). So:

        * if NTP holds the clock, do nothing (the bench);
        * if Central has ever answered, do nothing — server_time wins;
        * otherwise step only a clock that is implausible on its face, and
          re-anchor the on-disk age files with it.

        Never raises: boot must not hang on this.
        """
        ...

    def _init_watchdog(self):
        """Initialize health watchdog"""
        ...

    def _init_dashboard(self):
        """Initialize web dashboard"""
        ...

    def _run_detection_loop(self):
        """Main detection loop"""
        ...

    def _handle_calibrate_command(self):
        """Handle remote calibrate command"""
        ...

    def _handle_set_config_command(self, payload):
        """Remote config change: {'key': <allowlisted name>, 'value': ...}.

        Writes and saves the value, then returns the ack payload::

            {'key': name, 'applied': bool, 'needs_restart': [name] or []}

        `needs_restart` lists the applied keys that are only read at
        construction (see the comment on REMOTE_CONFIG_KEYS), so the operator
        knows to follow with a 'restart' command instead of waiting for a
        change that will never arrive. The same fact is logged at WARNING,
        which is the level the remote log handler forwards to Central, so it
        is visible there even though the queued 'a' event carries only the
        command id. A rejected key or value is logged and reported as
        applied=False, never raised: the command thread must keep running.
        """
        ...
    SDR_TUNE_MIN_HZ = 24000000.0
    SDR_TUNE_MAX_HZ = 1766000000.0
    SDR_RATE_MIN_HZ = 225000.0
    SDR_RATE_MAX_HZ = 2560000.0

    def _handle_set_frequencies_command(self, payload):
        """Apply a server-pushed tag list and/or band plan, then restart so the
        detector re-centers.

        Two independent things can arrive, and EITHER ALONE is a valid push:

        * ``known_frequencies_mhz`` — the tag whitelist. An explicitly empty
          list clears it, putting the station into hunting mode (uniform comb).
        * a band plan (``frequency`` / ``sample_rate`` / ``freq_min`` /
          ``freq_max``, in Hz) — moves the SDR passband.

        A hunting station has no tag list, so a band-plan-only push must be
        accepted: that is what lets an operator step the ~2 MHz passband across
        a wide search band from the dashboard instead of driving to the site.
        Absent key = leave that setting alone; present key = change it.

        Managed from the dashboard (set_frequencies / set_tag_config). The
        controlled restart (the same proven path OTA uses) is deliberate: the
        offline queue preserves data and startup rebuilds channels cleanly,
        avoiding live in-loop channel surgery on the field station.
        """
        ...

    def _restart_after_ack(self, delay_sec=3):
        """Restart the service AFTER the current command handler returns.

        A synchronous restart inside the handler killed the process before
        the command was recorded and acked; Central redelivered it, and the
        redelivery was acked only because the config already matched: one
        extra restart per frequency push. Same shape as the OTA handler.
        """
        ...

    def _handle_run_check_command(self, payload):
        """Run an allowlisted diagnostic and return the output through the logs.

        There is no inbound network path to a cellular station, so this is how a
        remote operator (or an agent) sees inside one. The result rides the log
        pipeline that already carries detector lines to Central, which means no
        new endpoint, no new transport, and nothing to keep alive.

        Read-only and allowlisted by name: see core/remote_checks.py. Failures
        are reported, never raised -- a diagnostic must not be able to break the
        station it is inspecting.
        """
        ...

    def _handle_restart_command(self):
        """Handle remote restart command"""
        ...

    def _handle_update_command(self):
        """Handle remote update command — safe OTA update from central server."""
        ...

def run_tests(config) -> int:
    """
    Run configuration tests

    Returns:
        Exit code (0 for success)
    """
    ...
