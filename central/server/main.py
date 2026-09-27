"""
RelayStation Central Server - Entry Point
Run with: python -m server.main or uvicorn server.main:app
"""
import argparse
import logging
import uvicorn
from .database import Database
from .api import app, init_database

def main():
    """Main entry point"""
    ...
