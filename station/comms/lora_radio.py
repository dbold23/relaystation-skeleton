"""LoRa radio drivers behind one small interface.

Two HAT families cover what sits on a Raspberry Pi header in 2026:

* **E22-style UART modules** -- the Waveshare "SX1262 915M LoRa HAT" is an
  EBYTE E22-900T22S behind a serial port. The Pi never talks to the SX1262;
  it talks to the module's MCU at 9600 8N1, and the module hides spreading
  factor behind an "air rate". Two GPIOs (M0, M1) select the mode. This is
  `E22SerialRadio`.
* **SX127x/RFM95W SPI boards** -- Adafruit's LoRa Radio Bonnet and the
  Dragino LoRa/GPS HAT. The Pi drives the chip directly over SPI through
  `adafruit_rfm9x`. This is `RFM9xRadio`.

`FakeRadio` is the in-memory one the tests and a laptop use.

The interface is deliberately tiny -- `send(bytes)`, `receive(timeout)` ->
`Packet | None`, `close()` -- because that is all the frame codec and the
gateway need, and because a third HAT should cost one class, not a redesign.

Which one to instantiate comes from `[LoRa] driver` in config.ini via
`open_radio(load_lora_config(path))`. Nothing here imports hardware libraries
at module load: a station without a HAT, or a laptop, can import this file.
"""
from __future__ import annotations
import collections
import configparser
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional, Tuple

class TxGuard:

    def __init__(self, keep: int=256):
        ...

    def note(self, start: float, end: float) -> None:
        ...

    def was_transmitting(self, t0: float, t1: float, guard_s: float=0.02) -> bool:
        """True if any transmission overlapped [t0, t1] (with a small guard
        either side for PA ramp and settling)."""
        ...

    def duty_cycle(self, window_s: float=3600.0, now: Optional[float]=None) -> float:
        ...

class PowerPolicy:
    """Step the transmit power down while the gateway hears us with margin,
    and back up the moment it does not. Fed by the RSSI in each ACK.

    Every step down is 4x less PA current for the same airtime, and the same
    factor less energy splashed into the SDR next door. The E22's ladder is
    10/13/17/22 dBm; an RFM95 can take any of 5..23."""

    def __init__(self, ladder=(10, 13, 17, 22), start_dbm: Optional[int]=None, target_rssi_dbm: int=-100, hysteresis_db: int=6, misses_before_up: int=2):
        ...

    def on_ack(self, rssi_dbm: Optional[int]) -> int:
        """Called with the RSSI the gateway reported (None = ACK without one).
        Returns the power to use for the next frame."""
        ...

    def on_missed_ack(self) -> int:
        ...
E22_BASE_MHZ = 850.125

@dataclass
class Packet:
    data: bytes
    rssi_dbm: Optional[int] = None
    snr_db: Optional[float] = None
    received_at: float = 0.0

class LoRaRadio:
    """What the codec and gateway need from any radio."""

    def send(self, data: bytes) -> None:
        ...

    def receive(self, timeout_s: float=1.0) -> Optional[Packet]:
        ...

    def close(self) -> None:
        ...

    def describe(self) -> str:
        ...

def load_lora_config(path: Optional[str]=None, overrides: Optional[Dict[str, str]]=None) -> Dict[str, str]:
    """[LoRa] section of config.ini over DEFAULTS, then explicit overrides.
    Missing file or section is fine: the defaults describe a Waveshare HAT
    on /dev/serial0 at 915.125 MHz."""
    ...

def open_radio(cfg: Dict[str, str]) -> LoRaRadio:
    ...

def _bool(v) -> bool:
    ...

def _int_or_none(v) -> Optional[int]:
    ...

class FakeRadio(LoRaRadio):
    """In-memory radio. `link(other)` makes two of them hear each other."""

    def __init__(self):
        ...

    def link(self, other: 'FakeRadio') -> None:
        ...

    def set_power(self, tx_power_dbm: int) -> bool:
        ...

    def send(self, data: bytes) -> None:
        ...

    def receive(self, timeout_s: float=1.0) -> Optional[Packet]:
        ...

    def describe(self) -> str:
        ...
E22_SUBPACKET_240 = 0
E22_RSSI_BYTE = 128
E22_WOR_2000MS = 3

def e22_channel(frequency_mhz: float) -> int:
    ...

def e22_config_frame(frequency_mhz: float, tx_power_dbm: int=22, air_rate: str='2.4k', uart_baud: int=9600, address: int=0, net_id: int=0, rssi_byte: bool=True, save: bool=False) -> bytes:
    """The 12-byte register write the E22-900T22S expects in configuration
    mode (M0=0, M1=1): C0/C2, start address 0, length 9, then ADDH ADDL NETID
    SPED OPTION CHAN OPTION2 CRYPT_H CRYPT_L. Matches EBYTE's E22-900T22S
    register map and Waveshare's sx126x.py. Verify on the bench by reading it
    back (C1 00 09) before trusting a link that will not come up."""
    ...

def e22_decode_config(reply: bytes) -> Dict[str, object]:
    """Inverse of e22_config_frame for a module's reply (C1 00 09 + 9
    registers). Returns the settings as the module holds them, so a setup
    tool can compare what it wrote against what stuck. Raises ValueError on
    anything that is not a 12-byte C1 reply."""
    ...

class E22SerialRadio(LoRaRadio):
    """Waveshare SX1262 LoRa HAT and any EBYTE E22-900T22S on a UART.

    Transparent mode: whatever bytes go in come out of every module on the
    same channel/address/net id, with one RSSI byte appended when enabled.
    Packets are delimited by silence on the serial line, so `receive` reads
    until an inter-byte gap and then hands back one packet. Two air packets
    closer than that gap arrive as one `Packet`; the frame codec re-splits
    them, at the cost of the first one's RSSI byte being read as data (the
    magic-byte resync skips it) and both frames carrying the last RSSI.

    M0/M1: M0=0,M1=0 normal; M0=0,M1=1 configuration. Given as BCM pins (the
    Waveshare HAT: jumper B, M0/M1 caps removed, then 22 and 27). Pass None for both
    when the module was configured once with `save=True` and the pins are not
    wired: the driver then skips configuration and just uses the port.
    """

    def __init__(self, port: str='/dev/serial0', baud: int=9600, frequency_mhz: float=915.125, tx_power_dbm: int=22, air_rate: str='2.4k', address: int=0, net_id: int=0, m0_pin: Optional[int]=22, m1_pin: Optional[int]=27, rssi_byte: bool=True, configure: bool=True, sleep_when_idle: bool=False):
        ...

    @staticmethod
    def _open_pins(m0_pin: int, m1_pin: int):
        ...

    def _set_mode(self, m0: bool, m1: bool) -> None:
        ...

    def _normal_mode(self):
        ...

    def _config_mode(self):
        ...

    def sleep(self) -> None:
        """Deep sleep (M0=1, M1=1). No-op without the mode pins."""
        ...

    def wake(self) -> None:
        ...

    def configure(self, save: bool=False) -> bytes:
        """Write the register frame, read it back, remember the readback.
        Returns the module's reply (12 bytes starting C1 on success)."""
        ...

    def read_config(self) -> bytes:
        ...

    def set_power(self, tx_power_dbm: int) -> bool:
        """Change TX power (E22 ladder 22/17/13/10) with a config write.
        Returns True when the module was reconfigured. Without the mode
        pins this is refused: a register frame written in transparent mode
        is not a configuration, it is twelve bytes transmitted on air."""
        ...
    AIRTIME_FIXED_S = 0.2
    AIRTIME_OVERHEAD = 1.1

    def airtime_s(self, nbytes: int) -> float:
        """Estimated time the PA is keyed for a packet of `nbytes`, from the
        write to the end of the burst. Used to hold after a send and to
        record the window the detector blanks; must not undershoot."""
        ...

    def send(self, data: bytes) -> None:
        ...

    def receive(self, timeout_s: float=1.0) -> Optional[Packet]:
        ...

    def _air_bps(self) -> int:
        ...

    def close(self) -> None:
        ...

    def describe(self) -> str:
        ...

class RFM9xRadio(LoRaRadio):
    """adafruit_rfm9x on SPI, dtparam=spi=on either way.

    Adafruit LoRa Radio Bonnet: CS=CE1, RESET=D25.
    Dragino LoRa/GPS HAT: the module's NSS is wired to BCM25 (a plain GPIO,
    not a hardware chip-select) and RESET to BCM17, so CS=D25, RESET=D17
    (Dragino LoRa GPS HAT user manual v1.0, pin table). Any Blinka pin name
    works here; it is looked up on `board`."""

    def __init__(self, frequency_mhz: float=915.0, tx_power_dbm: int=23, spreading_factor: int=9, bandwidth_hz: int=125000, coding_rate: int=5, cs: str='CE1', reset: str='D25', sleep_when_idle: bool=False):
        ...

    def set_power(self, tx_power_dbm: int) -> bool:
        ...

    def send(self, data: bytes) -> None:
        ...

    def receive(self, timeout_s: float=1.0) -> Optional[Packet]:
        ...

    def describe(self) -> str:
        ...
