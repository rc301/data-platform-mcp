"""Workflow-altitude diagnosis of a Glue job run.

One call bundles what the agent needs to start diagnosing: run summary (times in
BRT, DPU, workers, duration), a regression signal (recent runs), and — only when
the run failed — a bounded error excerpt from CloudWatch. This keeps the agent
to a single high-signal round-trip instead of orchestrating several low-level
reads, and keeps the composition in the library (the MCP server stays a shell).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from dataplatform.config import Session
from dataplatform.glue.logs import error_excerpt

# Brazil has had no DST since 2019, so a fixed -03:00 offset is correct.
BRT = timezone(timedelta(hours=-3), "BRT")

_FAILURE_STATES = {"FAILED", "ERROR", "TIMEOUT", "STOPPED"}


def diagnose_job_run(
    session: Session, job_name: str, run_id: str, *, recent_runs: int = 5
) -> dict[str, Any]:
    glue = session.client("glue")
    command_name = glue.get_job(JobName=job_name)["Job"].get("Command", {}).get("Name", "glueetl")
    run = glue.get_job_run(JobName=job_name, RunId=run_id)["JobRun"]
    state = run.get("JobRunState")

    result: dict[str, Any] = {
        "job": job_name,
        "run_id": run_id,
        "state": state,
        "summary": _summarize_run(job_name, run_id, run),
        "recent_runs": _recent_runs(glue, job_name, run_id, recent_runs),
    }

    if state == "SUCCEEDED":
        result["outcome"] = "success"
    elif state in _FAILURE_STATES:
        result["outcome"] = "failure"
        result["error_message"] = run.get("ErrorMessage")
        result["error_excerpt"] = error_excerpt(session, run_id, command_name)
    else:
        result["outcome"] = "in_progress"
    return result


def _fmt_brt(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(BRT).strftime("%Y-%m-%d %H:%M:%S %Z")


def _summarize_run(job_name: str, run_id: str, run: dict[str, Any]) -> dict[str, Any]:
    return {
        "job": job_name,
        "run_id": run_id,
        "started_brt": _fmt_brt(run.get("StartedOn")),
        "completed_brt": _fmt_brt(run.get("CompletedOn")),
        "duration_seconds": run.get("ExecutionTime"),
        "worker_type": run.get("WorkerType"),
        "number_of_workers": run.get("NumberOfWorkers"),
        "max_capacity_dpu": run.get("MaxCapacity"),
        "dpu_seconds": run.get("DPUSeconds"),
    }


def _recent_runs(
    glue: Any, job_name: str, current_run_id: str, limit: int
) -> list[dict[str, Any]]:
    runs = glue.get_job_runs(JobName=job_name, MaxResults=limit).get("JobRuns", [])
    return [
        {
            "run_id": r.get("Id"),
            "state": r.get("JobRunState"),
            "started_brt": _fmt_brt(r.get("StartedOn")),
            "duration_seconds": r.get("ExecutionTime"),
            "is_current": r.get("Id") == current_run_id,
        }
        for r in runs
    ]
