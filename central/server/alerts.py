"""
Alert engine for RelayStation Central.

Turns station events into person-facing alerts (dashboard feed + ntfy phone
push). Rule-based, stdlib-only, synchronous-cheap: on_event_batch() does
dict checks and at most a couple of indexed SQL lookups; the ntfy HTTP POST
runs on a daemon thread so ingest never blocks on the network.

Two tiers, and the tier decides whether a phone rings.

TIER 1, pushed. A human must act, and no amount of software will resolve it:
    tag_confirmed   — a lock at a frequency a human deployed or confirmed.
                      The scientific headline, and the reason the fleet exists.
    station_offline — no contact for `offline_threshold_min` minutes.
    station_degraded— reporting but detecting nothing. The silent-failure shape
                      this whole system keeps producing.

TIER 2, dashboard only. Worth seeing when you look; never worth a buzz:
    station_error   — station forwarded an ERROR/CRITICAL log.
    diagnostics     — a maintenance bundle produced a warning.
    command_unacked — a queued command the station never picked up.
    tag_rate_change - a locked tag's pulse spacing moved and held (doubled
                      rate is the usual mortality signal). Tier 2 until it has
                      been seen to fire on a real mortality-mode tag.
    ota_undeliverable — the OTA tree holds a file over the per-file limit, so
                      every station's update fails whole. Raised by the
                      manifest endpoint, cleared by the first clean manifest.
    tag_reappeared  — a known tag seen again after a real silence. Kept because
                      it is genuinely interesting on the page, demoted because
                      it is not worth a phone: it announced 1025 h and 4695 h
                      of "silence" during a backlog drain that was really one
                      outage, which is fixed separately by measuring the gap
                      from the event's own timestamp.

Anything not named in ALERT_TIERS defaults to tier 2, so a new kind can never
accidentally reach a phone.

Deleted outright (2026-09-12), because none of them was a decision anyone made
from a card:
    station_online, station_recovered — replaced by resolve_alerts(). A station
        coming back is the absence of news. The alert it ends clears itself.
    unlisted_tag    — an off-whitelist frequency is the definition of a
        judgement call. It belongs in the review queue, which already receives
        those captures, not on a phone at 3 am.
    interference    — a human had already ruled the frequency noise.
"""
import logging
from . import tag_behaviour
import threading
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional
TIER_PUSH = 1

class AlertEngine:
    """Evaluates alert rules and publishes to the feed + ntfy."""

    def __init__(self, db):
        ...

    def settings(self) -> Dict[str, str]:
        ...

    def _enabled(self, kind: str, settings: Dict[str, str]) -> bool:
        ...

    def on_event_batch(self, station_id: str, events: List[Dict], prior_tag_seen: Dict[int, str]):
        """Called after store_events() commits.

        prior_tag_seen: freq_khz -> last_seen string captured BEFORE the
        batch was stored (see Database.get_tag_last_seen_map).
        """
        ...

    def _check_pulse_rate(self, station_id: str, raw_khz: int, settings: Dict[str, str]):
        """A sustained change in a locked tag's pulse spacing. Most VHF
        mortality sensors double the rate, and the station's validator hides
        exactly that (Relay-Cellular tests/test_tag_window.py), so this reads
        the arrivals as heard. Dashboard only until it has been seen to work
        on a real mortality-mode tag; see server/tag_behaviour.py."""
        ...

    def check_periodic(self):
        """Offline/online detection; run every ~60 s from the lifespan task."""
        ...

    def raise_alert(self, kind: str, severity: str, station_id: Optional[str], message: str, dedup_key: str=None):
        """Public entry for other modules (e.g. diagnostics analysis)."""
        ...

    def resolve_alert(self, dedup_key: str) -> int:
        """Public entry: the condition behind this dedup key has ended."""
        ...

    def send_test(self) -> Dict:
        """Manual test push (Setup page 'Send me a test alert')."""
        ...

    def _is_confirmed_tag(self, station_id: str, freq_khz: int) -> bool:
        """Has a human put a real tag at this frequency, at this station?

        Only a lock HERE is worth a phone. A lock on a frequency nobody has
        deployed is a candidate for the review queue, not an alert.
        """
        ...

    def _is_muted(self, station_id: str, freq_khz: int) -> bool:
        """Has a human labelled this frequency noise on the review page?

        Guarded like _is_interferer so an alert can never crash ingest on an
        older schema.
        """
        ...

    def _is_confirmed_noise(self, station_id: str, freq_khz: int) -> bool:
        """Either kind of human verdict: the station's interferer list, or a
        'noise' label from the review queue."""
        ...

    def _is_interferer(self, station_id: str, freq_khz: int) -> bool:
        """Guarded lookup so an alert never crashes ingest if the DB helper is
        unavailable (older schema)."""
        ...

    def _resolve(self, dedup_key: str):
        """The condition this alert described has ended: clear the card.

        Guarded, because a feed that cannot clear itself is a nuisance but a
        periodic check that raises is a broken alert engine.
        """
        ...

    def _raise(self, kind: str, severity: str, station_id: Optional[str], message: str, dedup_key: str, settings: Dict[str, str], dedup_hours: float=None, dedup_any_ack: bool=False):
        ...

    def _push_ntfy(self, settings: Dict[str, str], title: str, message: str, severity: str, kind: str):
        ...

    @staticmethod
    def _hours_since(ts) -> Optional[float]:
        """Hours between a timestamp and now; None if unknown."""
        ...

    @staticmethod
    def _coerce_dt(ts):
        """A stored TEXT timestamp, a datetime, or epoch seconds -> datetime."""
        ...

    @staticmethod
    def _hours_between(start, end) -> Optional[float]:
        """Hours from start to end; None if either is unreadable."""
        ...

    @staticmethod
    def _event_time(event: Dict):
        """The station's own timestamp for an event ('t', epoch seconds), or
        now when it carries none. An event is news as of when it HAPPENED."""
        ...
