"""Rotate Central's admin key without restarting or recreating the container.

Run INSIDE the container, so the key is generated where it is used and never
crosses the wire:

    docker exec <container> python -m server.rotate_admin_key

It writes a fresh key to ADMIN_KEY_FILE (default /data/admin_key, on the data
volume, so it survives a rebuild) atomically with mode 0600. The running
server picks it up on the next admin request (server/api.py re-reads the file
when it changes): the old key stops working and every dashboard session
is logged out. Nothing is printed but the new key's fingerprint; read the key
itself with

    docker exec <container> cat /data/admin_key

Station keys are separate and unaffected.

To go back to the ADMIN_KEY env var, delete the file (--remove).
"""
import argparse
import hashlib
import os
import secrets
import sys
from pathlib import Path

def fingerprint(key: str) -> str:
    ...

def write_key(path: Path, key: str) -> None:
    """Atomic replace with 0600 from the first byte: a reader sees the old
    key or the new one, never a torn or world-readable file."""
    ...

def main(argv=None) -> int:
    ...
