"""Upload review candidates (tiny detection spectrograms) to Central for
fleet-wide human labeling. Scans the local dataset dir, base64s each capture's
uint8 spectrogram, and POSTs new ones to /api/v1/candidates (deduped server-side
on the capture id). Tracks what's been sent so re-runs are cheap.

Only uploads over WiFi by default (thumbnails are small but many; the NB-IoT
link is reserved for detection events). Run periodically (timer/cron) or once.
"""
import base64
import glob
import json
import os
import sys
import numpy as np
import requests
from core.config import get_config
from comms.nbiot_http import is_wifi_available
BATCH = 20

def _sent():
    ...

def _mark(ids):
    ...

def main():
    ...
