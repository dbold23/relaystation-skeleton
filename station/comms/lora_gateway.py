"""The gateway half of a LoRa link: frames in over the radio, events out to
Central over whatever backhaul the gateway Pi has.

A node never talks to Central. It talks to this. The gateway keeps a small
table from LoRa node id to the Central station the node is registered as
(station id + that station's own API key), turns each frame into the event
dict Central already ingests, batches per station and POSTs
`{'sid': ..., 'events': [...]}` to `/api/v1/events` with `X-API-Key`, the same
call a cellular station makes. Central therefore sees a LoRa node exactly as
it sees any other station, with `tx = 'lora'` on its heartbeats.

What it does not do, on purpose: no LoRaWAN, no MAC layer, no retransmission
from the gateway side. A node that wants delivery confirmation gets an ACK
frame back (its seq echoed) and can resend; the gateway itself keeps a
bounded retry queue so a backhaul blip does not lose the last hour.
"""
from __future__ import annotations
import json
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Callable, Deque, Dict, List, Optional
from comms import lora_frames as F
from comms.lora_radio import LoRaRadio, Packet

@dataclass
class NodeRoute:
    station_id: str
    api_key: str
    hbi_s: Optional[int] = 60
    fw: Optional[str] = None

def parse_gateway_map(text: str) -> Dict[int, NodeRoute]:
    """'1=elkhorn-node-1:KEY,2=elkhorn-node-2:KEY[:hbi]' -> {1: NodeRoute, ...}"""
    ...

def requests_post(url: str, headers: Dict, body: Dict, timeout: float=30.0) -> bool:
    ...

@dataclass
class GatewayStats:
    packets: int = 0
    frames: int = 0
    bad_bytes: int = 0
    posted: int = 0
    post_failures: int = 0

class LoRaGateway:

    def __init__(self, radio: LoRaRadio, routes: Dict[int, NodeRoute], central_url: str, post: PostFn=requests_post, ack: bool=True, gateway_node_id: int=0, max_queued: int=2000, clock: Callable[[], float]=time.time):
        ...

    def run_once(self, timeout_s: float=1.0) -> int:
        """Receive one packet, ingest every frame in it, flush what is due.
        Returns the number of frames handled."""
        ...

    def ingest(self, pkt: Packet) -> int:
        ...

    def _handle(self, frame: F.Frame, pkt: Packet) -> None:
        ...

    def _send_ack(self, frame: F.Frame, rssi_dbm: Optional[int]=None) -> None:
        ...

    def rx_loop(self, stop: threading.Event, timeout_s: float=1.0) -> None:
        """Receive, ingest and ACK until `stop` is set. A radio error is
        logged and retried after a second; it must not end the thread, since
        relay_station treats a dead gateway thread as a reason to exit."""
        ...

    def flush_loop(self, stop: threading.Event, interval_s: float=20.0, max_batches: int=4) -> None:
        """Post what the nodes sent, every `interval_s`, bounded per wake."""
        ...
    MAX_BATCH_BYTES = 9000

    def _pop_batch(self, q: Deque[Dict], max_batch: int, max_bytes: int) -> List[Dict]:
        ...

    def flush(self, max_batch: int=50, max_batches: Optional[int]=None, max_bytes: int=MAX_BATCH_BYTES) -> int:
        """POST what is pending, per station, at most `max_batches` POSTs
        (None = until empty). A failed batch goes back to the front of its
        queue and that station is left for the next flush. Returns events
        posted."""
        ...

    def pending_count(self) -> int:
        ...

    def heartbeat_block(self) -> Dict:
        """A few bytes for the gateway station's own heartbeat ('lora'):
        per node the last RSSI and how long ago it was heard, plus the
        frame/post counters. Central stores it with the heartbeat, so a
        node that goes quiet is visible on the gateway's row too."""
        ...

    def summary(self) -> str:
        ...
