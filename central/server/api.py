"""
REST API for RelayStation Central Server
FastAPI-based API for receiving station data and serving dashboard
"""
import asyncio
import csv
import hmac
import io
import json
import logging
import math
import os
import secrets
import tarfile
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from fastapi import FastAPI, HTTPException, Header, Request, Depends, Query, Cookie
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
from .database import Database, key_fingerprint, mode_offline_threshold_min, site_key as db_site_key
from .alerts import AlertEngine
from . import diagnostics as diagnostics_mod
from . import range_calibration as range_calc
from . import species as species_mod
from . import tag_behaviour
ADMIN_KEY_MIN_LEN = 16

def _read_admin_key_file() -> Optional[str]:
    """The key in ADMIN_KEY_FILE, or None if there is no usable one. Cached
    on (inode, size, mtime): one stat per admin request."""
    ...

def _admin_key() -> str:
    """The admin key in force right now."""
    ...

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run the periodic alert checks (station offline/online) while serving."""
    ...

class _RevalidatingStatic(StaticFiles):
    """StaticFiles that forces a revalidation instead of a blind cache hit.

    Starlette serves static assets with etag + last-modified but no
    Cache-Control. With no explicit policy a browser falls back to *heuristic*
    caching — typically a fraction of the age since last-modified — and mobile
    Safari holds on hard. The script tags are unversioned (/static/js/x.js), so
    a stale copy has no way to age out on its own: a deployed dashboard change
    could sit invisible on a phone while the server served the new file happily.
    That is a bad property for the thing you check in the field.

    'no-cache' does NOT mean "don't cache" — it means "cache it, but revalidate
    before use". Paired with the etag that is already sent, an unchanged file
    costs one conditional request answered 304 with no body, and a changed file
    is picked up immediately. For an admin dashboard on a handful of devices
    that trade is entirely worth it.
    """

    def file_response(self, *args, **kwargs):
        ...

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    """Browsers request /favicon.ico directly (bookmarks, older UAs)."""
    ...

def init_database(database: Database):
    """Initialize the database instance"""
    ...

def get_db() -> Database:
    """Dependency to get database instance"""
    ...

def get_alert_engine() -> AlertEngine:
    ...

class EventBatch(BaseModel):
    """Batch of events from a station"""
    sid: str
    events: List[Dict]

class CandidateBatch(BaseModel):
    """Review candidates (tiny detection thumbnails) uploaded for labeling."""
    sid: str
    candidates: List[Dict]

class CandidateLabel(BaseModel):
    label: str

class StationRegister(BaseModel):
    """Station registration request"""
    station_id: str
    api_key: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    sdr_center_hz: Optional[float] = None
    freq_min_hz: Optional[float] = None
    freq_max_hz: Optional[float] = None
    hunt_mode: Optional[bool] = None

class CommandCreate(BaseModel):
    """Command creation request"""
    command_type: str
    payload: Optional[Dict] = None

class TagRetrieve(BaseModel):
    """Tag retrieval request"""
    frequency_khz: int
    station_id: str

class FrequencyAdd(BaseModel):
    """Deploy a tag: a frequency out at a site from a date. site None means
    every site; deployed_at None means now."""
    frequency_mhz: float
    label: Optional[str] = None
    pulse_width_ms: Optional[float] = None
    site: Optional[str] = None
    deployed_at: Optional[str] = None

class DeploymentRetire(BaseModel):
    """The tag came back. site None retires the all-sites row, 'any' every
    active row at that frequency."""
    site: Optional[str] = None
    retrieved_at: Optional[str] = None

class TagUpsert(BaseModel):
    """Insert or update a row in the rich tag registry (ATS CSV or custom).

    ``unique_key`` is stable across edits; format:
        "<job_number>/<serial_number>/<tx_frequency_mhz:.3f>"
    Custom tags should use ``is_custom=True`` and prefix unique_key with
    "custom:" to prevent collision with ATS entries.
    """
    unique_key: str
    frequency_mhz: float
    model: Optional[str] = None
    tag_type: Optional[str] = None
    job_number: Optional[str] = None
    serial_number: Optional[str] = None
    pulse_rate_ppm: Optional[float] = None
    pulse_width_ms: Optional[float] = None
    status: Optional[str] = None
    is_custom: bool = False

class StationDeployment(BaseModel):
    """Replace a station's deployed-tag set (idempotent)."""
    deployed_keys: List[str]
    updated_by: Optional[str] = None

class DeploymentCommit(BaseModel):
    """Commit a station's deployment → queue set_tag_config command."""
    updated_by: Optional[str] = None
    confirm: str

async def verify_station(x_api_key: str=Header(...), x_station_id: str=Header(...)) -> str:
    """Verify station authentication"""
    ...

def _session_token() -> str:
    """Deterministic session-cookie value derived from the admin key.

    Login sets it as an HttpOnly cookie so the browser never has to keep
    the admin key readable in JS, and so HTML routes can be gated
    server-side (the old login overlay was client-side only — the pages
    leaked station/tag data to anyone who skipped it)."""
    ...

def _session_valid(cookie_value: Optional[str]) -> bool:
    ...

async def verify_admin(x_admin_key: Optional[str]=Header(None), admin_key: Optional[str]=Query(None), relay_session: Optional[str]=Cookie(None)) -> bool:
    """Verify admin auth via header, query param, or session cookie."""
    ...

def _species_resolver(database):
    """A Resolver primed with the registry's species assignments.

    Built per request rather than cached: assignments change from the UI, and
    a stale cache would show the old animal until a restart. The query is a
    handful of rows over an indexed column.
    """
    ...

@app.post('/api/v1/events')
async def receive_events(batch: EventBatch, station_id: str=Depends(verify_station)):
    """
    Receive batch of events from a station.
    Events can include: detections (d), heartbeats (h), logs (l), etc.
    """
    ...

@app.post('/api/v1/candidates')
async def receive_candidates(batch: CandidateBatch, station_id: str=Depends(verify_station)):
    """Receive review candidates (tiny detection thumbnails) from a station.
    Deduped on cand_uid so retries are safe; payloads are ~KB each."""
    ...

@app.get('/api/v1/stations/{station_id}/commands')
async def get_commands(station_id: str, verified_station: str=Depends(verify_station)):
    """Get pending commands for a station"""
    ...

@app.delete('/api/v1/stations/{station_id}/commands/{command_id}')
async def ack_command(station_id: str, command_id: int, verified_station: str=Depends(verify_station)):
    """Station acknowledges a command after executing it.

    The edge client (comms/central_client.py) DELETEs each command once
    handled; commands are already marked executed on fetch, so this ack is
    idempotent — deleting an unknown id still returns success.
    """
    ...

@app.post('/api/v1/heartbeat')
async def receive_heartbeat_legacy(request: Request, station_id: str=Depends(verify_station)):
    """
    Legacy heartbeat endpoint (compatibility with old Pi code).
    Redirects heartbeats to events batch format.
    """
    ...

@app.post('/api/v1/admin/stations')
async def register_station(req: StationRegister, _=Depends(verify_admin)):
    """Register a new station"""
    ...

@app.get('/api/v1/admin/stations')
async def list_stations(_=Depends(verify_admin)):
    """List all registered stations"""
    ...

@app.get('/api/v1/admin/stations/{station_id}')
async def get_station(station_id: str, _=Depends(verify_admin)):
    """Get single station details"""
    ...

class StationEdit(BaseModel):
    """Operator knowledge about a station. Everything here is typed by a
    person, because no heartbeat can report which repo a Pi runs, which
    gateway it talks through, what battery is bolted to the pole, or that the
    coax looked chewed."""
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    site: Optional[str] = None
    station_type: Optional[str] = None
    install_profile: Optional[str] = None
    uplink_station_id: Optional[str] = None
    deployed: Optional[int] = None
    antenna_type: Optional[str] = None
    antenna_azimuth_deg: Optional[float] = None
    range_m: Optional[float] = None
    power_source: Optional[str] = None
    panel_w: Optional[float] = None
    battery_wh: Optional[float] = None
    issue_flags: Optional[List[str]] = None
    notes: Optional[str] = None

@app.patch('/api/v1/admin/stations/{station_id}')
async def edit_station(station_id: str, req: StationEdit, _=Depends(verify_admin)):
    """Edit the operator-owned fields of one station.

    PATCH, not PUT: the editor sends only what changed, and a field left out
    must keep its value rather than being blanked. Clearing a field is an
    explicit empty string or null in the body, which Pydantic gives us as
    None, so `exclude_unset` is what separates "not sent" from "cleared".
    """
    ...

@app.delete('/api/v1/admin/stations/{station_id}')
async def delete_station(station_id: str, _=Depends(verify_admin)):
    """Delete a station and all its associated data"""
    ...

@app.get('/api/v1/admin/commands/{command_id}')
async def get_command_status(command_id: int, _=Depends(verify_admin)):
    """Lifecycle of one queued command — lets the UI show delivered/acked."""
    ...

@app.post('/api/v1/admin/stations/{station_id}/commands')
async def queue_command(station_id: str, cmd: CommandCreate, _=Depends(verify_admin)):
    """Queue a command for a station"""
    ...

class KeyRotate(BaseModel):
    """mode: 'command' (deliver over the command channel, default),
    'manual' (stage it and return it once, for a Pi re-keyed by hand), or
    'revoke' (replace the key now and discard it: the old key dies at once,
    for a station nobody runs any more)."""

@app.post('/api/v1/admin/stations/{station_id}/rotate-key')
async def rotate_station_key(station_id: str, req: KeyRotate, response: Response, _=Depends(verify_admin)):
    ...

@app.delete('/api/v1/admin/stations/{station_id}/rotate-key')
async def cancel_station_key_rotation(station_id: str, _=Depends(verify_admin)):
    """Forget the pending key; the current key stays in force. A station
    that already saved the pending key falls back to its previous one on the
    first 401 (Relay-Cellular central_client), so this does not strand it."""
    ...

@app.get('/api/v1/admin/stations/{station_id}/key-status')
async def station_key_status(station_id: str, _=Depends(verify_admin)):
    ...

@app.get('/api/v1/admin/keys')
async def fleet_key_status(_=Depends(verify_admin)):
    """Key rotation state of every station, and of the admin key itself
    (its source and fingerprint), for auditing a rotation. No key material."""
    ...

@app.get('/api/v1/admin/tags')
async def list_tags(active_hours: int=24, include_retrieved: bool=False, include_muted: bool=False, _=Depends(verify_admin)):
    """List all tags across all stations. Tags at frequencies the reviewer
    labeled noise are muted and hidden unless include_muted is set."""
    ...

@app.get('/api/v1/admin/tags/{frequency_khz}/behaviour')
async def tag_behaviour_view(frequency_khz: int, station_id: Optional[str]=None, hours: float=Query(24.0, gt=0, le=24 * 60), _=Depends(verify_admin)):
    """What one tag's pulse train says, from the windows its locked reports
    carry (server/tag_behaviour.py): presence, movement and pulse-rate state
    per station, plus the per-window series for a chart. A station running
    code older than Relay-Cellular d4f95ca sends no windows and shows none."""
    ...

@app.post('/api/v1/admin/tags/retrieve')
async def mark_retrieved(req: TagRetrieve, _=Depends(verify_admin)):
    """Mark a tag as retrieved"""
    ...

class TagLock(BaseModel):
    """Tag lock request"""
    frequency_khz: int
    station_id: str

@app.post('/api/v1/admin/tags/clear')
async def clear_all_tags(station_id: Optional[str]=None, _=Depends(verify_admin)):
    """Clear all active tags (mark as retrieved). Optional station_id filter."""
    ...

@app.delete('/api/v1/admin/tags/retrieved')
async def delete_retrieved_tags(station_id: Optional[str]=None, _=Depends(verify_admin)):
    """Permanently delete all retrieved tags. Optional station_id filter."""
    ...

class TestSessionCreate(BaseModel):
    """Create a new test session"""
    station_id: str
    name: Optional[str] = None
    antenna_type: Optional[str] = None
    antenna_height_m: Optional[float] = None
    antenna_azimuth_deg: Optional[float] = None
    antenna_tilt_deg: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    environment_type: Optional[str] = None
    notes: Optional[str] = None

class TestMeasurementBatch(BaseModel):
    """Batch of test measurements"""
    session_id: str
    station_id: str
    measurements: List[Dict]

class RangeWaypointCreate(BaseModel):
    """Create a range test waypoint"""
    distance_m: float
    bearing_deg: Optional[float] = None
    waypoint_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    notes: Optional[str] = None

@app.post('/api/v1/admin/tags/lock')
async def lock_tag(req: TagLock, _=Depends(verify_admin)):
    """Lock a tag (mark for tracking)"""
    ...

@app.get('/api/v1/admin/logs')
async def get_logs(station_id: Optional[str]=None, level: Optional[str]=None, limit: int=100, _=Depends(verify_admin)):
    """Get logs from stations"""
    ...

class AlertSettingsUpdate(BaseModel):
    """Partial update of alert settings (only provided keys change)."""
    settings: Dict[str, str]

@app.get('/api/v1/admin/alerts')
async def list_alerts(limit: int=100, unacked_only: bool=False, since_id: Optional[int]=None, _=Depends(verify_admin)):
    """Alert feed, newest first, plus the unacked count for the header bell."""
    ...

@app.post('/api/v1/admin/alerts/{alert_id}/ack')
async def ack_alert(alert_id: int, _=Depends(verify_admin)):
    """Acknowledge one alert."""
    ...

@app.post('/api/v1/admin/alerts/ack_all')
async def ack_all_alerts(_=Depends(verify_admin)):
    """Acknowledge every unacked alert."""
    ...

@app.get('/api/v1/admin/alerts/settings')
async def get_alert_settings(_=Depends(verify_admin)):
    """Effective alert settings (defaults merged with stored overrides).
    Includes the ntfy topic + server so Setup can render subscribe steps."""
    ...

@app.post('/api/v1/admin/alerts/settings')
async def update_alert_settings(req: AlertSettingsUpdate, _=Depends(verify_admin)):
    """Update alert settings (partial; only provided keys change)."""
    ...

@app.post('/api/v1/admin/alerts/test')
async def send_test_alert(_=Depends(verify_admin)):
    """Send a test ntfy push so lab members can verify their subscription."""
    ...

def public_base_url(request: Request) -> str:
    """The URL a station must use to reach this server, as the world sees it.

    Central runs behind a TLS-terminating proxy (Caddy on the fleet host)
    that forwards plain http to the container, so request.base_url reads
    http://<host>/ and every generated config and installer told the station
    to post to plain http, which the proxy answers with a 308 (found building
    elkhorn-radio-shack-2, 2026-09-10). The proxy states what it terminated
    in X-Forwarded-Proto and X-Forwarded-Host; take those when present and
    fall back to the request's own URL when there is no proxy.
    """
    ...

def nbiot_base_url() -> str:
    """Base URL a cellular station should use over NB-IoT.

    Must be a bare IP with http:// — the SIM7028's HTTP stack cannot do DNS or
    TLS reliably, so the station's public hostname is unusable on that path.
    Overridable per deployment; defaults to the Elastic IP the fleet already
    points at. Set to "" to omit the line entirely (WiFi-only deployments).
    """
    ...
_DEFAULT_SDR_CENTER = 151320000.0
_DEFAULT_FREQ_MIN = 151190000.0
_DEFAULT_FREQ_MAX = 151450000.0
_DEFAULT_SAMPLE_RATE = 2048000.0

def render_station_config(station: dict, server_url: str, freq_line: str='', nbiot_url: str='') -> str:
    """Render a station's complete config.ini. Single source of truth for the
    wizard's copy block + QR and the one-line installer's embedded config.

    Complete is the point: every section the detector reads is emitted
    explicitly, because each omitted key silently becomes a core/config.py
    fallback tuned for nothing in particular (see _DETECTION_DEFAULTS).
    """
    ...

def station_freq_line(database, station_id: str) -> str:
    """Comma-separated MHz for a station's OWN deployed tags.

    Falls back to the global known_frequencies whitelist only when nothing is
    deployed at this station yet. The global list is the wrong default on its
    own: it is Elkhorn's 151 MHz fish tags, which every provisioned station used
    to inherit — including stations listening 13 MHz away.
    """
    ...

def render_install_script(station: dict, server_url: str, config_text: str, install_url: str, code_url: str) -> str:
    """Render the one-line installer bash for a station."""
    ...

@app.get('/api/v1/admin/stations/{station_id}/config')
async def get_station_config(station_id: str, request: Request, _=Depends(verify_admin)):
    """Server-rendered config.ini snippet for a station — single source of
    truth for the Setup wizard's copy block and QR code."""
    ...

@app.get('/install/{station_id}.sh')
async def get_install_script(station_id: str, request: Request, key: str=Query(None)):
    """One-line Pi installer for a station. Authed by ?key=<api_key> (the same
    key the returned config already contains), so no admin session is needed on
    the Pi. Returns a bash script for `curl … | sudo bash`."""
    ...

def _ships_to_station(rel: Path) -> bool:
    """True if this repo-relative path belongs in a station's code tarball."""
    ...

@app.get('/install/{station_id}.tar.gz')
async def get_install_code(station_id: str, key: str=Query(None)):
    """The station code itself, as a tarball.

    The installer cannot `git clone`: the station repo is private and a fresh Pi
    has no GitHub credentials (it fails with "could not read Username"). Central
    already holds the code — it is the same OTA tree the update path serves —
    so it hands it over directly. One source of truth, no tokens on the Pi.

    Authed by the station's own api_key, like the install script.
    """
    ...

@app.get('/api/v1/admin/stations/{station_id}/health')
async def get_station_health_history(station_id: str, hours: int=24, _=Depends(verify_admin)):
    """Health time series derived from stored heartbeat events — feeds the
    station-detail sparklines. No extra storage; reads the events table."""
    ...

@app.get('/api/v1/admin/activity')
async def get_activity(hours: int=24, bins: int=48, station_id: Optional[str]=None, _=Depends(verify_admin)):
    """Binned activity for the dashboard charts: per station whether it
    checked in, listened and heard in each bin, and per tag where and when it
    was heard. Read from the events table; see Database.get_activity."""
    ...

def _pending_run_info(database: Database, station_id: str) -> Optional[Dict]:
    """UI state for an in-flight run_diagnostics command:
    queued (not yet fetched) or running (fetched < 15 min ago)."""
    ...

@app.get('/api/v1/admin/stations/{station_id}/diagnostics')
async def get_station_diagnostics(station_id: str, limit: int=20, full: bool=False, _=Depends(verify_admin)):
    """Diagnostics history (newest first) + any pending run."""
    ...

@app.get('/api/v1/admin/stations/{station_id}/diagnostics/latest')
async def get_station_diagnostics_latest(station_id: str, _=Depends(verify_admin)):
    """Full latest bundle + analysis + pending-run state."""
    ...

@app.post('/api/v1/admin/stations/{station_id}/diagnostics/run')
async def run_station_diagnostics(station_id: str, request: Request, _=Depends(verify_admin)):
    """Queue a run_diagnostics command (station picks it up at its next
    check-in and runs at its next duty-cycle sleep boundary)."""
    ...

@app.get('/api/v1/admin/diagnostics/latest')
async def get_fleet_diagnostics(_=Depends(verify_admin)):
    """Latest bundle per station — feeds the fleet health-comparison table."""
    ...

@app.get('/api/v1/admin/stats')
async def get_stats(_=Depends(verify_admin)):
    """Get overall system statistics"""
    ...

def _events_summary(database: Database, station_id: Optional[str], hours: int) -> List[Dict]:
    """Event counts by station + type for the last N hours (shared by the
    admin API endpoint and the /more page's server-rendered first paint)."""
    ...

@app.get('/api/v1/admin/events/summary')
async def get_events_summary(station_id: Optional[str]=None, hours: int=24, _=Depends(verify_admin)):
    """Get event summary by type for diagnostics — shows if detections vs heartbeats are arriving"""
    ...

@app.get('/api/v1/admin/frequencies')
async def get_known_frequencies(include_retired: bool=False, _=Depends(verify_admin)):
    """Deployments: what is out, where (site, None = everywhere) and since
    when. Retired rows only with include_retired."""
    ...

def _site_label(key: str) -> str:
    ...

def _station_site(station_row: Dict) -> str:
    ...

def _site_options(database) -> List[Dict]:
    """The sites the fleet has stations at, for pickers."""
    ...

@app.post('/api/v1/admin/frequencies')
async def add_known_frequency(req: FrequencyAdd, _=Depends(verify_admin)):
    """Add a known tag frequency to the whitelist and push to all stations.

    If ``pulse_width_ms`` is provided it's persisted with the frequency so the
    Pi can build a correctly-sized matched-filter template (Phase 1 fix).
    """
    ...

@app.post('/api/v1/admin/frequencies/{frequency_khz}/retire')
async def retire_known_frequency(frequency_khz: int, req: DeploymentRetire, _=Depends(verify_admin)):
    """Mark a deployment retrieved. The row stays as history so detections
    from while it was out still resolve to it; the stations at that site stop
    listening for it on their next check-in."""
    ...

@app.delete('/api/v1/admin/frequencies/{frequency_khz}')
async def remove_known_frequency(frequency_khz: int, site: Optional[str]='any', _=Depends(verify_admin)):
    """Hard-delete a deployment (a typo, not a retrieval) and push."""
    ...

@app.post('/api/v1/admin/frequencies/push')
async def push_frequencies(_=Depends(verify_admin)):
    """Manually push current frequency whitelist to all active stations"""
    ...

def _push_frequencies_to_stations(database):
    """Queue set_frequencies to every active station, each with the tags out
    at ITS site (plus the all-sites ones). A station at Ano Nuevo has no
    business listening for Elkhorn's tags, and the same frequency can be a
    different animal at each place. Legacy payload shape (no pulse widths);
    the per-station deploy path (set_tag_config) carries richer data."""
    ...

@app.get('/api/v1/admin/species')
async def list_species(_=Depends(verify_admin)):
    """The species catalog, for the registry's per-tag picker."""
    ...

class TagSpecies(BaseModel):
    """Assign the animal a registered tag is riding on.

    An empty/absent species clears the assignment, which drops the tag back to
    whatever its frequency band implies — not to nothing.
    """
    species: Optional[str] = None

@app.put('/api/v1/admin/tags/registry/{unique_key:path}/species')
async def set_tag_species(unique_key: str, req: TagSpecies, _=Depends(verify_admin)):
    """Set (or clear) a registry tag's species."""
    ...

@app.get('/api/v1/admin/tags/registry')
async def get_tag_registry(include_custom: bool=True, _=Depends(verify_admin)):
    """Return the full tag registry (ATS imports + custom entries)."""
    ...

@app.post('/api/v1/admin/tags/registry')
async def upsert_tag(req: TagUpsert, _=Depends(verify_admin)):
    """Insert or update a tag in the registry. Idempotent on unique_key."""
    ...

@app.delete('/api/v1/admin/tags/registry/{unique_key:path}')
async def delete_tag(unique_key: str, _=Depends(verify_admin)):
    """Remove a tag from the registry (cascades to clear deployment state)."""
    ...

@app.get('/api/v1/admin/stations/{station_id}/deployment')
async def get_station_deployment(station_id: str, _=Depends(verify_admin)):
    """Return the station's currently-deployed tag set + computed band plan."""
    ...

@app.put('/api/v1/admin/stations/{station_id}/deployment')
async def set_station_deployment(station_id: str, req: StationDeployment, _=Depends(verify_admin)):
    """Replace the station's deployed-tag set. Does not push to the Pi —
    use POST /commit for that."""
    ...

@app.post('/api/v1/admin/stations/{station_id}/deployment/preview')
async def preview_station_deployment(station_id: str, _=Depends(verify_admin)):
    """Compute + return the config delta for the station's deployed set
    WITHOUT queueing a command. Used by the dashboard's diff preview."""
    ...

@app.post('/api/v1/admin/stations/{station_id}/deployment/commit')
async def commit_station_deployment(station_id: str, req: DeploymentCommit, _=Depends(verify_admin)):
    """Queue a set_tag_config command for the station.

    UX gate: caller must send ``confirm: "DEPLOY"`` in the body (matches the
    typed-DEPLOY gate pattern in the UI).
    """
    ...

def _compute_band_plan(tags: list, sample_rate: float=2048000.0, band_margin_hz: float=100000.0, usable_fraction: float=0.9) -> dict:
    """Shared SDR-tuning computation for a station's deployed tag set.

    Mirrors RelayStation-main/tags/deployment.py::compute_config_from_deployment
    but operates on DB-row dicts (frequency_khz + pulse_width_ms + model, etc.)
    so the server can compute without any file-system dependency.
    """
    ...

def _build_set_tag_config_payload(tags: list, plan: dict) -> dict:
    """Payload for the set_tag_config command. Keep this compact — it
    travels over NB-IoT on every deploy."""
    ...

def _iter_ota_files(base_dir: Path):
    """Every file the update manifest ships from base_dir, enumerated
    RECURSIVELY so a subpackage added later ships with its importer instead of
    being silently omitted (which would strand the fix and mask it as
    "current")."""
    ...

def _fingerprint_of(hashes: Dict[str, str]) -> str:
    """md5 over the sorted 'path:md5' lines, first 8 hex. The station's
    heartbeat 'fw' is this over its own files."""
    ...

def _in_legacy_fw_scope(rel: str) -> bool:
    """What a station on pre-2026-09-23 code still hashes: core/*.py,
    comms/*.py, scripts/*.py, scripts/*.sh (top level only) and
    relay_station.py. Remove once no station reports a legacy value."""
    ...

def _verify_ota_station(x_api_key: Optional[str], x_station_id: Optional[str], what: str) -> None:
    """Authenticate a station on the update endpoints (transitional)."""
    ...

@app.get('/api/v1/updates/manifest')
async def get_update_manifest(x_api_key: Optional[str]=Header(None), x_station_id: Optional[str]=Header(None)):
    """
    Return list of updatable files with MD5 hashes.
    Stations compare this against their local files to determine what changed.
    Serves from OTA_DIR (deploy repo mount) or /app fallback.
    """
    ...

def _note_ota_oversize(oversize: List[str], files: List[Dict]) -> None:
    """Say it loudly when the OTA tree holds a file /updates/file will refuse.

    The manifest still lists such a file (dropping it would ship the rest of a
    multi-file change without it), so every station that checks in downloads
    the other files, gets 413 on this one, and applies NOTHING: one oversized
    file blocks the whole update for the whole fleet. That is how five
    detector fixes once sat undeliverable while every dashboard was green.
    Now it is an ERROR in the log and a card in the alert feed, cleared by the
    first manifest that is clean again. Never raises: this runs inside the
    manifest request.
    """
    ...

@app.get('/api/v1/updates/file')
async def get_update_file(path: str, x_api_key: Optional[str]=Header(None), x_station_id: Optional[str]=Header(None)):
    """
    Serve a single file's content (base64 encoded).
    Designed for NB-IoT: small individual file downloads.
    """
    ...

@app.post('/api/v1/test/sessions')
async def create_test_session(req: TestSessionCreate, _=Depends(verify_admin)):
    """Create a new test session"""
    ...

@app.get('/api/v1/test/sessions')
async def list_test_sessions(station_id: Optional[str]=None, _=Depends(verify_admin)):
    """List all test sessions"""
    ...

@app.get('/api/v1/test/sessions/{session_id}')
async def get_test_session(session_id: str, _=Depends(verify_admin)):
    """Get a specific test session"""
    ...

@app.post('/api/v1/test/sessions/{session_id}/end')
async def end_test_session(session_id: str, _=Depends(verify_admin)):
    """End a test session"""
    ...

@app.delete('/api/v1/test/sessions/{session_id}')
async def delete_test_session_endpoint(session_id: str, _=Depends(verify_admin)):
    """Delete a test session and all its measurements and waypoints"""
    ...

@app.get('/api/v1/test/sessions/{session_id}/summary')
async def get_test_session_summary(session_id: str, _=Depends(verify_admin)):
    """Get summary statistics for a test session"""
    ...

@app.post('/api/v1/test/measurements')
async def store_test_measurements(req: TestMeasurementBatch, _=Depends(verify_admin)):
    """Store a batch of test measurements"""
    ...

@app.get('/api/v1/test/sessions/{session_id}/measurements')
async def get_test_measurements(session_id: str, limit: int=1000, _=Depends(verify_admin)):
    """Get measurements for a test session"""
    ...

@app.get('/api/v1/test/sessions/{session_id}/live')
async def get_live_measurements(session_id: str, seconds: int=5, _=Depends(verify_admin)):
    """Get the most recent measurements (for live display)"""
    ...

@app.post('/api/v1/test/sessions/{session_id}/waypoints')
async def add_range_waypoint(session_id: str, req: RangeWaypointCreate, _=Depends(verify_admin)):
    """Add a range test waypoint"""
    ...

@app.get('/api/v1/test/sessions/{session_id}/waypoints')
async def get_range_waypoints(session_id: str, _=Depends(verify_admin)):
    """Get all waypoints for a test session"""
    ...

@app.get('/api/v1/test/sessions/{session_id}/export')
async def export_test_session(session_id: str, _=Depends(verify_admin)):
    """Export complete test session data as JSON"""
    ...

@app.get('/api/v1/test/active')
async def get_active_test_sessions(_=Depends(verify_admin)):
    """Get all active field-test sessions across all stations.

    Range walks are excluded: the classic dashboard's Testing tab treats
    sessions[0] here as "the active test session" and offers to end it —
    which would kill a range walk in progress and attach station
    measurements to it."""
    ...
LIVE_WINDOW_BATCHES = 3
LIVE_WINDOW_MIN_S = 30
LIVE_WINDOW_MAX_S = 180
DEFAULT_BATCH_INTERVAL_S = 60
DEFAULT_REDUCED_BATCH_INTERVAL_S = 1800

def _station_batch_interval_s(station: Optional[Dict]) -> float:
    """How often this station ships a batch of events, in seconds."""
    ...

def _live_window_seconds(station: Optional[Dict]) -> int:
    """The live-signal window that matches this station's uplink cadence."""
    ...

@app.get('/api/v1/test/live-signal')
async def get_live_signal_by_frequency(station_id: str, frequency_khz: int, seconds: Optional[int]=None, _=Depends(verify_admin)):
    """Get live signal data for a specific station+frequency from the events table.
    Used by solo range test to show real-time signal for a target tag.

    'seconds' defaults to the station's own cadence (see _live_window_seconds);
    callers that pass it explicitly still get exactly that window. The window
    actually used comes back as stats.window_seconds so the page can say which
    one it is drawing."""
    ...

class RangeSessionCreate(BaseModel):
    """Start a range-calibration walk"""
    station_id: str
    frequency_khz: int
    name: Optional[str] = None
    notes: Optional[str] = None
    station_latitude: Optional[float] = None
    station_longitude: Optional[float] = None

class RangeTrackBatch(BaseModel):
    """Batch of phone GPS points: [{t, lat, lon, acc?}, ...].

    client_now is the phone's idea of "now" at send time; the server uses it
    to shift every point onto server time, since the detection events the
    track is matched against carry station/server-side epoch timestamps."""
    points: List[Dict]
    client_now: Optional[float] = None

class StationLocationSet(BaseModel):
    """Pin a station's coordinates (needed before any range math)."""
    latitude: float
    longitude: float

def _registry_pulse_rate(database, frequency_khz: int) -> Optional[float]:
    """Pulse rate (ppm) for the tag nearest this frequency, within the same
    ±2 kHz window the detector's whitelist uses. Enables absolute detection
    rate (heard/expected) in the raster instead of just detections/minute."""
    ...

@app.post('/api/v1/range/sessions')
async def create_range_session(req: RangeSessionCreate, _=Depends(verify_admin)):
    """Start a range-calibration session for one station + one tag frequency."""
    ...

@app.get('/api/v1/range/sessions')
async def list_range_sessions(station_id: Optional[str]=None, active_only: bool=False, _=Depends(verify_admin)):
    """List range-calibration sessions (newest first, with track counts)."""
    ...

@app.post('/api/v1/range/sessions/{session_id}/track')
async def add_range_track(session_id: str, req: RangeTrackBatch, _=Depends(verify_admin)):
    """Store a batch of phone GPS points for an active session.

    Returns the last point's distance/bearing to the station so the phone
    can show them without doing its own geodesy.
    """
    ...

def _range_warnings(clock_skew_s: Optional[float]) -> List[str]:
    """Conditions that make a walk silently produce nothing.

    Detections are placed on the ground by matching STATION-side timestamps
    to phone GPS fixes within range_calc.MAX_GAP_S. A station whose clock is
    off by more than that drops every detection out of the correlation while
    the Tags page still shows the tag being heard, so the walk reads as "no
    range at all" instead of "wrong clock". Nothing checked this before.
    """
    ...

def _compute_range_results(database: Database, session: Dict, cell_m: float=25.0) -> Dict:
    """The full analysis payload for one range session — shared by the
    results endpoint and the export endpoint so the two can never drift."""
    ...

@app.get('/api/v1/range/sessions/{session_id}/results')
async def get_range_results(session_id: str, cell_m: float=25.0, _=Depends(verify_admin)):
    """Everything the range page draws: the GPS track, each detection placed
    on the ground with its distance and RSSI, the coverage raster, the
    path-loss fit, and headline stats. Recomputed from stored track + events
    on every call, so it works identically live and long after the walk."""
    ...

def _range_csv(rows: List[Dict], fields: List[str]) -> str:
    ...

@app.get('/api/v1/range/sessions/{session_id}/export')
async def export_range_session(session_id: str, format: str='json', table: str='samples', _=Depends(verify_admin)):
    """Full walk download. format=json (default): the complete analysis
    payload. format=csv: flat, model-training-ready tables — table=samples
    is one row per positioned detection (unthinned), table=track one row per
    GPS fix; the fixes with no matching detection are the negative examples.
    Both load straight into pandas. Export walks you want as a training
    corpus while fresh: the retention sweep prunes events after ~30 days,
    and the correlation cannot outlive the events it joins against."""
    ...

@app.post('/api/v1/range/sessions/{session_id}/end')
async def end_range_session(session_id: str, _=Depends(verify_admin)):
    """End a range-calibration session (results stay queryable forever)."""
    ...

@app.post('/api/v1/admin/stations/{station_id}/location')
async def set_station_location(station_id: str, req: StationLocationSet, _=Depends(verify_admin)):
    """Set a station's coordinates in place (register_station would also
    rewrite the api_key). Lets the field workflow pin the station by
    standing next to it with the phone."""
    ...
LOGIN_MAX_ATTEMPTS = 10
LOGIN_WINDOW_S = 300

def _login_throttled(ip: str) -> bool:
    """True if this IP has burned its failed-login budget. Prunes as it goes."""
    ...

def _login_failed(ip: str) -> None:
    ...

@app.post('/api/v1/auth/verify')
async def verify_admin_key(request: Request, response: Response):
    """Verify an admin key and establish the HttpOnly session cookie
    (used by dashboard login; pages are gated server-side on the cookie)."""
    ...

@app.post('/api/v1/auth/logout')
async def logout(response: Response):
    """Clear the session cookie."""
    ...

def _offline_bases() -> tuple:
    """(full-mode minutes, data-saving minutes) from the alert settings.

    The same values the alert engine reads, so the dashboard badge and the
    phone alert never disagree. Each is only a base: every caller passes the
    station's reported cadence too, and mode_offline_threshold_min floors the
    result by it."""
    ...

def ota_fingerprints() -> Tuple[Optional[str], Optional[str]]:
    """(full, legacy) content fingerprints of the OTA tree. Full is md5 over
    the sorted 'path:filehash' lines of exactly the files the update manifest
    serves; stations compute the identical value over their local files and
    report it in heartbeats ('fw'). Matching means 'running exactly what the
    server would deploy', regardless of git state (safe_update applies files
    without moving HEAD). Legacy is the same recipe over the narrower subset a
    station on pre-2026-09-23 code still reports. Cached 60s."""
    ...

def ota_fingerprint() -> Optional[str]:
    """The full-scope fingerprint of the OTA tree (see ota_fingerprints)."""
    ...

def fw_update_state(fw: Optional[str], full: Optional[str], legacy: Optional[str]) -> str:
    """'current', 'partial', 'behind' or 'unknown' for a station's 'fw'.

    'partial' is a station still on the old fingerprint code whose value
    matches the server over the part that code hashes. It is NOT current:
    health/, monitoring/, web/, scripts/ subfolders and spectrogram_service.py
    are unverified, which is exactly how a missing watchdog fix once read as
    current. Once the OTA tree carries the new fingerprint code, a station
    matching it here is running that code and reports the full value, so in
    practice 'partial' only appears while Central is ahead of the tree."""
    ...
PWR_IDLE_W = 5.9
PWR_FULL_W = 9.4

def estimate_power_w(cpu_percent) -> Optional[float]:
    """Estimated watts for a station at the given CPU load, or None."""
    ...

def _duration_word(seconds) -> Optional[str]:
    """'12 h', '30 min', '2 d' -- for a cadence the station reported."""
    ...

def modem_label(station: Dict) -> Optional[str]:
    """One line for what the station's modem last reported, or None if it
    never has. Built from stored REPORTS (heartbeat q/cr or the watchdog's
    health line), never from the typed install profile: 'cellular gateway'
    is what somebody called it, 'cellular searching, no signal' is what the
    modem said."""
    ...

def _annotate_station_status(stations: List[Dict], now: Optional[datetime]=None) -> List[Dict]:
    """Attach status + last_seen_ago to station rows in place.

    Uses UTC to match SQLite CURRENT_TIMESTAMP; offline threshold is the
    configurable offline_threshold_min (see mode_offline_threshold_min)."""
    ...

def _compute_banner(stations: List[Dict], tags: List[Dict], unacked_count: int) -> Dict:
    """Worst-of status banner for the home page (mirrored in rs-home.js):
    any offline station → red; any degraded or never-seen station, unacked
    alert or unknown tag → amber; otherwise green."""
    ...

@app.get('/', response_class=HTMLResponse)
async def home(request: Request, relay_session: Optional[str]=Cookie(None)):
    """RelayStation Central home page.

    Without a valid session cookie the page renders as a login-only shell —
    no station/tag data is embedded server-side before authentication."""
    ...

@app.get('/classic', response_class=HTMLResponse)
async def classic_dashboard(request: Request, relay_session: Optional[str]=Cookie(None)):
    """Serve the legacy multi-station dashboard (kept during the redesign).

    Without a valid session cookie the page renders as a login-only shell —
    no station/tag data is embedded server-side before authentication."""
    ...

@app.get('/station/{station_id}', response_class=HTMLResponse)
async def station_detail(request: Request, station_id: str, relay_session: Optional[str]=Cookie(None)):
    """Station detail page (session-gated; login happens on /).

    The page shell is server-rendered; detections, logs, health history and
    diagnostics are fetched by rs-station.js via the admin API."""
    ...

def _tags_page_rows(tags: List[Dict], now: datetime) -> List[Dict]:
    """Annotate tag rows for template rendering (MHz + human ago strings)."""
    ...

@app.get('/stations', response_class=HTMLResponse)
async def stations_page(request: Request, relay_session: Optional[str]=Cookie(None)):
    """Fleet list page: map + Tailscale-style table + demoted rankings."""
    ...

@app.get('/review', response_class=HTMLResponse)
async def review_page(request: Request, relay_session: Optional[str]=Cookie(None)):
    """Fleet-wide candidate review: label saved detection thumbnails tag/noise."""
    ...

@app.get('/api/v1/admin/review/count')
async def get_review_count(_=Depends(verify_admin)):
    """How many captures still owe the reviewer a verdict.

    Deliberately its own tiny endpoint: the nav badge polls this on every page
    and must not pull candidate images to render a number.
    """
    ...

@app.get('/api/v1/admin/candidates')
async def admin_list_candidates(station_id: Optional[str]=None, only_unlabeled: bool=True, limit: int=120, freq_khz: Optional[int]=None, _=Depends(verify_admin)):
    """Candidate thumbnails for the review gallery (image included)."""
    ...

@app.post('/api/v1/admin/candidates/{cand_id}/label')
async def admin_label_candidate(cand_id: int, body: CandidateLabel, _=Depends(verify_admin)):
    ...

@app.get('/api/v1/admin/candidates/export')
async def admin_export_candidates(_=Depends(verify_admin)):
    """Labeled candidates (with images) for FP-discriminator training."""
    ...

@app.get('/tags', response_class=HTMLResponse)
async def tags_page(request: Request, relay_session: Optional[str]=Cookie(None)):
    """One-stop tag data page: unknown-tag triage, detections, map, registry."""
    ...

class ViewLinkCreate(BaseModel):
    label: Optional[str] = None

def _public_state(station: Dict) -> str:
    ...

def _live_payload(database, now: Optional[datetime]=None) -> Dict:
    """Everything /live shows, and nothing it does not. Built from the same
    status annotation the admin pages use, so the two can never disagree about
    whether a station is listening."""
    ...

def _live_headline(listening: int, active: int, heard: int) -> str:
    ...

@app.get('/api/v1/admin/view-links')
async def list_view_links(request: Request, _=Depends(verify_admin)):
    ...

@app.post('/api/v1/admin/view-links')
async def create_view_link(req: ViewLinkCreate, request: Request, _=Depends(verify_admin)):
    ...

@app.delete('/api/v1/admin/view-links/{link_id}')
async def revoke_view_link(link_id: int, _=Depends(verify_admin)):
    ...

@app.get('/api/v1/live/{token}')
async def live_feed(token: str):
    ...

@app.get('/live/{token}', response_class=HTMLResponse)
async def live_page(request: Request, token: str):
    ...

@app.get('/setup')
async def setup_page():
    """The Setup hub was dissolved into its natural homes — add-a-station →
    Stations, season whitelist → Tags, phone alerts → More. Kept as a redirect
    so existing QR codes / bookmarks pointing at /setup still resolve."""
    ...

def _fleet_health_rows(stations: List[Dict], bundles: List[Dict], now: datetime) -> List[Dict]:
    """Join station list with latest diagnostics bundles for the /more
    comparison table. Sorted worst-first: critical findings, then warnings,
    then stale bundles; stations with no bundle at the end."""
    ...

@app.get('/more', response_class=HTMLResponse)
async def more_page(request: Request, relay_session: Optional[str]=Cookie(None)):
    """Fleet expert view: health comparison, recent activity, logs, and
    links out (Classic view lives here now)."""
    ...

@app.get('/range', response_class=HTMLResponse)
async def range_page(request: Request, relay_session: Optional[str]=Cookie(None)):
    """Phone-first range calibration: walk a test tag away from a station,
    watch live signal, and map how far detection actually reaches."""
    ...

def _format_timedelta(seconds: float) -> str:
    """Format seconds into human-readable string"""
    ...
