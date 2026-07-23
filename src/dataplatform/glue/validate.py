"""Validate a replicated job and drive short validation runs."""

from __future__ import annotations

from typing import Any

from dataplatform.config import Session, ensure_sandbox
from dataplatform.glue.jobs import get_job

_REQUIRED = ("Role", "Command", "GlueVersion")


def validate_job(session: Session, job_name: str) -> dict[str, Any]:
    """Static checks that a (sandbox) job is well formed and runnable.

    Read-only. Confirms the job exists, has the fields Glue requires, and that
    its script location is set. Returns a structured report rather than raising.
    """

    issues: list[str] = []
    try:
        config = get_job(session, job_name)
    except session.client("glue").exceptions.EntityNotFoundException:
        return {"job": job_name, "ok": False, "issues": ["job does not exist"]}

    for field in _REQUIRED:
        if field not in config:
            issues.append(f"missing required field: {field}")

    command = config.get("Command", {})
    if not command.get("ScriptLocation"):
        issues.append("Command.ScriptLocation is empty")

    return {"job": job_name, "ok": not issues, "issues": issues, "config": config}


def start_validation_run(
    session: Session,
    job_name: str,
    arguments: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Trigger a validation run of a sandbox job. Guarded write."""

    ensure_sandbox(session)
    glue = session.client("glue")
    # TODO(empresa) item 6 — argumentos herdados: Arguments aqui IGNORA os
    # DefaultArguments do job. Jobs reais costumam precisar de --JOB_NAME,
    # --job-bookmark-option, etc. Para um run de validação barato e determinístico:
    # mesclar DefaultArguments + desabilitar bookmark + capar DPU/workers.
    run_id = glue.start_job_run(
        JobName=job_name,
        Arguments=arguments or {},
    )["JobRunId"]
    return {"job": job_name, "run_id": run_id, "sandbox_account": session.account_id}


def get_run_status(session: Session, job_name: str, run_id: str) -> dict[str, Any]:
    """Return the current state of a job run (read-only)."""

    run = session.client("glue").get_job_run(JobName=job_name, RunId=run_id)["JobRun"]
    return {
        "job": job_name,
        "run_id": run_id,
        "state": run.get("JobRunState"),
        "error_message": run.get("ErrorMessage"),
        "execution_time_seconds": run.get("ExecutionTime"),
    }
