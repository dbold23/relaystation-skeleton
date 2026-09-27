"""
Central Server Client for RelayStation
Reports detections, heartbeats, and logs to a central server.
Designed for NB-IoT with offline queue and batching.

Includes:
- Batch-level exponential backoff (backs off across batches, not just retries)
- Connection state awareness (skips sends when offline)
- Separate log queue to prevent feedback loops
"""
import hashlib
import json
import logging
import os
import re
import threading
import time
import requests
from typing import Dict, Optional, List, Callable
from datetime import datetime
from .offline_queue import OfflineQueue, EVENT_DETECTION, EVENT_HEARTBEAT, EVENT_LOG, DEFAULT_LOCKED_REPORT_INTERVAL_SEC
from .nbiot_http import NBIoTHTTPClient, is_wifi_available, local_link_kind
from .clock_sync import ClockSync
from .tag_window import TagWindows
MAX_RETRIES = 3
INITIAL_BACKOFF = 2
MAX_BACKOFF = 60

def _fingerprint(key: str) -> str:
    """First 8 hex of sha256(key), Relay-Central's key_fingerprint(): enough
    to match a log line to Central's key-status, useless to an attacker."""
    ...

def _is_auth_failure(result) -> bool:
    ...

def _api_json(response):
    """Parsed JSON body if this is a real reply from Central, else None.

    A captive portal (and some transparent proxies) answer HTTP 200 with an
    HTML login page, so a 200 status code is NOT proof we reached the server —
    only a body that parses as JSON is. Returning None here is what lets the
    caller fall back to NB-IoT: without it, the station marks a phantom uplink
    on the portal's 200, then json() throws on the HTML and the whole request is
    retried on the same dead WiFi, so both telemetry and command-polling go dark
    while the watchdog still thinks the link is fresh (the exact go-dark-but-
    green failure a captive guest network like moss-guest would cause).
    """
    ...
BATCH_BACKOFF_FACTOR = 2
BATCH_BACKOFF_MAX = 900
BATCH_MAX_EVENTS = 50
CELL_BATCH_BYTES = 9400
WIFI_BATCH_BYTES = 120000
WIFI_BATCH_EVENTS = 300
CATCHUP_MIN_QUEUE = 100
CATCHUP_MAX_BATCHES = 40
CATCHUP_CELL_BYTES = 200000
CATCHUP_WIFI_BYTES = 5000000

class ConnectionStateTracker:
    """Tracks whether any network path to the server is available."""

    def __init__(self):
        ...

    @property
    def is_online(self) -> bool:
        ...

    @property
    def connection_type(self) -> str:
        ...

    def mark_success(self, conn_type: str):
        """Called after a successful send."""
        ...

    def should_probe(self) -> bool:
        """Whether enough time has passed to re-check connectivity."""
        ...

    def probe(self) -> str:
        """Actually check connectivity. Returns 'wifi', 'nbiot', or 'offline'."""
        ...

class CentralClient:
    """
    Client for reporting to central RelayStation server.

    Features:
    - Batched sends (configurable interval)
    - Offline queue for connectivity gaps
    - Exponential backoff on failures (per-request AND per-batch)
    - NB-IoT optimized (small payloads)
    - Automatic failover from WiFi to NB-IoT cellular
    - Connection state awareness (skips sends when offline)
    """

    def __init__(self, config):
        """
        Initialize central client.

        Args:
            config: Config instance with [Central] section
        """
        ...

    def start(self):
        """Start background sender thread."""
        ...

    def stop(self):
        """Stop background sender thread."""
        ...

    def _get_batch_backoff(self) -> float:
        """Calculate wait time based on consecutive failures."""
        ...

    def _sender_loop(self):
        """Background thread that sends batched events."""
        ...

    def _send_wake(self) -> int:
        """One wake of the sender: a batch, then keep going while there is
        a real backlog and the link is healthy (see CATCHUP_*). Returns the
        number of batches sent."""
        ...

    def _send_batch(self) -> int:
        """Send a batch of events to the server (serialized, see _send_lock).
        Returns the payload bytes confirmed sent, 0 if nothing was."""
        ...

    def _send_batch_locked(self) -> int:
        ...

    def _note_server_time(self, body, t0):
        """Hand a successful Central reply to the clock sync with the round
        trip it took (comms.clock_sync). Never raises into the sender."""
        ...

    def _mark_uplink(self):
        ...

    def _modem(self) -> NBIoTHTTPClient:
        """The one NBIoTHTTPClient this process talks to the modem through.
        Created on first use under a lock: the sender thread, a gateway's
        post thread and a confirmation upload can all arrive here together,
        and two instances would each claim the serial port and GPIO."""
        ...

    def post_as(self, station_id: str, api_key: str, endpoint: str, data: Dict, timeout: int=30) -> bool:
        """POST on behalf of ANOTHER station, over this station's transports.

        A LoRa gateway forwards a node's events to Central as the node: same
        WiFi/NB-IoT failover, retries and captive-portal checks as our own
        traffic, but the node's X-Station-ID and API key, so Central files
        the events under the node and the gateway's key never has to be
        trusted for two stations. True only for a real success reply.
        """
        ...

    def seconds_since_uplink(self) -> float:
        """Seconds since the server last confirmed a request from us on ANY
        transport (WiFi or NB-IoT). The health watchdog uses this as data-plane
        truth instead of probing google over a WiFi path that legitimately
        doesn't exist in the field."""
        ...

    def _post(self, endpoint: str, data: Dict, timeout: int=30, headers: Optional[Dict]=None) -> Optional[Dict]:
        """POST with our own key, falling back to the previous key once if
        Central rejects a key it rotated to (see _apply_new_api_key).
        `headers` (post_as) bypasses the key logic entirely."""
        ...

    def _post_raw(self, endpoint: str, data: Dict, timeout: int=30, headers: Optional[Dict]=None) -> Optional[Dict]:
        """
        POST to central server with retries and automatic WiFi/NB-IoT failover.

        Args:
            endpoint: API endpoint (e.g., '/api/v1/events')
            data: Payload dict
            timeout: Request timeout in seconds
            headers: override the auth headers (post_as: a LoRa node's
                     identity riding the gateway's link); default is ours

        Returns:
            Response dict or None on failure
        """
        ...

    def _get(self, endpoint: str, timeout: int=30) -> Optional[Dict]:
        """GET from central server with WiFi/NB-IoT failover."""
        ...

    def report_detection(self, frequency_mhz: float, signal_db: float, confidence: float, is_locked: bool=False, is_unlisted: bool=False, period_sec: Optional[float]=None, source: Optional[str]=None):
        """
        Report a tag detection.

        Args:
            frequency_mhz: Frequency in MHz (e.g., 151.200)
            signal_db: Signal strength in dB above noise
            confidence: Confidence score (0.0 - 1.0)
            is_locked: Whether tag has been locked
            is_unlisted: Whether this is an unknown (non-whitelisted) frequency
            period_sec: the detector's fitted beacon period, if any; sets how
                many pulses a locked report's window expected
            source: evidence source ('survey', 'mf', 'fold'). A fold decision
                is a statement about many pulses, not a pulse, so it is not
                counted as an arrival.
        """
        ...

    def report_candidate_confirm(self, frequency_mhz: float, reason: str, extra_meta: Optional[Dict]=None):
        """Send a small confirmation thumbnail for a retrieval-worthy detection
        (lock / unlisted) over WiFi *or* NB-IoT, so it reaches the Review
        gallery from a cellular-only field station. Deduped per (freq, reason),
        rate-capped, and inert when disabled or no recent capture exists."""
        ...

    def _latest_thumb(self, frequency_mhz: float, tol_khz: float=3.0):
        """Freshest local capture near `frequency_mhz`, downsampled to the
        configured confirm size (max-pool preserves the pulse). None if absent."""
        ...

    def report_heartbeat(self, cpu_percent: float, memory_percent: float, temperature_c: Optional[float], active_tags: int, uptime_seconds: int, extras: Optional[Dict]=None):
        """
        Report station heartbeat.
        """
        ...

    def report_log(self, level: str, message: str):
        """
        Report a log message (WARNING and above).

        Args:
            level: Log level (WARNING, ERROR, CRITICAL)
            message: Log message
        """
        ...

    def report_tag_locked(self, frequency_mhz: float, pulse_count: int, confidence: float):
        """Report that a tag has been locked."""
        ...

    def report_tag_retrieved(self, frequency_mhz: float):
        """Report that a tag has been retrieved (removed from tracking)."""
        ...

    def fetch_commands(self) -> List[Dict]:
        """
        Fetch pending commands from server.

        Returns:
            List of command dicts
        """
        ...

    def send_now(self):
        """Force immediate send of queued events."""
        ...

    def get_stats(self) -> Dict:
        """Get client statistics."""
        ...

    def start_command_polling(self, interval_seconds: int=60):
        """
        Start background command polling thread.

        Args:
            interval_seconds: How often to poll for commands (default 60s)
        """
        ...

    def stop_command_polling(self):
        """Stop command polling thread."""
        ...

    def _command_poll_loop(self):
        """Background thread that polls for commands."""
        ...
    on_run_check = None

    def _handle_command(self, cmd: Dict):
        """Process a command from the server."""
        ...

    def _previous_api_key(self) -> str:
        ...

    def _persist_api_keys(self, current: str, previous: str):
        ...

    def _apply_new_api_key(self, payload: Dict):
        """set_api_key: switch to the key Central issued.

        Order matters. The new key goes to disk (config.ini, atomically) with
        the old one as api_key_previous BEFORE this process uses it, so a
        crash at any point leaves a station that boots with a key Central
        accepts. A save that fails raises, so the command is not acked and
        Central redelivers it; the old key is untouched and still valid.
        """
        ...

    def _try_previous_api_key(self, send: Callable[[], Optional[Dict]]):
        """Central rejected our key and we hold a previous one: try it. If it
        works, go back to it for good (persisted). Returns the reply, or None
        if the previous key was rejected too (the current key stays)."""
        ...

    def _forget_previous_api_key(self):
        """Central accepted the current key, so it has retired the old one."""
        ...

    def _ack_command(self, cmd_id: int):
        """Acknowledge command was processed.

        Primary path: an 'a' event through the offline queue — it rides the
        WiFi/NB-IoT failover with the next batch, so field stations can ack.
        The legacy direct DELETE (WiFi-only) is kept as a fast path; its
        failure is expected and harmless on cellular."""
        ...
    on_restart = None
    on_calibrate = None
    on_update = None
    on_set_config = None
    on_set_frequencies = None
