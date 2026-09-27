"""
Storage Manager for Spectrogram Logger
Handles disk space monitoring, file cleanup, and retention policies
"""
import logging
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class StorageManager:
    """Manage storage for spectrogram files with automatic cleanup"""

    def __init__(self, base_path: str, max_gb: float=18, warning_threshold: float=0.9):
        """
        Initialize storage manager

        Args:
            base_path: Base directory for spectrogram storage
            max_gb: Maximum storage allocation in GB
            warning_threshold: Trigger cleanup at this fraction of max_gb
        """
        ...

    def get_usage(self) -> Dict[str, float]:
        """
        Calculate current storage usage

        Returns:
            Dict with bytes, gb, and percent usage
        """
        ...

    def get_available_space(self) -> Dict[str, float]:
        """
        Get available disk space on the filesystem

        Returns:
            Dict with total, used, free, and percent
        """
        ...

    def cleanup_if_needed(self, target_percent: float=0.7) -> bool:
        """
        Remove old files if approaching storage limit

        Args:
            target_percent: Clean to this fraction of max_bytes

        Returns:
            True if cleanup was performed
        """
        ...

    def cleanup_by_age(self, retention_days: int=14) -> int:
        """
        Remove files older than retention period

        Args:
            retention_days: Keep files newer than this many days

        Returns:
            Number of files deleted
        """
        ...

    def get_daily_subdirs(self) -> List[Path]:
        """
        Get list of daily subdirectories (YYYY-MM-DD format)

        Returns:
            List of directory paths sorted by date
        """
        ...

    def get_storage_summary(self) -> Dict:
        """
        Get comprehensive storage summary

        Returns:
            Dict with usage stats, file counts, and oldest/newest dates
        """
        ...

    def ensure_daily_directory(self, date: Optional[datetime]=None) -> Path:
        """
        Create and return daily subdirectory path

        Args:
            date: Date for directory (default: today)

        Returns:
            Path to daily directory
        """
        ...
