"""
NB-IoT HTTP Client for SIM7028 HAT
Provides HTTP POST via AT commands when WiFi is unavailable.
"""
import serial
import time
import json
import re
import logging
import threading
from typing import Dict, Optional
SERIAL_BAUD = 115200
DEFAULT_TIMEOUT = 30
MAX_HTTPDATA_BYTES = 10000
WAKE_RESET_GPIO = 6
WAKE_PULSE_S = 0.01
RESET_PULSE_S = 0.5
RECOVERY_FAIL_THRESHOLD = 3
RECOVERY_MIN_INTERVAL_S = 900
_GPIO_DEVICE = None

def _get_gpio():
    """Return the shared WAKE/RST GPIO device, or None off-Pi (fail-soft)."""
    ...
MODEM_CLOCK_MIN_YEAR = 2024
MODEM_CLOCK_MAX_YEAR = 2060

def parse_cclk(response: str):
    """Parse an AT+CCLK? reply -> timezone-aware UTC datetime, or None.
    Format: +CCLK: "yy/MM/dd,hh:mm:ss+zz" where zz is the TZ offset in
    QUARTER-hours (SIMCom). The SIM7028 R2110 answers with a FOUR-digit year
    ("2000/01/01,02:42:32+08" on pi3, 2026-09-10); the two-digit pattern
    never matched it, so no station ever took modem time and pi1 logged
    "no modem network time available yet" for a week while 7.2 h off.
    Tolerates a missing/anomalous TZ (assumes UTC). Returns None for an unset
    modem clock (year before MODEM_CLOCK_MIN_YEAR)."""
    ...

class NBIoTResponse:
    """Mock response object compatible with requests.Response"""

    def __init__(self, status_code: int, text: str=''):
        ...

    def json(self) -> Dict:
        ...

class NBIoTHTTPClient:
    """HTTP client using AT commands for SIM7028 NB-IoT HAT."""

    def __init__(self, serial_port: str=SERIAL_PORT, baud: int=SERIAL_BAUD):
        ...

    @contextmanager
    def _lock_port(self):
        """Serialize modem access across THREADS (self._lock) and PROCESSES
        (flock). The station daemon and scripts/safe_update.py are separate
        processes sharing /dev/ttyAMA0 — without the file lock an OTA manifest
        download races the station's heartbeat batch and both lose (proven in
        the field 2026-07-16: 'Could not fetch manifest'). Blocks up to 90s
        for the other process to finish, then proceeds rather than deadlock."""
        ...

    def _send_at(self, ser, command: str, wait: float=1.0, hard_timeout: float=10.0, expect: str=None) -> str:
        """Send AT command and return response.

        Args:
            ser: Serial port
            command: AT command string
            wait: Initial wait time before reading
            hard_timeout: Absolute maximum wait to prevent hangs
        """
        ...

    def _read_http_body(self, ser, content_length: int, timeout_s: float=120.0) -> str:
        """Read a response body via AT+HTTPREAD offset requests.

        The SIM7028 streams each request's data as repeated
        '+HTTPREAD: <n>\r
<n raw bytes>' frames (512B chunks) ending with
        '+HTTPREAD: 0' — and hands over at most ~7.5KB per request no matter
        how much is asked for (proven on the bench 2026-07-16: 7680/50050).
        So the body is walked with AT+HTTPREAD=<offset>,<len> requests until
        content_length is reached. Binary-safe: trusts frame lengths only —
        never scans payload for OK/ERROR, which base64 bodies can contain."""
        ...

    def _config_keep_awake(self, ser):
        """Stop the modem from ever sleeping its UART off.

        Proven wedge on pi1 2026-07-14: factory defaults are PSM enabled
        (T3324~5min/T3412~20h) + PMU depth Hibernate (QCPMUCFG=1,4), where the
        UART block is POWERED OFF — the modem goes deaf to AT until a wake pin
        or power cycle. On a solar/mains station the ~5mA idle cost of staying
        awake is noise next to the Pi 5 + SDR, so:
          CPSMS=0    — disable PSM (persists in NVM)
          CEDRXS=0   — disable eDRX (network had granted it)
          QCPMUCFG=1,1 — cap sleep at Idle, UART always wakeable.
                       NO_SAVE: must be re-sent after every modem boot/reset,
                       which is why this runs per-boot, not once-ever.
        """
        ...

    def _ensure_network(self, ser) -> bool:
        """Ensure network is open."""
        ...

    def post(self, url: str, json_data: Dict=None, headers: Dict=None, timeout: int=DEFAULT_TIMEOUT) -> NBIoTResponse:
        """Send HTTP POST using AT commands (with transport-failure watchdog)."""
        ...

    def _post_impl(self, url: str, json_data: Dict=None, headers: Dict=None, timeout: int=DEFAULT_TIMEOUT) -> NBIoTResponse:
        ...

    def get(self, url: str, headers: Dict=None, timeout: int=DEFAULT_TIMEOUT) -> NBIoTResponse:
        """Send HTTP GET using AT commands (with transport-failure watchdog)."""
        ...

    def _get_impl(self, url: str, headers: Dict=None, timeout: int=DEFAULT_TIMEOUT) -> NBIoTResponse:
        ...

    def get_signal_strength(self) -> Dict:
        """
        Query signal strength via AT+CSQ

        Returns:
            {
                'rssi': int (0-31, 99=no signal) or None if it could not be read,
                'ber': int (bit error rate, 0-7, 99=not detectable) or None,
                'rssi_dbm': Optional[int] (approximate dBm: -113 + rssi*2),
                'error': str, only when the read failed
            }

        A read that FAILS (port busy, timeout, garbage) returns None, never 99.
        It used to return 99, which is the modem's own word for "no measurable
        signal", so a station whose serial port was merely busy logged "NO
        SIGNAL - check antenna/coax" and the dashboard told a field trip to
        look at the coax. Two stations spent six weeks dark under that
        message; nobody can say today how much of it was real.
        """
        ...

    def get_network_time(self):
        """Query the modem's network-set real-time clock (AT+CCLK). After
        registration the carrier sets modem time (CTZU); this is the field
        time source when there is no NTP (cellular-only site). Returns a
        timezone-aware UTC datetime, or None."""
        ...

    def get_network_info(self) -> Dict:
        """
        Get network registration and operator information

        Returns:
            {
                'registered': bool,
                'registration_status': int (0=not, 1=home, 2=searching,
                                            3=denied, 5=roaming) or None if
                                            it could not be read,
                'operator': str,
                'network_type': str,
                'error': str, only when the read failed
            }

        CEREG stat 0 is a real answer ("not registered, not searching"). A
        read that fails must not be reported as that answer: it used to be,
        and a busy port then looked exactly like a modem that had given up.
        """
        ...

    def _probe(self, window_s: float=3.0) -> bool:
        """True if the modem answers AT at the working baud within window_s."""
        ...

    def _pulse_gpio(self, seconds: float) -> bool:
        """Drive the WAKE/RST line high for `seconds`, then low.

        Uses the process-wide singleton from _get_gpio() so every client
        instance in this process shares one device (a second instance can
        never lose the pin to GPIOPinInUse). Fail-soft off-Pi.
        """
        ...

    def _reg_status_unlocked(self) -> Optional[int]:
        """CEREG <stat>, for callers that ALREADY hold the port lock.

        get_network_info() takes _lock_port() itself, so recover_modem() cannot
        use it — the lock is not reentrant and it would deadlock until the 90s
        bounded wait expired.

        Returns the raw CEREG stat, or None if it could not be read:
            0 = not registered, not searching   2 = SEARCHING
            1 = registered (home)               3 = registration DENIED
            5 = registered (roaming)            4 = unknown
        """
        ...

    def _csq_unlocked(self) -> int:
        """AT+CSQ <rssi>, for callers that ALREADY hold the port lock.

        get_signal_strength() takes _lock_port() itself, so recover_modem()
        cannot use it (the lock is not reentrant -> deadlock). Returns the raw
        RSSI (0-31), or 99 = no signal / could not read.
        """
        ...

    def recover_modem(self) -> Dict:
        """Escalating modem recovery ladder (field-safe, rate-capped by caller).

        Rungs, cheapest first — each verified against the SIM7028/QCX212 docs:
          0. alive but SEARCHING -> do nothing (see below)
          1. alive + registered -> AT+QCRST software reboot (CFUN=1,1's reset
                                 flag is documented as IGNORED on this chip)
          2. 9600 LPUART wake -> RX at 9600 baud wakes the core when 115200
                                 traffic can't (sleeping UART block)
          3. WAKE pin edge    -> GPIO6 falling edge, AT must follow within
                                 ~10ms (burst + retries; edge, not level)
          4. hard reset       -> GPIO6 high 500ms through the WAKE->RST field
                                 jumper (H2 header); without the jumper this
                                 is just a long wake pulse and rung fails soft
        On success the keep-awake config is re-armed (QCPMUCFG is NO_SAVE).

        Rung 0 is why this ladder is not simply "transport broke -> reboot": a
        modem that answers AT but has not registered yet is not wedged, it is
        WORKING — searching. AT+QCRST throws that progress away and restarts the
        band scan from zero, and a multi-band NB-IoT scan takes longer than
        RECOVERY_MIN_INTERVAL_S. A station in marginal coverage would therefore
        reset-storm its own modem and never attach (observed on pi2 2026-07-16:
        HTTP 714 "no network" -> 3 failures -> QCRST, every 15 min, forever).
        Only a modem that is registered and STILL failing transport is stuck.
        """
        ...

    def _track_transport(self, status_code: int):
        """Count consecutive transport failures; trigger the recovery ladder.

        >=500 means we never reached the server (local 500/503 or gateway
        errors); any <500 proves the radio path works and resets the count.
        Recovery is rate-capped so a dead site can't reset-storm the modem.
        """
        ...

    def check_and_recover(self) -> Dict:
        """
        Check modem health and attempt recovery if needed.

        Returns:
            {
                'healthy': bool,
                'registered': bool,
                'signal': dict,
                'recovered': bool,
                'action_taken': str
            }
        """
        ...

    def measure_bandwidth(self, payload_size: int=1024, timeout: int=60) -> Dict:
        """
        Measure bandwidth with test payload (DIAGNOSTIC MODE ONLY)

        WARNING: Uses cellular data - only use for testing/diagnostics

        Args:
            payload_size: Size of test payload in bytes (default: 1KB)
            timeout: Maximum time for transmission in seconds

        Returns:
            {
                'bytes_sent': int,
                'duration_seconds': float,
                'throughput_bps': float,
                'success': bool,
                'latency_ms': float,
                'signal_before': Dict,
                'signal_after': Dict
            }
        """
        ...

def local_link_kind() -> Optional[str]:
    """The kind of local IP link that is up with a routable address.

    Returns 'eth' for wired, 'wifi' for wireless, or None when neither is
    usable. Wired wins when both are up, because that is the path the station
    will actually take.

    Read from `ip -o -4 addr show up scope global`, one call. 'scope global'
    is what excludes a 169.254 self-assigned address, which is an interface
    with no DHCP lease, not a network.
    """
    ...

def is_wifi_available() -> bool:
    """True when a local IP path is up: WIRED OR WIRELESS, i.e. not cellular.

    The name is kept because every caller uses it and it reads as the question
    being asked ("can I use the ordinary network instead of the modem?"), but
    the meaning is "not cellular", not "wlan0".

    Incident 2026-09-10: this checked `wlan0` and only `wlan0`. Every caller
    treats False as "the modem is the only way out", so a station on Ethernet
    with no wireless interface sent every batch and every command poll to a
    SIM7028 that was not there. It would detect tags perfectly and never
    appear on the dashboard. Found while preparing a wired station; see
    tests/test_ethernet_station.py.
    """
    ...
