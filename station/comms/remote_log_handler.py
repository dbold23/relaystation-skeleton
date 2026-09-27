"""
Remote Log Handler for RelayStation
Forwards important logs (WARNING+) to central server.

IMPORTANT: Logs from the comms.* namespace are suppressed to prevent
a feedback loop where send-failure logs get re-queued and amplify.
"""
import logging
import threading
import time
from typing import Optional, Callable

class RemoteLogHandler(logging.Handler):
    """
    Custom log handler that forwards logs to central server.
    Only forwards WARNING and above to minimize bandwidth.

    Suppresses logs from the comms.* namespace to prevent a feedback loop
    where send-failure warnings get re-queued into the send pipeline.
    """

    def __init__(self, report_callback: Callable[[str, str], None], min_level: int=logging.WARNING):
        """
        Initialize remote log handler.

        Args:
            report_callback: Function to call with (level, message)
            min_level: Minimum level to forward (default: WARNING)
        """
        ...

    def emit(self, record: logging.LogRecord):
        """Handle a log record"""
        ...

    def flush(self):
        """Flush queued logs to central server"""
        ...

def setup_remote_logging(central_client) -> Optional[RemoteLogHandler]:
    """
    Set up remote logging to central server.

    Args:
        central_client: CentralClient instance

    Returns:
        RemoteLogHandler instance or None if setup fails
    """
    ...
