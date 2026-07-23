"""Workflow-altitude diagnosis of a Glue job run.

One call bundles what the agent needs to start diagnosing: run summary (times in
BRT, DPU, workers, duration), a regression signal (recent runs), and — only when
the run failed — a bounded error excerpt from CloudWatch. This keeps the agent
to a single high-signal round-trip instead of orchestrating several low-level
reads, and keeps the composition in the library (the MCP server stays a shell).
"""

from __future__ import annotations

from typing import Any

from dataplatform.config import Session
from dataplatform.glue.jobs import list_job_runs
from dataplatform.glue.logs import error_excerpt
from dataplatform.timeutil import fmt_brt

_FAILURE_STATES = {"FAILED", "ERROR", "TIMEOUT", "STOPPED"}


def diagnose_job_run(
    session: Session, job_name: str, run_id: str, *, recent_runs: int = 5
) -> dict[str, Any]:
    glue = session.client("glue")
    command_name = glue.get_job(JobName=job_name)["Job"].get("Command", {}).get("Name", "glueetl")
    run = glue.get_job_run(JobName=job_name, RunId=run_id)["JobRun"]
    state = run.get("JobRunState")

    history = list_job_runs(session, job_name, limit=recent_runs)
    for r in history:
        r["is_current"] = r["run_id"] == run_id

    result: dict[str, Any] = {
        "job": job_name,
        "run_id": run_id,
        "state": state,
        "summary": _summarize_run(job_name, run_id, run),
        "recent_runs": history,
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


def _summarize_run(job_name: str, run_id: str, run: dict[str, Any]) -> dict[str, Any]:
    return {
        "job": job_name,
        "run_id": run_id,
        "started_brt": fmt_brt(run.get("StartedOn")),
        "completed_brt": fmt_brt(run.get("CompletedOn")),
        "duration_seconds": run.get("ExecutionTime"),
        "worker_type": run.get("WorkerType"),
        "number_of_workers": run.get("NumberOfWorkers"),
        "max_capacity_dpu": run.get("MaxCapacity"),
        "dpu_seconds": run.get("DPUSeconds"),
    }
