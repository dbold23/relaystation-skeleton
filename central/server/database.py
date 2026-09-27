"""
Database layer for RelayStation Central Server
SQLite-backed storage for stations, events, and tags
"""
import sqlite3
import hashlib
import hmac
import json
import math
import re
import logging
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from contextlib import contextmanager

def _event_time_text(t) -> Optional[str]:
    """A station event's unix 't' in the text shape rows are written in."""
    ...

def _finite_num(v):
    """v if it is a real, finite int or float, else None. JSON Infinity and
    NaN parse as floats; int() of one raises and JSONResponse refuses to
    encode one, so a single such value used to 500 a whole endpoint."""
    ...

def _safe_float(v, scale: float=1.0) -> Optional[float]:
    """float(v) / scale, or None for anything that is not a finite number.
    Infinity and NaN parse as floats but crash int() and JSON output, so a
    station sending one would otherwise poison its whole batch."""
    ...

def key_fingerprint(key: Optional[str]) -> Optional[str]:
    """First 8 hex of sha256(key): tells two keys apart in a log or a status
    reply without disclosing either. Never log or return a key itself."""
    ...

def utc_timestamp(dt: Optional[datetime]=None) -> str:
    """UTC wall-clock time in the text shape CURRENT_TIMESTAMP writes
    ('YYYY-MM-DD HH:MM:SS').

    Every TIMESTAMP column here is TEXT underneath, so a WHERE on one is a
    string comparison. Bind this, never a datetime object: a bound datetime
    only becomes comparable text through sqlite3's default adapter, which is
    deprecated as of Python 3.12 and is not the shape the rest of this file
    writes. get_active_tags and the retired-tag cleanup bound raw datetimes
    against tags.last_seen (bug A, 2026-09-08)."""
    ...
REDUCED_OFFLINE_MIN = 60.0

def mode_offline_threshold_min(nbiot_mode, base_full_min: float, heartbeat_interval_s=None, reduced_base_min=None) -> float:
    """Minutes of last_seen silence before a station of this mode is offline.

    Two inputs, and the second is what makes this safe:

    * the operator's setting for the mode — offline_threshold_min for full,
      offline_threshold_reduced_min for a data-saving station;
    * a FLOOR of 2x the station's own reported check-in cadence, which no
      setting can undercut.

    The floor exists because the setting and the cadence are configured in
    different places. An operator who tells a station to check in twice a day
    and forgets to widen the server threshold would otherwise watch it sit
    permanently "offline" while working perfectly. The station knows its own
    cadence and now reports it ('hbi'), so the server derives the honest
    minimum instead of trusting a mirrored number to stay in sync. A station
    too old to report it passes None and gets exactly the previous behaviour.

    A reduced station ALWAYS reports nb='reduced', so a NULL mode is never a
    slow-cadence station — it's a legacy/fast station or one mid-provisioning;
    treating None as full catches a genuine drop fast, which is the operator's
    stated priority.
    """
    ...
TAG_MATCH_TOL_KHZ = 3

def site_key(station_id: str, explicit=None) -> str:
    ...

def _int_or_none(value):
    ...

def modem_state_from(rssi, cereg) -> str:
    """Name the modem's condition. Both None means the station could not get
    an answer: the modem did not respond to AT (UART asleep or the module
    hung, the failure that needed a hardware reset in the field) or the read
    itself failed (port busy). Either way it is a different thing from having
    no signal, and since Relay-Cellular stopped reporting a failed read as
    rssi 99 / CEREG 0, a 'no_signal' here is the modem's own word."""
    ...

def parse_modem_health_line(message: str):
    """(rssi, cereg) from a forwarded "NB-IoT health: ..." warning, with
    'None' fields as None; None when the line is not a modem report."""
    ...

class Database:
    """SQLite database for central server"""

    def __init__(self, db_path: str=None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        ...

    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        ...

    @contextmanager
    def _transaction(self):
        """Context manager for database transactions"""
        ...

    def _init_schema(self):
        """Initialize database schema"""
        ...

    def register_station(self, station_id: str, api_key: str, location: str=None, latitude: float=None, longitude: float=None, station_type: str='cellular', sdr_center_hz: float=None, freq_min_hz: float=None, freq_max_hz: float=None, hunt_mode: bool=None) -> bool:
        """
        Register a new station or update existing.

        Args:
            station_id: Unique station identifier
            api_key: API key for authentication
            location: Optional location description
            station_type: Hardware lineage ('cellular' today; picks the install repo)
            latitude: Optional GPS latitude
            longitude: Optional GPS longitude
            sdr_center_hz: Band plan — SDR centre; passband is this +/- rate/2
            freq_min_hz/freq_max_hz: search band (clamped to the passband)
            hunt_mode: True = no whitelist, uniform comb (unknown frequencies)

        Band-plan args are None-safe: None means "leave as-is" on update and
        "use the renderer's 151 MHz defaults" on insert, so callers that predate
        the band plan keep working unchanged.

        Returns:
            True if created, False if updated
        """
        ...

    def update_station(self, station_id: str, fields: Dict) -> bool:
        """Apply an allowlisted set of operator-edited fields to a station.

        Returns False if the station does not exist. Unknown keys are ignored
        rather than raising, so a newer dashboard talking to an older server
        degrades to writing the fields it does understand.

        A station may not uplink through itself, which would render as a node
        hanging off nothing and would make the topology walk loop.
        """
        ...

    def record_measured_range(self, station_id: str, range_m) -> None:
        """Cache a range walk's own answer on the station it belongs to.

        The full computation (correlate the walk against detections, raster
        it, fit the path loss) is far too heavy to run for every station on
        every dashboard poll, so the result is stored when a walk is looked
        at. A number somebody walked outranks a number somebody typed, and
        this is what lets the map say which it is showing.
        """
        ...

    def delete_station(self, station_id: str) -> bool:
        """
        Delete a station and all its associated data (tags, events, commands).

        Returns:
            True if station existed and was deleted, False if not found
        """
        ...

    def verify_api_key(self, station_id: str, api_key: str, require_active: bool=True) -> bool:
        """Verify a station API key, completing a key rotation if it is the
        pending one.

        The current key always verifies. While a rotation is pending the new
        key verifies too, and its first use promotes it: api_key becomes the
        new key, the old one stops working, and the set_api_key command that
        carried it is scrubbed. Promotion is keyed on the station actually
        using the new key, not on its ack, so a station that acked without
        switching (firmware that does not know set_api_key acks unknown
        commands) keeps the old key working instead of being locked out.
        """
        ...

    def _scrub_key_commands(self, conn, station_id: str):
        """Drop the key from every set_api_key command for a station and
        retire the unacked ones. The key must not outlive its delivery in the
        commands table, and a cancelled or superseded one must not be
        redelivered."""
        ...

    def _promote_pending_key(self, station_id: str, pending: str):
        ...

    def begin_key_rotation(self, station_id: str, new_key: str, queue_command: bool=True) -> Optional[int]:
        """Stage `new_key` as the station's pending key.

        Both keys authenticate until the station uses the new one. With
        queue_command, a set_api_key command carrying the key is queued in the
        same transaction, so a pending key never exists without its delivery.
        Returns the command id (or 0 when no command was queued). Raises
        ValueError if the station does not exist or a rotation is already
        pending: replacing a pending key a station may already have saved
        would leave it holding a key Central no longer knows.
        """
        ...

    def cancel_key_rotation(self, station_id: str) -> bool:
        """Forget a pending key; the current key stays. Returns whether one
        was pending."""
        ...

    def replace_api_key(self, station_id: str, new_key: str) -> bool:
        """Replace the key outright: the old key stops working now. For a
        station nobody is running (retire a leaked key without deleting the
        station's history) or one being re-keyed by hand at the bench."""
        ...

    def get_key_status(self, station_id: str) -> Optional[Dict]:
        """Rotation state without any key material: a short fingerprint of
        the current key (enough to tell two keys apart in a log, useless to
        an attacker), whether a rotation is pending and since when, and when
        the key last changed."""
        ...

    def update_station_heartbeat(self, station_id: str, cpu_pct: int, mem_pct: int, temp_c: Optional[int], active_tags: int, uptime_sec: int):
        """Update station heartbeat data"""
        ...

    def get_all_stations(self) -> List[Dict]:
        """Get all registered stations with status"""
        ...

    def get_station(self, station_id: str) -> Optional[Dict]:
        """Get single station details"""
        ...

    def store_events(self, station_id: str, events: List[Dict]):
        """
        Store batch of events from a station.

        Args:
            station_id: Source station ID
            events: List of event dicts with 'e' (type), 't' (timestamp), etc.
        """
        ...
    MIN_PLAUSIBLE_EPOCH_S = 1000000000
    REPLAY_SPAN_S = 900

    @classmethod
    def _batch_clock_skew_s(cls, events: List[Dict]) -> Optional[float]:
        """Seconds this station's clock lags the server's, or None.

        Every event carries a STATION-side epoch, and a range walk matches
        detections to phone GPS fixes within range_calibration.MAX_GAP_S of
        those stamps -- so a skewed station clock drops every detection out
        of the correlation while the dashboard stays green. Nothing measured
        this before the 2026-09-10 field walk that came back empty.

        Measured against the NEWEST heartbeat in the batch: an event replayed
        out of the offline queue is legitimately old, so only the freshest
        stamp separates a wrong clock from a late delivery. Positive = the
        station's clock is behind the server's.
        """
        ...

    def _process_detection(self, conn: sqlite3.Connection, station_id: str, event: Dict):
        """Process detection event - update tags table.

        The station reports the frequency it MEASURED (a median of peak
        estimates), so one tag arrives as 151.239, 151.240, 151.241 from one
        read to the next. Rows are keyed on the tag it was matched to: the
        deployment out at this station's site at that moment, within the
        detector's tolerance. No such deployment means the detection is
        unlisted, whatever the station's own whitelist said."""
        ...

    def _upsert_tag(self, conn: sqlite3.Connection, station_id: str, event: Dict, locked: bool) -> None:
        ...

    @staticmethod
    def _store_tag_window(conn: sqlite3.Connection, station_id: str, event: Dict, freq_khz: int, raw_khz: int, dep_id, at: str) -> None:
        """Keep the pulse-accounting fields a 'k' report carries. A field
        that does not parse is stored as NULL rather than failing the batch:
        the report itself has already counted."""
        ...

    def get_tag_windows_for_report(self, station_id: str, raw_khz: int, hours: float=72.0) -> List[Dict]:
        """The windows of whichever tag this station's report at raw_khz was
        matched to (its newest window at that raw frequency says which)."""
        ...

    def get_tag_windows(self, frequency_khz: int, station_id: Optional[str]=None, hours: float=24.0, limit: int=5000) -> List[Dict]:
        """Pulse-accounting windows for one tag, oldest first, over the last
        `hours` of station time (newest `limit` rows at most)."""
        ...

    def _process_tag_locked(self, conn: sqlite3.Connection, station_id: str, event: Dict):
        """Process tag locked event — same upsert as a detection, locked."""
        ...

    def _site_of(self, conn: sqlite3.Connection, station_id: str) -> str:
        ...

    def _active_deployments_sql(self, at: str):
        ...

    def _uses_deployments(self, conn) -> bool:
        """Once anything has ever been put out, a detection that matches no
        deployment at its site and time is unknown, full stop. Only an
        installation that has never deployed a tag falls back to the
        station's own whitelist verdict."""
        ...

    def _match_deployment(self, conn, station_id: str, freq_khz: int, at: Optional[str], tolerance_khz: int=TAG_MATCH_TOL_KHZ) -> Optional[Dict]:
        """The deployment out at this station's site at time `at` (None =
        any not-yet-retrieved one) whose frequency is nearest to the
        measurement, within tolerance. A site-specific deployment beats an
        all-sites one at the same distance."""
        ...

    def _consolidate_tags(self, conn: sqlite3.Connection) -> int:
        """One-shot at migration: fold rows keyed on a measured kHz into the
        deployed tag they belong to (site- and time-aware), summing counts and
        keeping the extremes. Returns rows merged."""
        ...

    def get_deployments(self, include_retired: bool=False, site: Optional[str]=None) -> List[Dict]:
        """Deployments, active by default (retrieved_at NULL). `site` filters
        to that site plus the all-sites rows."""
        ...

    def deployments_for_station(self, station_id: str) -> List[Dict]:
        """What this station should listen for: the active deployments at
        its site plus the all-sites ones."""
        ...

    def add_deployment(self, frequency_khz: int, label: Optional[str]=None, pulse_width_ms: Optional[float]=None, site: Optional[str]=None, deployed_at: Optional[str]=None) -> int:
        """Put a tag out. An active row at the same frequency and site is
        updated rather than duplicated; a retired one is left as history and
        a new row starts. Returns the row id."""
        ...

    def retire_deployment(self, frequency_khz: int, site: Optional[str]=None, retrieved_at: Optional[str]=None) -> int:
        """The tag came back (or the animal did). Keeps the row as history so
        detections from while it was out still resolve to it. Returns rows
        retired. `site` None retires the all-sites row; 'any' retires every
        active row at that frequency."""
        ...

    def remove_deployment(self, frequency_khz: int, site: Optional[str]='any') -> bool:
        """Hard delete (a typo, not a retrieval)."""
        ...

    def create_view_link(self, token: str, label: Optional[str]=None) -> Dict:
        ...

    def list_view_links(self, include_revoked: bool=False) -> List[Dict]:
        ...

    def revoke_view_link(self, link_id: int) -> bool:
        ...

    def view_link_active(self, token: str) -> bool:
        """Read-only check for the live feed, which a page polls: counting
        every poll would be a write per viewer per half minute."""
        ...

    def open_view_link(self, token: str) -> Optional[Dict]:
        """The live link for a token, counting the open; None if the token is
        unknown or revoked."""
        ...

    def _sync_known_frequencies_mirror(self, conn: sqlite3.Connection) -> None:
        """known_frequencies = the distinct active frequencies, for any reader
        that still looks there."""
        ...

    def _process_tag_retrieved(self, conn: sqlite3.Connection, station_id: str, event: Dict):
        """Process tag retrieved event"""
        ...

    @staticmethod
    def advance_energy(prev_session, prev_wh, prev_total, session, wh):
        """(total, session_high_water) after one reported energy counter.

        Pure so it can be tested against the cases that actually occur: a
        restart (the token changes and the counter begins again at zero), a
        replayed or out-of-order heartbeat from a flushed offline queue (a
        counter BELOW the high-water mark for its session), and a first report.
        Only positive deltas are added, so nothing a late packet does can make
        the fleet appear to have used negative energy.
        """
        ...
    FUTURE_STAMP_TOLERANCE_S = 300

    @classmethod
    def _ordering_stamp(cls, stamp, now: Optional[float]=None):
        """(stamp to store, bound past which a stored stamp is wrong).

        The forward-only guards (last_heartbeat_event_t, modem_reported_at)
        order reports by the STATION's clock. A single stamp from the future
        used to freeze them: on 2026-09-11 elkhorn-radio-shack-2 read a
        modem clock 25,198 s fast, heartbeats went out 7 h ahead, and after
        the clock was put right every true heartbeat was "older" than the
        stored mark and dropped. fw, cfg, the stage partition and the modem
        state stood still for 7 h while last_heartbeat kept moving, which
        is exactly the window in which an operator checks whether an update
        (command 162) landed. A clock set to 2099 would freeze them for good.

        So a stamp more than the tolerance ahead is stored as server time
        (it is known wrong, and receive time is the best order we have), and
        a stored stamp already past the bound (written before this fix)
        no longer blocks anything. A replayed heartbeat that is honestly old
        is still rejected.
        """
        ...

    def _process_heartbeat(self, conn: sqlite3.Connection, station_id: str, event: Dict):
        """Process heartbeat event ('w'/'thr' are the optional power extension)"""
        ...

    def _apply_modem_report(self, conn: sqlite3.Connection, station_id: str, rssi, cereg, reported_at) -> None:
        """Record what the station's modem reported. Keyed on the STATION's
        own timestamp so that a queue flush (which arrives oldest-first) and a
        late duplicate can never overwrite a newer report with an older one."""
        ...

    def _apply_modem_from_log(self, conn: sqlite3.Connection, station_id: str, message: str, reported_at) -> None:
        """The watchdog's "NB-IoT health: ..." warning is the modem report a
        station sends when it CANNOT heartbeat over cellular; it is how the
        blackout's cause reaches Central once any link returns."""
        ...

    def _backfill_modem_state(self, conn: sqlite3.Connection) -> None:
        """One-shot at migration: the newest modem report per station from
        what is already stored (cellular heartbeats carry q/cr; health
        warnings carry cereg/rssi), so the page is not blank until the next
        cellular check-in, which for a dark station is exactly the one that
        never comes."""
        ...
    LOG_DEDUP_WINDOW_S = 3600

    def _collapse_repeated_log(self, conn: sqlite3.Connection, station_id: str, event: Dict, timestamp: int) -> bool:
        """If this log message repeats one seen within the dedup window,
        bump that row's repeat_count/last_timestamp and report True (caller
        skips the raw event insert). First occurrences return False and are
        stored normally by _process_log, which registers them here."""
        ...

    def _process_log(self, conn: sqlite3.Connection, station_id: str, event: Dict):
        """Process log event"""
        ...

    def get_recent_detections_by_frequency(self, station_id: str, frequency_khz: int, seconds: int=10, tolerance_khz: int=5) -> List[Dict]:
        """Get recent detection events for a specific station and frequency.

        Queries the events table for detection ('d') and locked-tag ('k') events
        within the last N seconds, parses JSON payload, and filters by frequency
        within tolerance.
        """
        ...

    def get_detections_in_window(self, station_id: str, frequency_khz: int, start_ts: int, end_ts: int, tolerance_khz: int=5) -> List[Dict]:
        """Detection ('d'/'k') events for a station+frequency inside an
        absolute time window. Same payload parsing as
        get_recent_detections_by_frequency, but bounded on both ends so a
        finished range-calibration session replays identically forever.
        """
        ...

    def is_tag_locked(self, station_id: str, frequency_khz: int, tolerance_khz: int=2) -> bool:
        """Is this frequency currently locked on this station?

        A locked tag reports at most one event per frequency per 60 s (the
        lock rate-limit), so a range walk against a locked tag collects ~1
        sample a minute instead of one per pulse — the range page warns the
        tester up front. Tolerance matches the detector's ±2 kHz whitelist
        window.
        """
        ...

    def get_all_tags(self, include_retrieved: bool=False, include_muted: bool=True) -> List[Dict]:
        """Get all tracked tags across all stations"""
        ...

    def get_active_tags(self, hours: int=24, include_muted: bool=False) -> List[Dict]:
        """Get tags seen in the last N hours (noise-muted hidden by default)"""
        ...

    def mark_tag_retrieved(self, frequency_khz: int, station_id: str):
        """Mark a tag as retrieved"""
        ...

    def lock_tag(self, frequency_khz: int, station_id: str):
        """Lock a tag (mark for focused tracking)"""
        ...

    def clear_all_tags(self, station_id: str=None):
        """Clear all active tags (mark as retrieved). If station_id given, only that station."""
        ...

    def delete_retrieved_tags(self, station_id: str=None):
        """Permanently delete all retrieved tags. If station_id given, only that station."""
        ...

    def queue_command(self, station_id: str, command_type: str, payload: Dict=None) -> int:
        """
        Queue a command for a station.

        Args:
            station_id: Target station
            command_type: Command type (e.g., 'restart', 'recalibrate', 'update_config')
            payload: Optional command payload

        A set_config for a key that already has an UNFETCHED set_config queued
        supersedes it rather than stacking behind it. Two reasons, both seen for
        real (2026-07-17: five identical nbiot_mode commands queued on one
        station):

          * The control gives no instant feedback in low-power mode — the
            confirming heartbeat is itself slowed by the change — so an operator
            reasonably taps again. Every extra copy is cellular spent to set a
            value that is already set.
          * If you change your mind, the older queued value is simply wrong.
            Delivering "reduced" and then "full" wastes a round trip; delivering
            them out of order on a flaky link is worse.

        Only UNFETCHED commands are superseded — once a station has it, the
        at-least-once delivery contract owns it, and rewriting history there
        would desync the ack.
        """
        ...

    def get_pending_config(self, station_id: str, key: str) -> Optional[str]:
        """Value of a set_config for `key` that the station has not run yet.

        Lets the dashboard show "Low (pending)" instead of the stale current
        value, which otherwise reads as "your tap did nothing" for a full
        low-power cycle — and is what makes people tap again.
        """
        ...
    COMMAND_REDELIVERY_GRACE_MIN = 10
    COMMAND_MAX_DELIVERIES = 5

    def get_pending_commands(self, station_id: str) -> List[Dict]:
        """Get deliverable commands for a station and stamp them fetched.

        Delivers: never-fetched commands, plus unacked ones whose last fetch
        is older than the redelivery grace. Acked (executed_at) commands are
        never redelivered — the ack arrives via an 'a' event or the legacy
        DELETE route."""
        ...

    def peek_pending_commands(self, station_id: str) -> List[Dict]:
        """Commands to ride the /events reply. Takes NO delivery slot.

        The reply is a fast path, not an owner. get_pending_commands() is
        the owner: it stamps fetched_at and spends one of
        COMMAND_MAX_DELIVERIES, and that budget only means something if the
        station on the other end can ACKNOWLEDGE what it was given.

        A station running firmware older than commands-on-reply cannot read
        the key at all, so when the reply spent a delivery the command was
        consumed in silence, the station's own poll saw an empty list for
        the whole grace window, and at the cap the command was abandoned
        with an alert. Live on pi1 (2026-09-17): update commands 167 and
        171 both had fetched_at set and delivery_count climbing with
        executed_at NULL, while a GET from the station with its own key
        returned no commands. It cannot update itself to the firmware that
        would let it read the reply, because the update is the command
        being eaten. The faster the batch cadence relative to the poll, the
        more often the reply wins the race: on WiFi, 15 s batches against a
        60 s poll, it won three for three.

        So: offer only commands the poll has NEVER taken (fetched_at IS
        NULL), and stamp nothing. A station that acts on the reply acks,
        executed_at is set, and it is never offered again. A station that
        ignores the reply leaves the poll's budget untouched and whole.
        Once the poll has taken a command, this path goes quiet for it, so
        it cannot re-offer forever behind the poll's back.
        """
        ...

    def mark_command_executed(self, command_id: int):
        """Mark a command as executed"""
        ...

    def get_logs(self, station_id: str=None, level: str=None, limit: int=100) -> List[Dict]:
        """Get logs, optionally filtered"""
        ...

    def insert_alert(self, severity: str, kind: str, message: str, station_id: str=None, dedup_key: str=None, notified: bool=False) -> int:
        """Insert a person-facing alert; returns the new alert id."""
        ...

    def get_alerts(self, limit: int=100, unacked_only: bool=False, since_id: int=None) -> List[Dict]:
        """Get alerts, newest first."""
        ...

    def get_unacked_alert_count(self) -> int:
        ...

    def ack_alert(self, alert_id: int) -> bool:
        ...

    def ack_all_alerts(self) -> int:
        ...

    def resolve_alerts(self, dedup_key: str) -> int:
        """Clear any open alert with this dedup key, because the condition it
        described has ended.

        A station coming back is not news, it is the ABSENCE of news, and
        raising a second alert to say the first one is over doubles the cards
        the operator has to dismiss. "elkhorn-radio-shack is back online" and
        "elkhorn-radio-shack-2 heartbeats resumed" were two of the five cards
        in the 2026-09-12 feed. An alert that resolves itself must not ask for
        a click. Returns the number cleared.
        """
        ...

    def station_expects_freq(self, station_id: str, freq_khz: int) -> bool:
        """Public predicate: is a real tag deployed at this station within
        tolerance of this frequency? A lock there is a confirmed tag."""
        ...

    def find_recent_alert(self, dedup_key: str, within_hours: float, unacked_only: bool=True) -> Optional[Dict]:
        """Newest alert with this dedup_key inside the window (for de-dup)."""
        ...

    def mark_alert_notified(self, alert_id: int):
        ...

    def get_alert_settings(self) -> Dict[str, str]:
        ...

    def set_alert_setting(self, key: str, value: str):
        ...

    def get_tag_last_seen_map(self, station_id: str, freq_khz_list: List[int]) -> Dict[int, str]:
        """last_seen per frequency BEFORE a batch is stored — lets the alert
        engine detect a tag reappearing after a long silence (store_events
        overwrites last_seen, so this snapshot must be taken first)."""
        ...

    def get_heartbeat_history(self, station_id: str, hours: int=24, max_points: int=500) -> List[Dict]:
        """Health time series from stored 'h' events (oldest first).
        Downsamples evenly when there are more rows than max_points."""
        ...
    ACTIVITY_DULL_SX_DB = 3.0
    ACTIVITY_MAX_POINTS = 1500

    def get_activity(self, hours: int=24, bins: int=48, station_id: Optional[str]=None, now: Optional[int]=None) -> Dict:
        """Binned fleet activity for the dashboard charts.

        Three facts are kept apart on purpose, because this fleet has
        reported itself healthy while deaf: a station CHECKED IN (a
        heartbeat arrived), it was LISTENING (the SDR was attached and the
        detection loop moved), and it HEARD a tag (a detection). Per
        station and bin:

          hb     heartbeats in the bin
          det    detections ('d' and 'k') in the bin
          deaf   a heartbeat said sdr=false, or two or more heartbeats
                 showed the loop counter standing still
          look   channel-frames the detector examined ('st' partition,
                 every Nth heartbeat), None when no partition arrived
          sx     worst survey-gate excess over the noise model, dB
          state  off | deaf | listening | heard  (heard wins: a detection
                 is proof of hearing whatever the heartbeat said)

        Detections are also grouped per tag for the abacus (one row per tag,
        one mark per station and bin) and sampled raw for the band chart.
        Times are station event times (the same clock the range walk uses).
        """
        ...

    def insert_diagnostics(self, station_id: str, ts: int, kind: str, payload: str, analysis: str) -> int:
        ...

    def get_latest_diagnostics(self, station_id: str) -> Optional[Dict]:
        ...
    NOISE_CONSENSUS_LABELS = 3
    NOISE_FREQ_TOL_KHZ = 2

    def _station_expects_freq(self, conn, station_id: str, freq_khz: int) -> bool:
        """True if a real tag is deployed at this station within tolerance of
        freq. This is the escape hatch for 'what if it's eventually a real tag':
        the moment an operator deploys a tag at a frequency, that frequency
        stops being treated as a known interferer there — a deliberate human
        intent overrides the machine's noise assumption."""
        ...

    def _is_known_noise_freq(self, conn, freq_khz: int, station_id: Optional[str]=None) -> bool:
        """A frequency is a known interferer only when HUMANS have ruled it
        noise enough times AT THIS STATION — and only while no real tag is
        deployed there. Machine ('auto') labels never count toward the
        consensus, so the auto-labeler cannot bootstrap itself; scoping by
        station keeps a location-bound carrier from muting a genuine tag at the
        same frequency elsewhere. NULL label_source = legacy row = counts as
        human (back-compat)."""
        ...

    def is_interferer_freq(self, station_id: str, freq_khz: int) -> bool:
        """Public predicate for the alert engine: is this (station, freq) a
        human-confirmed interferer with no tag deployed there?"""
        ...

    def is_muted_freq(self, station_id: str, freq_khz: int) -> bool:
        """Has a human already ruled this frequency noise?

        Labelling a review candidate 'noise' sets tags.is_muted within
        NOISE_FREQ_TOL_KHZ (see set_candidate_label). That verdict was being
        recorded and then ignored by the alert engine, so 151.370 at Elkhorn -
        a documented carrier, muted by the operator - still pushed
        tag_reappeared to a phone on 2026-09-12. The whole point of the review
        queue is that a verdict, once given, holds.
        """
        ...

    def add_candidate(self, station_id: str, cand: Dict) -> bool:
        """Upsert one review candidate (dedup on cand_uid). Returns True if new.

        Candidates at a frequency the reviewer has repeatedly labeled noise
        arrive pre-labeled 'noise' — a persistent interferer (e.g. a marina
        carrier re-captured ~100x/hr) must not refill the review queue after
        the human has already ruled on it."""
        ...

    def get_candidates(self, station_id: Optional[str]=None, label: Optional[str]=None, only_unlabeled: bool=False, limit: int=200, with_img: bool=True, freq_khz: Optional[int]=None) -> List[Dict]:
        ...

    def label_candidate(self, cand_id: int, label: str) -> bool:
        """Record a human verdict; a 'noise' verdict also mutes matching tags
        on the Tags page (reversible — 'tag' un-mutes). Nothing is deleted."""
        ...

    def candidate_counts(self) -> Dict:
        ...

    def get_diagnostics_history(self, station_id: str, limit: int=20, include_payload: bool=False) -> List[Dict]:
        ...

    def get_fleet_latest_diagnostics(self) -> List[Dict]:
        """Latest bundle per station (payload included — fleet comparison)."""
        ...

    def get_pending_diagnostics_command(self, station_id: str) -> Optional[Dict]:
        """Newest run_diagnostics command still queued (never fetched), or
        picked up in the last 15 min with no bundle received since — drives
        the UI's queued/running indicator; clears when results arrive.
        fetched_at is the pickup signal (executed_at only means acked)."""
        ...

    def get_offline_stations(self, base_full_min: float, reduced_base_min: float=None) -> List[Dict]:
        """DEPLOYED stations silent longer than their per-mode offline threshold.

        A parked station is expected to be dark, so it is excluded here rather
        than at the call sites. This is the one chokepoint: it suppresses the
        alert row, the ntfy push and the recovery alert together, because all
        three are driven off this result. Several stations are switched off on
        purpose between field seasons and Central raised an outage for each of
        them on every sweep, which is how the Needs-attention card turned into
        noise nobody read.

        base_full_min is the offline_threshold_min for full-mode stations;
        reduced_base_min the setting for data-saving ones. Each row's own
        reported cadence floors the result. Filtered in Python (not SQL) so the
        per-mode threshold comes from the single shared helper.
        """
        ...

    def get_degraded_stations(self, base_full_min: float, reduced_base_min: float=None) -> List[Dict]:
        """Stations still reporting (fresh last_seen) whose heartbeats — the
        detection loop's only output — stopped: the 'green but deaf' state.

        Both bounds use the SAME per-mode threshold, so a station is never in
        both this set and get_offline_stations (buckets stay disjoint).
        """
        ...

    def cleanup_old_data(self, days: int=30):
        """Remove data older than specified days"""
        ...

    def get_stats(self) -> Dict:
        """Get database statistics"""
        ...

    def get_known_frequencies(self) -> List[Dict]:
        """Active deployments, oldest name kept for callers. Each row carries
        site (None = every site), deployed_at and retrieved_at."""
        ...

    def is_frequency_known(self, frequency_khz: int, tolerance_khz: int=5) -> bool:
        """Is any ACTIVE deployment within tolerance of this frequency?"""
        ...

    def upsert_tag(self, *, unique_key: str, frequency_khz: int, model: str=None, tag_type: str=None, job_number: str=None, serial_number: str=None, pulse_rate_ppm: float=None, pulse_width_ms: float=None, status: str=None, is_custom: bool=False) -> int:
        """Insert or update a tag in the registry. Returns row id."""
        ...

    def delete_tag(self, unique_key: str) -> bool:
        ...

    def get_tag_registry(self, include_custom: bool=True) -> list:
        """Return all registry tags (ATS + custom unless include_custom=False)."""
        ...

    def set_tag_species(self, unique_key: str, species: str=None) -> bool:
        """Assign (or clear, with None) the animal a registered tag is on.

        Validation of the species key belongs to the caller — the DB stores
        whatever string it is handed so an old row keeps its value across a
        catalog change instead of being silently dropped.
        """
        ...

    def get_registry_species(self) -> list:
        """(frequency_khz, species) for every registered tag that has one.

        The index a Resolver needs to give a bare detection its species.
        """
        ...

    def get_tag(self, unique_key: str) -> dict:
        ...

    def get_station_deployed_tags(self, station_id: str) -> list:
        """Return the full tag records currently deployed at a station."""
        ...

    def set_station_deployment(self, station_id: str, deployed_keys: list, updated_by: str=None) -> int:
        """Replace a station's deployed-tag set atomically. Returns count."""
        ...
    CONFIG_APPLY_GRACE_S = 600.0

    def mark_config_pushed(self, station_id: str):
        """Record the station's current reported fingerprint at push time."""
        ...

    @classmethod
    def config_push_state(cls, row, now: datetime=None) -> Optional[str]:
        """'pending' | 'not_applied' | None for a station row.

        None means nothing is outstanding: either no push, or the station's
        fingerprint moved after it, which is the only positive evidence that a
        push actually took effect. 'not_applied' is the case that cost a field
        trip -- Central said executed, the station had discarded it.
        """
        ...

    def create_test_session(self, session_id: str, station_id: str, name: str=None, antenna_type: str=None, antenna_height_m: float=None, antenna_azimuth_deg: float=None, antenna_tilt_deg: float=None, latitude: float=None, longitude: float=None, environment_type: str=None, notes: str=None) -> bool:
        """Create a new test session"""
        ...

    def end_test_session(self, session_id: str):
        """End a test session"""
        ...

    def delete_test_session(self, session_id: str) -> bool:
        """Delete a test session and all its measurements and waypoints."""
        ...

    def get_test_session(self, session_id: str) -> Optional[Dict]:
        """Get a single test session"""
        ...

    def get_all_test_sessions(self, station_id: str=None) -> List[Dict]:
        """Get all test sessions, optionally filtered by station"""
        ...

    def store_test_measurements_batch(self, session_id: str, station_id: str, measurements: List[Dict]):
        """Store a batch of test measurements"""
        ...

    def get_test_measurements(self, session_id: str, limit: int=1000) -> List[Dict]:
        """Get measurements for a test session"""
        ...

    def get_latest_test_measurements(self, session_id: str, seconds: int=5) -> List[Dict]:
        """Get the most recent measurements from a session"""
        ...

    def add_range_waypoint(self, session_id: str, station_id: str, distance_m: float, bearing_deg: float=None, waypoint_name: str=None, latitude: float=None, longitude: float=None, notes: str=None) -> int:
        """Add a range test waypoint and calculate stats from recent measurements"""
        ...

    def get_range_waypoints(self, session_id: str) -> List[Dict]:
        """Get all waypoints for a test session"""
        ...

    def get_test_session_summary(self, session_id: str) -> Dict:
        """Get summary statistics for a test session"""
        ...

    def export_test_session(self, session_id: str) -> Dict:
        """Export complete test session data as JSON-ready dict"""
        ...

    def create_range_session(self, session_id: str, station_id: str, target_frequency_khz: int, name: str=None, latitude: float=None, longitude: float=None, notes: str=None) -> bool:
        """Create a range-calibration session. latitude/longitude are the
        STATION's position frozen for this session — the walker's positions
        stream into range_track_points."""
        ...

    def add_range_track_points(self, session_id: str, station_id: str, points: List[Dict]) -> int:
        """Store a batch of phone GPS points.

        Each point: {'t': epoch_s, 'lat': .., 'lon': .., 'acc': accuracy_m
        or None, 'distance_m': precomputed station distance or None}.
        """
        ...

    def get_range_track_points(self, session_id: str) -> List[Dict]:
        """Full GPS track for a session, ascending by time."""
        ...

    def set_station_location(self, station_id: str, latitude: float, longitude: float) -> bool:
        """Set a station's coordinates without touching its api_key (unlike
        register_station). Range calibration needs real coordinates."""
        ...

    def get_range_sessions(self, station_id: str=None) -> List[Dict]:
        """Range-calibration sessions (newest first) with track-point counts."""
        ...
