"""Set the station clock from Central when nothing else will.

A field station has no NTP: the site has no WiFi, the modem's network time
was never parseable (a four-digit year, comms.nbiot_http.parse_cclk), the Pi 5
RTC has no battery on the fleet's boards, and hwclock was not installed. pi1
(elkhorn-radio-shack) ran 25,944 s (7.2 h) behind server time for the whole
week of the 2026-07-26 range walk, every page stayed green, and the walk was
empty because detections are matched to GPS fixes within 20 s of station
time.

Central stamps `server_time` (epoch seconds) on every reply a station gets,
over WiFi, Ethernet and NB-IoT alike. This module takes that stamp, estimates
the skew against the local clock, and steps the system clock when NTP is not
synchronised and the skew is larger than the measurement can be wrong by
(the round trip). On the bench, where NTP holds the clock, it never runs a
command. A step is logged at WARNING so it reaches Central's logs.
"""
import logging
import os
import subprocess
import time
from typing import Callable, Iterable, Optional, Sequence
MIN_STEP_S = 5.0
NTP_CHECK_INTERVAL_S = 300.0
MIN_STEP_SPACING_S = 60.0
EPOCH_MIN = 1700000000.0
EPOCH_MAX = 4000000000.0

class ClockSync:
    """Step the system clock from Central's `server_time` replies."""

    def __init__(self, enabled: bool=True, run: Callable=subprocess.run, now: Callable[[], float]=time.time, monotonic: Callable[[], float]=time.monotonic, anchor_paths: Optional[Sequence[str]]=None):
        ...

    def ntp_synchronized(self) -> Optional[bool]:
        """True/False from timedatectl, None when it cannot be asked. Cached."""
        ...

    def observe(self, body, rtt_s: float) -> str:
        """Feed one reply from Central. Returns what was done, for the tests
        and the log: 'ignored', 'within', 'ntp', 'unknown', 'spaced', 'stepped'
        or 'failed'."""
        ...

    def _step(self, skew: float, rtt_s: float) -> str:
        ...

def reanchor(paths: Iterable[str], delta_s: float) -> int:
    """Shift every epoch value in `paths` by `delta_s`, the amount the system
    clock just moved.

    These files record "when did X last happen" in wall-clock seconds and are
    read back as an age. A clock step changes the frame they were written in,
    so without this the age jumps by the step. That is what cold-rebooted
    elkhorn-radio-shack-2 four seconds after its clock moved 7 h forward
    (2026-09-11): health.watchdog read a 10.6 h blackout off a 4-second-old
    stamp. Never raises: a station must not fail to set its clock because a
    bookkeeping file is unwritable.

    Returns the number of files rewritten.
    """
    ...
