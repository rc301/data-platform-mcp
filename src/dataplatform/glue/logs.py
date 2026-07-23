"""CloudWatch log extraction for Glue job runs.

The goal is a *bounded, high-signal* excerpt — never the raw stream. Fatal
errors sit near the end of the error stream, so we tail it and return a window
around the last error marker (or the tail itself if no marker is found). This
keeps large logs out of the agent's context; the model interprets the excerpt.
"""

from __future__ import annotations

import os
from typing import Any

from dataplatform.config import AwsClientError, Session

# The /aws-glue/jobs root is stable, but group names below it vary per account:
#  * Error Logs live at a security-config-nested path ending in `/error`
#    (e.g. /aws-glue/jobs/<sec-config>/<domain>/<role>/error) — this is stderr,
#    where the traceback lands.
#  * All Logs (continuous) is a flat name starting with `logs-v2`
#    (e.g. /aws-glue/jobs/logs-v2-<sec-config>).
# So we DISCOVER groups under the root and classify by name, best-first: `/error`
# groups, then `logs-v2*` groups. An env var can override with an explicit list.
_LOG_GROUP_ROOT = "/aws-glue/jobs"
_LOG_GROUPS_ENV = "DATAPLATFORM_GLUE_LOG_GROUPS"  # explicit, comma-separated, best-first
# Fallback for non-nested accounts, appended after discovery.
_DEFAULT_ERROR_GROUPS = ("/aws-glue/jobs/error", "/aws-glue/jobs/logs-v2")


def _leaf(name: str) -> str:
    return name.rsplit("/", 1)[-1]

# Markers that usually bracket the real cause. Order-independent; matched as
# substrings against each event line.
_ERROR_MARKERS = ("Traceback", "Caused by", "Exception", "ERROR", "Error")

_CONTEXT_BEFORE = 15

# Within a group the driver stream is exactly `<run_id>` and executors are
# `<run_id>_g-<worker_hash>` (plus a noisy `<run_id>-progress-bar`). One stream is
# a guess, so we scan up to this many, best-first, until one carries an error.
_MAX_STREAMS_SCANNED = 5


def _list_log_group_names(logs: Any, prefix: str) -> list[str]:
    names: list[str] = []
    kwargs: dict[str, Any] = {"logGroupNamePrefix": prefix, "limit": 50}
    while True:
        resp = logs.describe_log_groups(**kwargs)
        names.extend(g["logGroupName"] for g in resp.get("logGroups", []))
        token = resp.get("nextToken")
        if not token:
            return names
        kwargs["nextToken"] = token


def _discover_log_groups(logs: Any, command_name: str) -> list[str]:
    """Error-bearing log groups to search, best-first.

    Default: list groups under /aws-glue/jobs and keep the error-bearing ones —
    the ``/error`` groups (stderr/traceback) first, then the ``logs-v2*`` All-Logs
    groups. This handles the per-account nesting automatically and needs the
    ``logs:DescribeLogGroups`` permission. DATAPLATFORM_GLUE_LOG_GROUPS overrides
    with an explicit comma-separated list (skips discovery and that permission).
    """
    override = os.environ.get(_LOG_GROUPS_ENV)
    if override:
        groups = [g.strip() for g in override.split(",") if g.strip()]
    else:
        try:
            names = _list_log_group_names(logs, _LOG_GROUP_ROOT)
        except AwsClientError:
            names = []
        error_groups = sorted(n for n in names if _leaf(n) == "error")
        all_logs_groups = sorted(n for n in names if _leaf(n).startswith("logs-v2"))
        groups = [*error_groups, *all_logs_groups, *_DEFAULT_ERROR_GROUPS]
    if command_name == "pythonshell":
        groups.append("/aws-glue/python-jobs/error")
    seen: set[str] = set()
    return [g for g in groups if not (g in seen or seen.add(g))]


def error_excerpt(
    session: Session,
    run_id: str,
    command_name: str,
    *,
    max_lines: int = 60,
    tail_events: int = 500,
) -> dict[str, Any]:
    """Return a bounded, high-signal excerpt from the run's CloudWatch logs.

    Tries the continuous-logging group then the legacy one; within a group, scans
    the run's worker streams until it finds the fatal error (see
    ``_excerpt_from_streams``).
    """

    logs = session.client("logs")
    tried: list[str] = []
    fallback: dict[str, Any] | None = None
    last_note: str | None = None

    for log_group in _discover_log_groups(logs, command_name):
        tried.append(log_group)
        try:
            streams = logs.describe_log_streams(
                logGroupName=log_group, logStreamNamePrefix=run_id
            ).get("logStreams", [])
        except AwsClientError as exc:
            code = exc.response["Error"]["Code"]
            # Group absent in this environment: just try the next candidate.
            if code == "ResourceNotFoundException":
                continue
            last_note = f"{log_group}: {code}"
            continue

        if not streams:
            continue

        result = _excerpt_from_streams(
            logs, log_group, run_id, streams, max_lines=max_lines, tail_events=tail_events
        )
        # Prefer the group whose streams actually carry the error (the "Error
        # Logs" group may differ from where continuous output lands); keep the
        # first excerpt as a fallback if no group shows an error marker.
        if result["found_error_markers"]:
            return result
        if fallback is None:
            fallback = result

    if fallback is not None:
        return fallback
    return {
        "log_groups_tried": tried,
        "available": False,
        "note": last_note or "sem log stream para o run em nenhum grupo conhecido",
    }


def _excerpt_from_streams(
    logs: Any,
    log_group: str,
    run_id: str,
    streams: list[dict[str, Any]],
    *,
    max_lines: int,
    tail_events: int,
) -> dict[str, Any]:
    """Scan worker streams best-first; return the first excerpt with an error
    marker, else the newest stream's tail.

    This is what makes the company's ``<run_id>_g-<worker_hash>`` naming work: the
    driver isn't identifiable by name, so rather than bet on one stream we look
    across the top ``_MAX_STREAMS_SCANNED`` for the one carrying the traceback.
    """
    fallback: tuple[str, str] | None = None

    for stream_name in _ordered_streams(streams, run_id)[:_MAX_STREAMS_SCANNED]:
        events = logs.get_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            startFromHead=False,
            limit=tail_events,
        ).get("events", [])
        lines = [str(e.get("message", "")).rstrip("\n") for e in events]
        excerpt, found = _extract(lines, max_lines)
        if fallback is None:
            fallback = (stream_name, excerpt)
        if found:
            return {
                "log_group": log_group,
                "log_stream": stream_name,
                "available": True,
                "found_error_markers": True,
                "excerpt": excerpt,
            }

    assert fallback is not None  # streams is non-empty, so the loop ran at least once
    stream_name, excerpt = fallback
    return {
        "log_group": log_group,
        "log_stream": stream_name,
        "available": True,
        "found_error_markers": False,
        "excerpt": excerpt,
    }


def _ordered_streams(streams: list[dict[str, Any]], run_id: str) -> list[str]:
    """Worker stream names best-first for finding the fatal error.

    The driver stream is exactly ``run_id`` and carries the traceback, so it wins;
    then any ``driver``-labelled stream; then newest by last event (executors are
    ``<run_id>_g-<worker_hash>`` with no label). The ``<run_id>-progress-bar``
    stream is pure noise and is dropped (unless it's all we have).
    """
    usable = [s for s in streams if "progress-bar" not in s["logStreamName"]] or streams

    def key(s: dict[str, Any]) -> tuple[bool, bool, float]:
        name = s["logStreamName"]
        return (name != run_id, "driver" not in name, -float(s.get("lastEventTimestamp", 0)))

    return [s["logStreamName"] for s in sorted(usable, key=key)]


def _extract(lines: list[str], max_lines: int) -> tuple[str, bool]:
    if not lines:
        return "", False
    for i in range(len(lines) - 1, -1, -1):
        if any(marker in lines[i] for marker in _ERROR_MARKERS):
            start = max(0, i - _CONTEXT_BEFORE)
            return "\n".join(lines[start : start + max_lines]), True
    return "\n".join(lines[-max_lines:]), False
