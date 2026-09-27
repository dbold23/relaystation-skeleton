"""Allowlisted remote diagnostics, for stations with no inbound network path.

Why this exists
---------------
A cellular station has no route in. Not because of NAT: the SIM7028 is driven as
an AT/HTTP appliance over a serial port, so the Pi has NO IP interface for the
modem at all (verified: no ppp0, wwan0 or usb0). SSH, Tailscale, WireGuard and
reverse tunnels all need an interface that does not exist, so none of them can
reach a field station as currently built.

What an operator actually needs from a remote station is almost never a shell.
It is "run this and tell me what happened". The station already polls Central for
commands and already ships log lines back. So a `run_check` command carries the
name of a diagnostic, the station runs it, and the output returns through the
existing log pipeline. One kilobyte per round trip on a transport that already
works, no new networking, and nothing to keep alive or pay for.

Concretely, this answers the questions that were unanswerable during the
2026-07-24 rollout to Elkhorn: what does its journal say, what airtime is it
achieving, did the update really apply. All of that had to be inferred from
Central telemetry and the server's own access log.

One line, not a dump
--------------------
Every check returns a SINGLE compact line. That is a transport decision, not a
style one. Results ride the remote log handler, which is deliberately stingy --
WARNING and above only, 10 lines per 10 second window, identical-message
suppression for an hour, and truncation at 200 characters. Those limits exist
because the uplink is metered and because real warnings must not be crowded out.
A 25-line journal dump loses to the rate limiter (measured: 1 of 6 lines
arrived) and would starve the channel it borrows.

So each check answers a question instead of dumping text. "6.0 loops/s, 77%
airtime" is more useful than fifty lines of journal, and it costs a few dozen
bytes.

Safety
------
* An ALLOWLIST of named checks. Never arbitrary shell, and no arguments are
  interpolated into a command line -- the name selects a fixed argv.
* Every check is bounded: its own timeout, and its output is truncated to a hard
  byte cap, because this returns over a metered NB-IoT link.
* Read-only by construction. Nothing here writes config, touches the SDR, or
  restarts a service; those already have their own commands with their own
  guards.
* Never raises. A diagnostic that crashes the station it is diagnosing is worse
  than no diagnostic.
"""
import logging
import os
import subprocess
MAX_OUTPUT_BYTES = 180
DEFAULT_TIMEOUT = 20.0

def _run(argv, timeout=DEFAULT_TIMEOUT):
    ...

def _journal():
    """The most recent status line plus the most recent warning, as one line.

    A tail of the journal is what you want at a terminal; over a metered uplink
    the useful subset is "is it looping, and what last went wrong".
    """
    ...

def _journal_errors():
    """Count of warnings/errors in the last 2 h plus the newest one."""
    ...

def _airtime():
    """Loops/s from the status line, which is the station's listening duty cycle.

    Airtime is the quantity that decided whether the detector worked at all: a
    stray 0.1 s sleep put it at 53%, which cost roughly every other pulse and
    made the pattern validator reject the rest.
    """
    ...

def _detector_stats():
    ...

def _config():
    """The few config values that matter operationally, secrets omitted."""
    ...

def _disk():
    ...

def _thermal():
    """Temperature and throttling. pi2 last reported 71 C before going dark."""
    ...

def _modem():
    """Registration and signal, read WITHOUT touching the serial port.

    Opening the modem here would fight the comms client for the port lock, and
    a diagnostic must never be able to break the transport carrying its own
    answer. So report what the station has already recorded instead.
    """
    ...

def _uptime():
    ...

def _fingerprint():
    """What the station believes it is running, for comparison with the server."""
    ...

def available():
    ...

def run_check(name):
    """Run one allowlisted check. Returns (ok, text). Never raises."""
    ...
