"""CloudWatch log extraction for Glue job runs.

The goal is a *bounded, high-signal* excerpt — never the raw stream. Fatal
errors sit near the end of the error stream, so we tail it and return a window
around the last error marker (or the tail itself if no marker is found). This
keeps large logs out of the agent's context; the model interprets the excerpt.
"""

from __future__ import annotations

from typing import Any

from dataplatform.config import AwsClientError, Session

# Where the error logs live depends on whether the job uses continuous logging.
# Continuous logging (the current Glue default) writes to /aws-glue/jobs/logs-v2;
# older jobs write to the legacy per-type error groups. We try logs-v2 first and
# fall back to the legacy group, so both worlds work without configuration.
_CONTINUOUS_LOG_GROUP = "/aws-glue/jobs/logs-v2"
_LEGACY_ERROR_LOG_GROUP = {
    "glueetl": "/aws-glue/jobs/error",
    "gluestreaming": "/aws-glue/jobs/error",
    "pythonshell": "/aws-glue/python-jobs/error",
}
_DEFAULT_LEGACY_ERROR_GROUP = "/aws-glue/jobs/error"

# Markers that usually bracket the real cause. Order-independent; matched as
# substrings against each event line.
_ERROR_MARKERS = ("Traceback", "Caused by", "Exception", "ERROR", "Error")

_CONTEXT_BEFORE = 15

# In logs-v2 each worker gets its own stream `<run_id>_g-<worker_hash>` with no
# driver/executor label, so a single stream is a guess. We scan up to this many
# (newest first) and return the first that actually carries an error marker.
_MAX_STREAMS_SCANNED = 5


def _candidate_log_groups(command_name: str) -> list[str]:
    """Log groups to search, in order: continuous logging then the legacy group."""
    legacy = _LEGACY_ERROR_LOG_GROUP.get(command_name, _DEFAULT_LEGACY_ERROR_GROUP)
    ordered = [_CONTINUOUS_LOG_GROUP, legacy]
    seen: set[str] = set()
    return [g for g in ordered if not (g in seen or seen.add(g))]


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

    for log_group in _candidate_log_groups(command_name):
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
    """Worker stream names best-first for finding the fatal error: exact ``run_id``
    (legacy driver / python shell), then any ``driver``-labelled stream, then
    newest by last event. Company logs-v2 streams (``<run_id>_g-<worker_hash>``)
    carry no label, so they fall to newest-first and the marker scan in
    ``_excerpt_from_streams`` locates the traceback.
    """

    def key(s: dict[str, Any]) -> tuple[bool, bool, float]:
        name = s["logStreamName"]
        return (name != run_id, "driver" not in name, -float(s.get("lastEventTimestamp", 0)))

    return [s["logStreamName"] for s in sorted(streams, key=key)]


def _extract(lines: list[str], max_lines: int) -> tuple[str, bool]:
    if not lines:
        return "", False
    for i in range(len(lines) - 1, -1, -1):
        if any(marker in lines[i] for marker in _ERROR_MARKERS):
            start = max(0, i - _CONTEXT_BEFORE)
            return "\n".join(lines[start : start + max_lines]), True
    return "\n".join(lines[-max_lines:]), False
