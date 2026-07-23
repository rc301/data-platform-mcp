"""MCP server exposing the data-platform toolkit to AI agents.

This module is a *thin shell*: every tool imports and delegates to the public
library functions in :mod:`dataplatform.glue`. There is deliberately no business
logic here — only the FastMCP wiring, argument typing and the docstrings that
tell the model when (and when not) to reach for each tool.

Design rules encoded here:
  * Only what *changes between runs* is a tool. Static knowledge — schemas,
    framework conventions — is documentation, not a tool call.
  * Credentials are the developer's own (``AWS_PROFILE``). Writes are guarded to
    sandbox accounts by the library layer.
  * Transport is stdio, so the server can be launched directly by Claude Code.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from dataplatform import __version__, glue
from dataplatform.config import resolve_session

mcp = FastMCP("data-platform")


@mcp.tool()
def get_server_info() -> dict[str, Any]:
    """Return the toolkit version and the resolved AWS identity.

    Use this first to confirm which account/profile the developer's credentials
    resolve to before running anything that reads or writes AWS.

    Do NOT use it as a health check loop — call it once per session.
    """
    session = resolve_session()
    return {
        "library_version": __version__,
        "aws_account": session.account_id,
        "aws_profile": session.profile,
        "aws_region": session.region,
    }


@mcp.tool()
def list_glue_jobs(name_contains: str | None = None) -> list[dict[str, Any]]:
    """List Glue jobs in the current (developer) account.

    Use to discover the exact job name before inspecting or replicating it.
    Optionally filter with a case-insensitive substring.

    Do NOT use to fetch full job configuration — use ``inspect_glue_job`` for
    that. This returns only a lightweight summary.
    """
    return glue.list_jobs(resolve_session(), name_contains=name_contains)


@mcp.tool()
def inspect_glue_job(job_name: str) -> dict[str, Any]:
    """Return the full portable configuration of one existing Glue job.

    Use before replicating, to review a job's command, arguments, role and
    worker sizing. Read-only.

    Do NOT use to browse — call ``list_glue_jobs`` first if you don't know the
    exact name.
    """
    return glue.get_job(resolve_session(), job_name)


@mcp.tool()
def replicate_job_to_sandbox(
    job_name: str,
    sandbox_profile: str,
    target_job_name: str | None = None,
    role_override: str | None = None,
    script_location_override: str | None = None,
) -> dict[str, Any]:
    """Copy an existing job into a sandbox account so it can be tested safely.

    Reads the job from the developer's default profile and writes it using
    ``sandbox_profile``. The write is refused unless that profile resolves to an
    account listed in ``DATAPLATFORM_SANDBOX_ACCOUNTS``.

    Use to stand up a throwaway copy of a production job for experimentation.
    Provide ``role_override`` / ``script_location_override`` when the sandbox
    uses different IAM roles or script buckets.

    Do NOT use to modify the original job or to write to a non-sandbox account —
    both are structurally prevented.
    """
    return glue.replicate_to_sandbox(
        source_session=resolve_session(),
        sandbox_session=resolve_session(profile=sandbox_profile),
        job_name=job_name,
        target_job_name=target_job_name,
        role_override=role_override,
        script_location_override=script_location_override,
    )


@mcp.tool()
def validate_sandbox_job(job_name: str, sandbox_profile: str) -> dict[str, Any]:
    """Statically validate a replicated sandbox job is well formed.

    Use right after ``replicate_job_to_sandbox`` to confirm the copy has the
    required fields and a script location before spending time on a real run.
    Read-only; returns a report with an ``ok`` flag and a list of issues.

    Do NOT use as a substitute for an actual run — it does not execute the job.
    """
    return glue.validate_job(resolve_session(profile=sandbox_profile), job_name)


@mcp.tool()
def run_sandbox_job(
    job_name: str,
    sandbox_profile: str,
    arguments: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Start a validation run of a sandbox job. Guarded write.

    Use to actually execute a replicated job once static validation passes.
    Refused unless ``sandbox_profile`` resolves to a configured sandbox account.
    Returns a ``run_id`` to poll with ``get_sandbox_run_status``.

    Do NOT use against production jobs or to run at scale — this is for short
    validation runs in the sandbox only.
    """
    return glue.start_validation_run(
        resolve_session(profile=sandbox_profile), job_name, arguments=arguments
    )


@mcp.tool()
def get_sandbox_run_status(job_name: str, run_id: str, sandbox_profile: str) -> dict[str, Any]:
    """Poll the state of a sandbox job run started by ``run_sandbox_job``.

    Use to check whether a validation run succeeded, is still running, or
    failed (with the error message). Read-only.

    Do NOT busy-loop on this — poll at sensible intervals.
    """
    return glue.get_run_status(resolve_session(profile=sandbox_profile), job_name, run_id)


@mcp.tool()
def diagnose_job_run(job_name: str, run_id: str, profile: str | None = None) -> dict[str, Any]:
    """Diagnose one Glue job run in a single high-signal call.

    Returns a bundle: run summary (times in BRT, DPU, workers, duration), the
    recent-run history (to tell whether the failure is new or chronic), and —
    only if the run failed — a bounded error excerpt from CloudWatch. Start here
    when a run fails; follow up with ``inspect_table`` / ``check_partitions``
    only if the excerpt points at data or schema.

    Runs against the job's account (``profile`` defaults to the dev's
    ``AWS_PROFILE``).

    Do NOT loop this to poll a running job — use it once the run has finished.
    """
    return glue.diagnose_job_run(resolve_session(profile=profile), job_name, run_id)


@mcp.tool()
def list_job_runs(job_name: str, limit: int = 5, profile: str | None = None) -> list[dict[str, Any]]:
    """List a job's most recent runs (id, state, start in BRT, duration).

    Reusable primitive for any command that needs run history: checking a
    regression, confirming the last sandbox run was green before promoting, or
    reporting when a job last succeeded. Runs against the job's account.

    Do NOT use to diagnose a specific failure — use ``diagnose_job_run`` for the
    full picture of one run.
    """
    return glue.list_job_runs(resolve_session(profile=profile), job_name, limit=limit)


@mcp.tool()
def inspect_table(database: str, table: str, data_profile: str) -> dict[str, Any]:
    """Inspect a source table's schema and format (read-only, data account).

    Returns columns, partition keys, S3 location and whether the table is
    Iceberg or Hive. Use to check for schema drift against the job's script, and
    to learn the table format before checking partitions.

    ``data_profile`` must resolve to the account holding the table (a third
    account the sandbox can read). Do NOT use for the job's own account.
    """
    return glue.inspect_table(resolve_session(profile=data_profile), database, table)


@mcp.tool()
def check_partitions(
    database: str, table: str, expression: str, data_profile: str
) -> dict[str, Any]:
    """Check whether catalog partitions matching ``expression`` exist.

    ``expression`` is a Glue partition filter, e.g. ``dt='2026-07-01'``. Use to
    confirm a source partition the job expected is actually present. Read-only,
    runs in the data account via ``data_profile``.

    Do NOT use on Iceberg tables — it detects them and refuses, because their
    partitions are not in the Glue Data Catalog. Do NOT use it to read data;
    it only checks presence.
    """
    return glue.check_partitions(resolve_session(profile=data_profile), database, table, expression)


def main() -> None:
    """Start the stdio MCP server.

    Invoked via ``data-platform-mcp serve`` (the CLI dispatches here); also
    runnable directly as ``python -m dataplatform.mcp.server``.
    """
    mcp.run()


if __name__ == "__main__":
    main()
