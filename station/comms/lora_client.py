"""The node side of a LoRa link: a drop-in for CentralClient on a Pi whose
only way out is a LoRa HAT.

relay_station.py talks to one object for everything it reports (detections,
heartbeats, locks, logs) and for what the watchdog asks ("when did anything
last get through?"). On a cellular station that object is
comms.central_client.CentralClient. On a LoRa node it is this class, with the
same public surface, the same persistent OfflineQueue underneath, and a
radio where the HTTP transport was. The station code does not know which
one it has.

What rides the air, and why it is shaped like this:

* One wake per `batch_interval_s` (or sooner when a tag locks). Per wake:
  the newest heartbeat as ONE frame, every detection heard since the last
  wake packed 22 to a DETECTIONS frame, each lock as its own frame, and at
  most one ERROR-or-worse log line. Older heartbeats are dropped unsent:
  history heartbeats are worth nothing over a link this narrow.
* Every frame waits `ack_wait_s` for the gateway's ACK. ACKed rows leave
  the queue. A missed ACK keeps the frame, with ITS SEQ, for the next wake:
  the gateway may have heard it and only the ACK was lost, and Central's
  dedup id is boot+seq, so resending under the same seq cannot double-count
  while resending under a new one would. After MAX_ATTEMPTS misses the rows
  go back to the pool and get a new seq later (the gateway was plainly not
  hearing us, so a duplicate is unlikely).
* One missed ACK ends the wake. The gateway is down or out of range;
  keying the PA three more times proves nothing and costs battery and SDR
  blanking.
* Times travel as ages (comms/lora_frames.py). A node has no NTP; it knows
  how long ago it heard the pulse, and the gateway knows the time. Rows
  older than the codec's 18 h cap are dropped with a WARNING.
* The ACK carries the RSSI the gateway heard us at, and PowerPolicy steps
  the PA down while there is margin. The module sleeps between wakes.

No commands come back over this link (v1). A node is configured on the
bench; `fetch_commands` returns nothing and the polling entry points are
no-ops so relay_station's wiring is unchanged.
"""
from __future__ import annotations
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
from . import lora_frames as F
from .lora_radio import PowerPolicy, load_lora_config, open_radio, E22_POWER
from .offline_queue import OfflineQueue, DEFAULT_LOCKED_REPORT_INTERVAL_SEC
MAX_ATTEMPTS = 5
MAX_PENDING_FRAMES = 4
LOGS_PER_WAKE = 1
LOG_MAX_CHARS = 96
BACKOFF_MAX_S = 600.0

@dataclass
class PendingFrame:
    """A frame that has a seq and rows but not yet an ACK."""
    seq: int
    ftype: int
    rows: List[Dict]
    build: Callable[[float], bytes]
    attempts: int = 0

@dataclass
class LinkStats:
    frames_sent: int = 0
    acked: int = 0
    missed: int = 0
    released: int = 0
    dropped_old: int = 0
    dropped_heartbeats: int = 0
    last_ack_rssi: Optional[int] = None
    last_ack_at: float = 0.0
    radio_errors: int = 0

class LoRaClient:
    """CentralClient's public surface, over a LoRa radio."""
    has_modem = False
    on_restart = None
    on_calibrate = None
    on_update = None
    on_set_config = None
    on_set_frequencies = None
    on_run_check = None

    def __init__(self, config, lora_cfg: Optional[Dict[str, str]]=None, radio=None, state_dir: Optional[str]=None, clock: Callable[[], float]=time.time):
        ...

    def start(self):
        ...

    def stop(self):
        ...

    def start_command_polling(self, interval_seconds: int=60):
        ...

    def stop_command_polling(self):
        ...

    def fetch_commands(self) -> List[Dict]:
        ...

    def report_detection(self, frequency_mhz: float, signal_db: float, confidence: float, is_locked: bool=False, is_unlisted: bool=False):
        ...

    def report_candidate_confirm(self, frequency_mhz: float, reason: str, extra_meta: Optional[Dict]=None):
        ...

    def report_heartbeat(self, cpu_percent: float, memory_percent: float, temperature_c: Optional[float], active_tags: int, uptime_seconds: int, extras: Optional[Dict]=None):
        ...

    def report_log(self, level: str, message: str):
        ...

    def report_tag_locked(self, frequency_mhz: float, pulse_count: int, confidence: float):
        ...

    def report_tag_retrieved(self, frequency_mhz: float):
        ...

    def send_now(self):
        ...

    def seconds_since_uplink(self) -> float:
        """Seconds since the gateway last ACKed a frame."""
        ...

    def get_stats(self) -> Dict:
        ...

    def _backoff(self) -> float:
        ...

    def _sender_loop(self):
        ...

    def _drop_radio(self) -> None:
        ...

    def _ensure_radio(self) -> bool:
        ...

    def _send_wake(self) -> int:
        """One wake: retry what is unacked, then plan and send new frames.
        Returns frames ACKed this wake."""
        ...

    def _plan(self) -> List[PendingFrame]:
        """Turn queued rows into frames. Rows already held by a pending
        frame are skipped (pop_batch has no exclusion, so the batch is
        widened by the held count and filtered here)."""
        ...

    @staticmethod
    def _record(payload: Dict, now: float):
        ...

    def _heartbeat_frame(self, row: Dict) -> PendingFrame:
        ...

    def _next_seq(self) -> int:
        ...

    def _transmit(self, pf: PendingFrame) -> bool:
        ...

    def _await_ack(self, seq: int) -> Optional[Dict]:
        ...

    def _apply_power(self, dbm: Optional[int]) -> None:
        ...

    def _mark_uplink(self):
        ...

    def _next_boot(self) -> int:
        """8-bit boot counter, persisted: a node has no RTC, so this is what
        keeps seq 0 after a reboot from colliding with seq 0 before it."""
        ...

def _bool(v) -> bool:
    ...
