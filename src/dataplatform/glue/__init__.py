"""Public Glue operations: the surface the MCP server delegates to."""

from dataplatform.glue.diagnose import diagnose_job_run
from dataplatform.glue.jobs import get_job, list_job_runs, list_jobs
from dataplatform.glue.tables import check_partitions, inspect_table

__all__ = [
    "list_jobs",
    "get_job",
    "list_job_runs",
    "diagnose_job_run",
    "inspect_table",
    "check_partitions",
]
