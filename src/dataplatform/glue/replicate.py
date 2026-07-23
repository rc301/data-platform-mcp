"""Replicate a job's configuration into a sandbox account."""

from __future__ import annotations

from typing import Any

from dataplatform.config import Session, ensure_sandbox
from dataplatform.glue.jobs import get_job


def _to_create_input(config: dict[str, Any], overrides: dict[str, str]) -> dict[str, Any]:
    payload = {k: v for k, v in config.items() if k != "Name"}
    if "Role" in overrides:
        payload["Role"] = overrides["Role"]
    if "ScriptLocation" in overrides and "Command" in payload:
        payload["Command"] = {**payload["Command"], "ScriptLocation": overrides["ScriptLocation"]}
    return payload


def replicate_to_sandbox(
    source_session: Session,
    sandbox_session: Session,
    job_name: str,
    target_job_name: str | None = None,
    role_override: str | None = None,
    script_location_override: str | None = None,
) -> dict[str, Any]:
    """Copy ``job_name`` from the source account into the sandbox account.

    The source read uses the developer's default credentials; the write uses
    ``sandbox_session`` and is guarded by :func:`ensure_sandbox`. Existing jobs
    are updated in place, otherwise the job is created.
    """

    ensure_sandbox(sandbox_session)

    config = get_job(source_session, job_name)
    target = target_job_name or job_name

    overrides: dict[str, str] = {}
    if role_override:
        overrides["Role"] = role_override
    if script_location_override:
        overrides["ScriptLocation"] = script_location_override
    job_input = _to_create_input(config, overrides)

    glue = sandbox_session.client("glue")
    existing = {j["name"] for j in _names(glue)}
    if target in existing:
        glue.update_job(JobName=target, JobUpdate=job_input)
        action = "updated"
    else:
        glue.create_job(Name=target, **job_input)
        action = "created"

    return {
        "action": action,
        "source_job": job_name,
        "target_job": target,
        "sandbox_account": sandbox_session.account_id,
    }


def _names(glue) -> list[dict[str, str]]:
    out = []
    for page in glue.get_paginator("get_jobs").paginate():
        out.extend({"name": j["Name"]} for j in page["Jobs"])
    return out
