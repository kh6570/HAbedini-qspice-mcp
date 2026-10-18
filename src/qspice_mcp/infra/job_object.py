# In the name of God, the Most Gracious, the Most Merciful
"""Windows job object. The implementation lives in mcp-app-core."""

from mcp_app_core.jobs import (
    assign_process_to_kill_on_close_job,
    reset_job_object_state_for_tests,
)

__all__ = [
    "assign_process_to_kill_on_close_job",
    "reset_job_object_state_for_tests",
]
