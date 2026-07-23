"""Read-only inspection of Glue jobs."""

from __future__ import annotations

from typing import Any

from dataplatform.config import Session
from dataplatform.timeutil import fmt_brt

# Fields that are meaningful when comparing / replicating a job. Everything
# else Glue returns (timestamps, ARNs, internal counters) is noise for the
# replicate → validate flow.
# TODO(empresa) item 4 — campos incompletos: jobs reais provavelmente usam
# SecurityConfiguration, NonOverridableArguments, NotificationProperty e
# MaxCapacity (pythonshell NÃO usa NumberOfWorkers). Tags nem vêm no get_job —
# é get_tags à parte, e a governança pode exigi-las. Acrescente o que a empresa
# usa antes de confiar na replicação (ver também replicate._to_create_input).
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


def list_job_runs(session: Session, job_name: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return the most recent runs of a job (id, state, start in BRT, duration).

    Reusable primitive: regression checks (analyze), "was the last sandbox run
    green?" (code-review), and "when did it last succeed?" (docs) all build on
    this rather than each re-querying run history.
    """
    runs = session.client("glue").get_job_runs(JobName=job_name, MaxResults=limit)["JobRuns"]
    return [
        {
            "run_id": r.get("Id"),
            "state": r.get("JobRunState"),
            "started_brt": fmt_brt(r.get("StartedOn")),
            "duration_seconds": r.get("ExecutionTime"),
        }
        for r in runs
    ]
