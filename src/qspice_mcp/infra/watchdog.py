# In the name of God, the Most Gracious, the Most Merciful
"""Orphan watchdog. The implementation lives in mcp-app-core."""

from mcp_app_core.watchdog import is_process_alive, reap_pids, run_watchdog

__all__ = [
    "is_process_alive",
    "reap_pids",
    "run_watchdog",
]
