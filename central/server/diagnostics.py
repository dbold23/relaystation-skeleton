"""
Diagnostics analysis for RelayStation Central.

Stations run a maintenance pass on command (RF survey, gain sweep, power,
pipeline health) and upload an 'm' event bundle. This module turns a bundle
into plain-English, actionable recommendations by comparing it against the
station's previous bundle. Pure rule-based — no ML, no dependencies.

Each finding: {"rule": str, "severity": "info"|"warning"|"critical",
               "message": str}
The empty list means "all checks passed".
"""
import json
import logging
from typing import Dict, List, Optional

def decode_throttled(raw) -> Dict:
    """'0x50005' -> {'raw': '0x50005', 'flags': [...decoded names...]}"""
    ...

def analyze(data: Dict, previous: Optional[Dict]=None) -> List[Dict]:
    """Analyze one diagnostics bundle's 'data' section against the previous
    bundle's (may be None). Returns a list of findings, worst first."""
    ...

def ingest_bundle(db, alert_engine, station_id: str, event: Dict):
    """Store one 'm' event: analyze against the station's previous bundle,
    persist payload + analysis, and raise an alert for warning+ findings.
    Called from the events endpoint after store_events."""
    ...
