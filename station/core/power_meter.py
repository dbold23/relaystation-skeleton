"""Measured board power, and the energy counter built from it.

Every watt figure on the dashboard was a MODEL of CPU load until this existed:
Central's `stations.power_w` had been NULL fleet-wide since the column was
added, so the fleet view showed "~6.1 W" computed from cpu_percent and a
two-point line (Relay-Central server/api.py:3043). The Pi 5 meters its own 5 V
input through the on-board PMIC, so the real number costs one subprocess call.

Pi 5 only. `vcgencmd pmic_read_adc` does not exist on a Pi 4 or a dev Mac, and
read_power() reports None there rather than guessing -- Central still shows its
own estimate, which is correctly labelled with a leading tilde.

Two things here are not obvious and both were found by review, not by testing.

**The PMIC total is two different physical quantities.** With EXT5V present it
is the board input at the USB-C connector, which includes USB VBUS and
therefore the RTL-SDR. Without it, the fallback sums the PMIC's regulated rails,
which excludes every conversion loss AND excludes USB entirely -- the SDR
becomes invisible and the figure lands 30-45% low on a 5.5 W station. Those
must never be mixed into one series, so read_power() names its source and only
the board-input reading is reported as watts.

**A value sampled once per heartbeat is biased, not merely coarse.** The
heartbeat fires at the transmit boundary, which correlates with the peak of the
work cycle; zero-order-holding that sample across a 30-minute low-power
interval overestimates mean load several-fold. So the station integrates
energy itself at the 10 s status cadence and reports a monotonic counter.
Central differences successive counters, which makes the accounting immune to
cadence changes, clock steps, queue reordering, and -- the case that actually
happened -- an offline queue that pruned 83% of a 42-day blackout: the energy
used during the pruned window is still inside the counter at the far end.
"""
import logging
import subprocess
import time
import uuid
DEFAULT_TIMEOUT = 3
MAX_SAMPLE_GAP_S = 60.0

def parse_pmic_read_adc(text):
    """Parse `vcgencmd pmic_read_adc` output (pure function, unit-testable).

    Lines look like:
        VDD_CORE_A current(15)=4.44580078A
        EXT5V_V volt(24)=5.09578223V
    Rail base name = token with the trailing _A/_V stripped. Returns
    (total_w, rails) where rails maps lowercase rail name -> {'v':, 'a':}
    for every rail with both readings. total_w = EXT5V volts x amps when
    both are present (the 5V input feed), else the sum of rail VxI pairs.
    Malformed lines are skipped.
    """
    ...

def pmic_source(text):
    """Which quantity parse_pmic_read_adc() returned for this text.

    SRC_BOARD when the EXT5V input rail carried both a volt and a current line,
    SRC_RAILS when the sum-of-rails fallback ran. The two differ by 30-45% and
    mean different things, so nothing may integrate them into one series.
    """
    ...

def parse_get_throttled(text):
    """Parse `vcgencmd get_throttled` output, e.g. 'throttled=0x0' -> '0x0'."""
    ...

def _vcgencmd(*args, timeout=DEFAULT_TIMEOUT):
    """stdout of vcgencmd, or None on any failure (absent, non-zero, slow)."""
    ...

def read_power(timeout=DEFAULT_TIMEOUT):
    """(watts, source, throttled_hex); any element None if unavailable.

    Never raises: this runs inside the detection loop, and a power reading is
    not worth losing a heartbeat over. The readings are independent -- a Pi 4
    has get_throttled but no pmic_read_adc -- so they are reported
    independently rather than failing as a pair.
    """
    ...

class EnergyCounter:
    """Monotonic watt-hours at the board input, integrated on-station.

    Call sample() on every status tick (10 s). Only board-input readings are
    integrated; a rail-sum reading is a different quantity and is discarded
    rather than blended. Elapsed time comes from time.monotonic(), so a clock
    step -- which this fleet does deliberately, from Central's server_time --
    cannot corrupt the integral.

    `session` changes whenever the process restarts, which is the signal
    Central needs: the counter is only differenceable within one session.
    """

    def __init__(self):
        ...

    def sample(self, reading=None):
        """Integrate one reading. Returns the watts used, or None if skipped."""
        ...

    def coverage(self):
        """Fraction of elapsed time actually covered by samples, 0.0 to 1.0."""
        ...

    def report(self):
        """The heartbeat block, or {} before anything has been integrated."""
        ...
