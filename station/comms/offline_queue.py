"""
Offline Queue for RelayStation
SQLite-backed queue for storing events when network is unavailable.
Designed for NB-IoT with spotty connectivity.

Log events are stored in a separate table with a smaller circular buffer
to prevent error logs from crowding out detection data during outages.
"""
import json
import sqlite3
import logging
import threading
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
MAX_LOG_EVENTS = 500
MAX_PAYLOAD_BYTES = 9000
MAX_EXECUTED_COMMANDS = 200
DEFAULT_LOCKED_REPORT_INTERVAL_SEC = 60.0

class OfflineQueue:
    """SQLite-backed queue for offline event storage."""

    def __init__(self, db_path: str=None, max_events: int=10000, locked_report_interval=None):
        """
        Initialize offline queue.

        Args:
            db_path: Path to SQLite database (default: ~/.relaystation/queue.db)
            max_events: Maximum data events to store (oldest get pruned)
            locked_report_interval: Seconds between locked-tag ('k') events per
                frequency. A number, or a zero-argument callable read on every
                push so a remote set_config takes effect live (no restart).
                None keeps DEFAULT_LOCKED_REPORT_INTERVAL_SEC.
        """
        ...

    def _connect(self):
        """Open a connection with durable, concurrency-safe pragmas. WAL +
        synchronous=NORMAL is crash-safe on flash (no corruption; may lose at
        most the last commit on a power cut) and lets the lock-free
        count()/get_stats() dashboard reads run without SQLITE_BUSY;
        busy_timeout waits out a writer instead of raising. journal_mode=WAL
        persists in the DB header, so it sticks across these per-op
        connections."""
        ...

    def _rebuild(self, reason: str=''):
        """Set aside a corrupt DB and recreate it empty. Losing the backlog is
        unfortunate but strictly better than an INDEFINITE blackout: a corrupt
        read otherwise propagates into the sender loop's broad except and hangs
        it forever, and a plain restart can't clear it (CREATE INDEX IF NOT
        EXISTS never rescans corrupt event pages). Called at init AND at runtime
        when a read hits malformed data."""
        ...

    def _init_db(self):
        """Initialize database schema."""
        ...

    def push(self, event_type: str, payload: Dict) -> int:
        """
        Add event to queue.

        Args:
            event_type: Event type (d=detection, h=heartbeat, k=locked, r=retrieved)
            payload: Event data dictionary

        Returns:
            Event ID, or -1 if the payload was rejected as oversized
        """
        ...

    def locked_report_interval(self) -> float:
        """Current seconds between locked-tag reports per frequency.

        Resolved on every call so a callable supplied at construction (the
        station passes one reading config) makes a remote change take effect
        without a restart. Anything unusable falls back to the default rather
        than raising on the detection thread.
        """
        ...

    def push_detection(self, frequency_khz: int, signal_db: int, confidence_pct: int, is_locked: bool=False, extra=None) -> int:
        """
        Add detection event to queue.

        Args:
            frequency_khz: Frequency in kHz (e.g., 151200 for 151.200 MHz)
            signal_db: Signal strength in dB
            confidence_pct: Confidence percentage (0-100)
            is_locked: Whether tag is locked
            extra: optional zero-argument callable returning more fields for
                the event. Called only when an event is actually written, so
                a rate-limited locked pulse costs nothing (comms/tag_window.py
                drains its per-tag window through this).
        """
        ...

    def push_heartbeat(self, cpu_pct: int, mem_pct: int, temp_c: Optional[int], active_tags: int, uptime_sec: int, extras: Optional[Dict]=None) -> int:
        """
        Add heartbeat event to queue. `extras` carries small detector-truth
        fields (sdr, loop count) the server needs for degraded-state checks.
        """
        ...

    def push_log(self, level: str, message: str) -> int:
        """
        Add log event to the separate log queue (circular buffer).
        Logs are stored separately from data events to prevent error logs
        from crowding out detection data during connectivity outages.

        Args:
            level: Log level (D=debug, I=info, W=warning, E=error)
            message: Log message
        """
        ...
    HEARTBEAT_THIN_S = 600
    HEARTBEAT_THIN_ABOVE = 200
    HEARTBEAT_THIN_OLDER_S = 7200

    def pop_batch(self, max_count: int=50, max_logs: int=5, max_bytes: Optional[int]=None) -> List[Dict]:
        """A batch to send: the present first, then the past.

        Two lanes. The LIVE lane is the newest heartbeat plus everything
        that arrived since the last successful send (locks before
        detections), so after an outage Central sees the station's current
        state in the first batch and a fresh lock never queues behind
        history. The BACKLOG lane fills what is left oldest-first,
        detections and locks before heartbeats. Both lanes stop at
        max_count events and at max_bytes of payload (the modem caps a POST
        at 10 kB; sizing by bytes instead of count is what stops the old
        halve-then-creep oscillation against that cap). Logs ride along
        from their own table as before. Call mark_sent() after a send.

        Self-heals on runtime DB corruption instead of letting a
        malformed-image error propagate into the sender loop's broad except,
        which would hang draining forever (the observed indefinite-blackout
        path). Rebuild drops the backlog: strictly better than never
        draining again, and a plain restart cannot clear the corruption."""
        ...

    def _heartbeat_count_cached(self) -> int:
        ...

    def thin_backlog_heartbeats(self, keep_every_s: int=None, older_than_s: int=None) -> int:
        """Keep one heartbeat per keep_every_s among those older than
        older_than_s (the newest in each bucket), delete the rest. The newest
        heartbeat overall is never touched. Returns rows deleted."""
        ...

    def _pop_batch_impl(self, max_count: int=50, max_logs: int=5, max_bytes: Optional[int]=None) -> List[Dict]:
        ...

    def mark_sent(self, events: list):
        """
        Remove successfully sent events from their respective tables.

        Args:
            events: List of event dicts (with 'id' and 'source' keys)
                    OR list of integer IDs (legacy — assumes 'events' table)
        """
        ...

    def increment_attempts(self, events: list):
        """
        Increment attempt count for failed sends.

        Args:
            events: List of event dicts (with 'id' and 'source' keys)
                    OR list of integer IDs (legacy — assumes 'events' table)
        """
        ...

    def was_command_executed(self, cmd_id: int) -> bool:
        """Whether this command ID has already been executed locally."""
        ...

    def record_command_executed(self, cmd_id: int):
        """Remember an executed command ID (pruned to the most recent
        MAX_EXECUTED_COMMANDS)."""
        ...

    def _prune_old_events(self, conn: sqlite3.Connection):
        """Remove oldest data events if over limit (log_events prunes itself)."""
        ...

    def count(self) -> int:
        """Get total number of events in both queues."""
        ...

    def clear(self):
        """Clear all events from both queues."""
        ...

    def get_stats(self) -> Dict:
        """Get queue statistics."""
        ...
