"""Compact binary frames for the LoRa hop between a node and its gateway.

Why a binary codec and not JSON: a LoRa packet at the air rates a 915 MHz
link runs is tens of bytes and hundreds of milliseconds of airtime. The
station's JSON heartbeat is ~250 bytes. A detection event is four numbers and
a time; it fits in 9 bytes here. The gateway turns a frame back into the exact
event dict Central already ingests (`{'e': 'd', 'f': ..., 's': ..., ...}`),
so nothing on Central changes for a LoRa node.

Frame layout (big-endian):

    0   magic      0xA7
    1   version    1
    2-3 node id    16-bit, from [LoRa] node_id
    4   boot       8-bit boot counter, so seq wraps and reboots stay unique
    5-6 seq        16-bit per-node sequence
    7   type       FrameType
    8   length     payload bytes (0..MAX_PAYLOAD)
    9.. payload
    -2  crc16      CRC-16/CCITT-FALSE over everything before it

Times ride as an AGE in seconds relative to transmission, not as an absolute
timestamp: a node that has never had NTP or cellular does not know the time,
but it always knows how long ago it heard the pulse. The gateway, which does
know the time, subtracts the age on arrival. That is also why a frame must be
transmitted promptly after it is built, and why the codec caps age at 65535 s
(about 18 h) -- anything older is a queue flush, and the gateway marks it.
"""
from __future__ import annotations
import struct
from dataclasses import dataclass
from typing import Dict, List, Optional
MAGIC = 167
VERSION = 1
CRC_LEN = 2
MAX_PAYLOAD = 200
MAX_AGE_S = 65535

class FrameType:
    HEARTBEAT = 1
    DETECTION = 2
    LOCK = 3
    LOG = 4
    BEACON = 5
    ACK = 6
    DETECTIONS = 7

class FrameError(ValueError):
    """The bytes are not a frame we can trust."""
FLAG_SDR = 1
FLAG_QUEUE_FLUSH = 2

def crc16(data: bytes, poly: int=4129, init: int=65535) -> int:
    """CRC-16/CCITT-FALSE. Pure Python; frames are tiny."""
    ...

@dataclass
class Frame:
    node_id: int
    boot: int
    seq: int
    ftype: int
    payload: bytes

    @property
    def type_name(self) -> str:
        ...

    @property
    def uid(self) -> str:
        """Central's per-station dedup id. Boot counter + seq: unique across
        a reboot, which is exactly when a node would otherwise resend seq 0."""
        ...

def encode(node_id: int, boot: int, seq: int, ftype: int, payload: bytes) -> bytes:
    ...

def decode(data: bytes) -> Frame:
    ...

def find_frame(buf: bytes) -> Optional[tuple]:
    """Locate the first complete, valid frame in a byte buffer (a serial read
    can glue two packets or prepend noise). Returns (frame, end_offset) or
    None if no complete frame is present yet."""
    ...

def _clamp(v, lo, hi):
    ...

def heartbeat_payload(uptime_s: float, cpu_pct: float, mem_pct: float, temp_c: Optional[float], tags: int, sdr: bool, queue_depth: int, loop_count: int, queue_flush: bool=False) -> bytes:
    ...

def detection_payload(freq_khz: int, signal_db: float, confidence: int, age_s: float) -> bytes:
    ...

def beacon_payload(counter: int, tx_power_dbm: int, interval_s: int) -> bytes:
    ...

def log_payload(level: str, text: str) -> bytes:
    ...

def ack_payload(seq: int, rssi_dbm: Optional[int]=None) -> bytes:
    ...

def detections_payload(records) -> bytes:
    """Many detections in one burst: an iterable of (freq_khz, signal_db,
    confidence, age_s), 9 bytes each, up to 22 per frame.

    This is the battery and the airtime argument in one place. A tag pulses
    every ~1.7 s and the detector reports it every few seconds; one LoRa burst
    per report is ~200 ms of a 22 dBm transmitter a few centimetres from the
    SDR, several times a minute, all day. One burst per interval carrying
    every channel heard since the last one is the same information at a
    fraction of the keying, and the detector is blind for one window instead
    of many."""
    ...

def decode_payload(frame: Frame) -> Dict:
    """Frame -> plain dict of the fields the payload carries."""
    ...

def to_central_events(frame: Frame, received_at: float, fw: Optional[str]=None, hbi: Optional[int]=None) -> List[Dict]:
    """Every Central event a frame carries (a DETECTIONS frame carries many,
    each with its own dedup id suffix)."""
    ...

def to_central_event(frame: Frame, received_at: float, fw: Optional[str]=None, hbi: Optional[int]=None) -> Optional[Dict]:
    """The event dict Central's /events endpoint already accepts, built at the
    gateway (which knows the wall clock). Returns None for frame types Central
    has no use for (beacon, ack). For DETECTIONS use to_central_events."""
    ...
