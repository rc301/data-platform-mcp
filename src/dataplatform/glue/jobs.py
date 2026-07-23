"""Read-only inspection of Glue jobs."""

from __future__ import annotations

from typing import Any

from dataplatform.config import Session

# Fields that are meaningful when comparing / replicating a job. Everything
# else Glue returns (timestamps, ARNs, internal counters) is noise for the
# replicate → validate flow.
_PORTABLE_FIELDS = (
    "Name",
    "Description",
    "Role",
    "Command",
    "DefaultArguments",
    "Connections",
    "MaxRetries",
    "Timeout",
    "GlueVersion",
    "NumberOfWorkers",
    "WorkerType",
    "ExecutionProperty",
)


def list_jobs(session: Session, name_contains: str | None = None) -> list[dict[str, Any]]:
    """Return a lightweight listing of Glue jobs in the session's account."""

    glue = session.client("glue")
    jobs: list[dict[str, Any]] = []
    paginator = glue.get_paginator("get_jobs")
    for page in paginator.paginate():
        for job in page["Jobs"]:
            name = job["Name"]
            if name_contains and name_contains.lower() not in name.lower():
                continue
            jobs.append(
                {
                    "name": name,
                    "glue_version": job.get("GlueVersion"),
                    "worker_type": job.get("WorkerType"),
                    "number_of_workers": job.get("NumberOfWorkers"),
                    "description": job.get("Description"),
                }
            )
    return jobs


def get_job(session: Session, job_name: str) -> dict[str, Any]:
    """Return the full, portable configuration of a single Glue job."""

    glue = session.client("glue")
    job = glue.get_job(JobName=job_name)["Job"]
    return {field: job[field] for field in _PORTABLE_FIELDS if field in job}
